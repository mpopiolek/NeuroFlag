from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.domain.errors import PipelineError
from app.domain.types import AnalysisDiagnostics, BugReportContext, NormsConfig
from app.ui.bug_report import (
    build_github_issue_url,
    collect_bug_report_context,
    format_bug_report_body,
    open_bug_report,
)


def _minimal_norms_config() -> NormsConfig:
    from app.domain.norms import load, resolve_norms_path

    return load(resolve_norms_path())


def _sample_context(**overrides: object) -> BugReportContext:
    defaults: dict[str, object] = {
        "app_version": "0.1.0",
        "os_string": "Windows 10 (AMD64)",
        "mne_version": "1.8.0",
        "numpy_version": "2.2.0",
        "error_code": "unexpected_error",
        "error_message_pl": "Nieoczekiwany błąd analizy: RuntimeError",
        "exception_type_name": "RuntimeError",
        "app_step_pl": "Plik",
        "eeg_suffix": ".edf",
        "header_channel_count": 32,
        "c3_o1_status": "present",
        "segment_mode": "annotations",
        "anonymize_header": True,
        "norms_version": 1,
        "manual_report": False,
    }
    defaults.update(overrides)
    return BugReportContext(**defaults)  # type: ignore[arg-type]


def test_format_body_excludes_pii_and_paths() -> None:
    ctx = _sample_context(
        error_message_pl="Nieoczekiwany błąd analizy: RuntimeError",
    )
    body = format_bug_report_body(ctx)
    assert "C:\\" not in body
    assert "C:/" not in body
    assert "@" not in body
    assert "AN" not in body
    assert "## Diagnostyka (auto-wypełnione)" in body
    assert "Uzupełnij sekcje szablonu poniżej" in body


def test_build_github_issue_url_contains_repo_and_template() -> None:
    ctx = _sample_context()
    url = build_github_issue_url(ctx)
    assert "github.com/mpopiolek/NeuroFlag" in url
    assert "template=bug_report.md" in url
    assert "labels=bug" in url


def test_manual_report_omits_error_code() -> None:
    ctx = _sample_context(
        manual_report=True,
        error_code=None,
        error_message_pl=None,
        exception_type_name=None,
        app_step_pl="Informacje",
    )
    body = format_bug_report_body(ctx)
    assert "Kod błędu" not in body
    assert "0.1.0" in body
    assert "Informacje" in body


def test_exception_type_name_in_body() -> None:
    ctx = _sample_context(exception_type_name="RuntimeError")
    body = format_bug_report_body(ctx)
    assert "RuntimeError" in body
    assert "**Typ wyjątku:** RuntimeError" in body


@dataclass
class _FakeState:
    norms_config: NormsConfig
    eeg_path: Path | None = None
    available_channels: list[str] = field(default_factory=list)
    channel_overrides: dict[str, str] = field(default_factory=dict)
    anonymize_header: bool = True
    analysis_in_progress: bool = False
    last_analysis_diagnostics: AnalysisDiagnostics | None = None


def test_collect_context_uses_suffix_not_path() -> None:
    from app.ui.views.file_import import FileImportView

    state = _FakeState(
        norms_config=_minimal_norms_config(),
        eeg_path=Path(r"C:\Users\Secret\patient.edf"),
        available_channels=["C3", "O1", "Fp1"],
    )
    app_window = MagicMock()
    app_window.app_state = state
    app_window.current_view = FileImportView.__new__(FileImportView)

    ctx = collect_bug_report_context(
        app_window,
        error=PipelineError("unexpected_error", "Test"),
    )

    body = format_bug_report_body(ctx)
    assert ctx.eeg_suffix == ".edf"
    assert "patient" not in body
    assert "Secret" not in body
    assert "Users" not in body


def test_collect_context_c3_o1_mapped() -> None:
    state = _FakeState(
        norms_config=_minimal_norms_config(),
        available_channels=["EEG 3", "O1"],
        channel_overrides={"C3": "EEG 3"},
    )
    app_window = MagicMock()
    app_window.app_state = state
    app_window.current_view = None

    ctx = collect_bug_report_context(app_window, manual=True)
    assert ctx.c3_o1_status == "mapped"
    assert "mapowanie ręczne" in format_bug_report_body(ctx)


def test_manual_report_uses_unknown_segment_mode_without_active_analysis() -> None:
    from app.ui.views.file_import import FileImportView

    state = _FakeState(
        norms_config=_minimal_norms_config(),
        last_analysis_diagnostics=AnalysisDiagnostics(segment_mode="annotations"),
    )
    app_window = MagicMock()
    app_window.app_state = state
    app_window.current_view = FileImportView.__new__(FileImportView)

    ctx = collect_bug_report_context(app_window, manual=True)
    body = format_bug_report_body(ctx)
    assert ctx.segment_mode == "unknown"
    assert "nieznane" in body


@patch("app.ui.bug_report.webbrowser.open")
def test_open_bug_report_long_url_uses_clipboard(mock_open: MagicMock) -> None:
    long_message = "x" * 7000
    ctx = _sample_context(error_message_pl=long_message)
    with patch("app.ui.bug_report._copy_body_to_clipboard") as mock_clip:
        open_bug_report(ctx)
    mock_clip.assert_called_once()
    mock_open.assert_called_once()
    url = mock_open.call_args[0][0]
    assert len(url) <= 6000
    assert "wklej" in url.lower()
