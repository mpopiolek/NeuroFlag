from __future__ import annotations

import platform
import tkinter.messagebox
import urllib.parse
import webbrowser
from typing import TYPE_CHECKING

from app import __version__
from app.domain.channels import get_missing_canonical
from app.domain.errors import PipelineError
from app.domain.types import (
    BugReportContext,
    C3O1Status,
    SegmentDetectionMode,
)
from app.ui import info_content

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow

_GITHUB_URL_MAX_LEN = 6000

_SEGMENT_MODE_PL: dict[SegmentDetectionMode, str] = {
    "annotations": "wykryte z adnotacji",
    "fallback": "fallback 3×3 min",
    "not_reached": "nie dotyczy",
    "unknown": "nieznane",
}

_C3_O1_STATUS_PL: dict[C3O1Status, str] = {
    "present": "obecne",
    "missing": "brak",
    "mapped": "mapowanie ręczne",
}


def _resolve_c3_o1_status(
    available_channels: list[str],
    channel_overrides: dict[str, str],
) -> C3O1Status:
    if channel_overrides:
        return "mapped"
    if get_missing_canonical(available_channels) == []:
        return "present"
    return "missing"


def _resolve_app_step_pl(app_window: AppWindow) -> str:
    if app_window.app_state.analysis_in_progress:
        return "Analiza (overlay)"

    current_view = app_window.current_view
    if current_view is None:
        return "Nieznany"

    from app.ui.views.file_import import FileImportView
    from app.ui.views.history import HistoryView
    from app.ui.views.info_view import InfoView
    from app.ui.views.metadata_form import MetadataFormView
    from app.ui.views.results_grid import ResultsGridView

    view_type = type(current_view)
    if view_type is MetadataFormView:
        return "Dane"
    if view_type in (FileImportView,):
        return "Plik"
    from app.ui.views.channel_mapping import ChannelMappingView

    if view_type is ChannelMappingView:
        return "Plik"
    if view_type is ResultsGridView:
        return "Wynik"
    if view_type is InfoView:
        return "Informacje"
    if view_type is HistoryView:
        return "Historia"
    return "Nieznany"


def _resolve_segment_mode(
    app_window: AppWindow,
    *,
    manual: bool,
) -> SegmentDetectionMode:
    if manual and not app_window.app_state.analysis_in_progress:
        return "unknown"
    diag = app_window.app_state.last_analysis_diagnostics
    if diag is None:
        return "unknown"
    return diag.segment_mode


def _optional_lib_versions() -> tuple[str | None, str | None]:
    mne_version: str | None = None
    numpy_version: str | None = None
    try:
        import mne

        mne_version = mne.__version__
    except ImportError:
        pass
    try:
        import numpy as np

        numpy_version = np.__version__
    except ImportError:
        pass
    return mne_version, numpy_version


def _os_string() -> str:
    return (
        f"{platform.system()} {platform.version()} "
        f"({platform.machine()})"
    )


def collect_bug_report_context(
    app_window: AppWindow,
    *,
    error: PipelineError | None = None,
    exception_type_name: str | None = None,
    manual: bool = False,
) -> BugReportContext:
    state = app_window.app_state
    mne_version, numpy_version = _optional_lib_versions()

    error_code: str | None = None
    error_message_pl: str | None = None
    if not manual and error is not None:
        error_code = error.code
        error_message_pl = error.user_message_pl

    eeg_suffix = state.eeg_path.suffix.lower() if state.eeg_path is not None else "brak"

    return BugReportContext(
        app_version=__version__,
        os_string=_os_string(),
        mne_version=mne_version,
        numpy_version=numpy_version,
        error_code=error_code,
        error_message_pl=error_message_pl,
        exception_type_name=exception_type_name,
        app_step_pl=_resolve_app_step_pl(app_window),
        eeg_suffix=eeg_suffix,
        header_channel_count=len(state.available_channels),
        c3_o1_status=_resolve_c3_o1_status(
            state.available_channels,
            state.channel_overrides,
        ),
        segment_mode=_resolve_segment_mode(app_window, manual=manual),
        anonymize_header=state.anonymize_header,
        norms_version=state.norms_config.version,
        manual_report=manual,
    )


def format_bug_report_body(ctx: BugReportContext) -> str:
    lines: list[str] = [
        "## Diagnostyka (auto-wypełnione)",
        "",
        f"- **Wersja NeuroFlag:** {ctx.app_version}",
        f"- **System:** {ctx.os_string}",
    ]
    if ctx.mne_version is not None:
        lines.append(f"- **MNE-Python:** {ctx.mne_version}")
    if ctx.numpy_version is not None:
        lines.append(f"- **NumPy:** {ctx.numpy_version}")

    if not ctx.manual_report and ctx.error_code is not None:
        lines.append(f"- **Kod błędu:** {ctx.error_code}")
    if not ctx.manual_report and ctx.error_message_pl is not None:
        lines.append(f"- **Komunikat:** {ctx.error_message_pl}")
    if ctx.exception_type_name is not None:
        lines.append(f"- **Typ wyjątku:** {ctx.exception_type_name}")

    lines.extend(
        [
            f"- **Krok aplikacji:** {ctx.app_step_pl}",
            f"- **Rozszerzenie pliku EEG:** {ctx.eeg_suffix or 'brak'}",
            f"- **Liczba kanałów w nagłówku:** {ctx.header_channel_count}",
            f"- **Status C3/O1:** {_C3_O1_STATUS_PL[ctx.c3_o1_status]}",
            f"- **Znaczniki OO/OZ/ZP:** {_SEGMENT_MODE_PL[ctx.segment_mode]}",
            (
                "- **Wyczyść dane identyfikacyjne:** "
                f"{'tak' if ctx.anonymize_header else 'nie'}"
            ),
            f"- **Wersja norms.json:** {ctx.norms_version}",
            "",
            "Uzupełnij sekcje szablonu poniżej.",
            "",
        ]
    )
    return "\n".join(lines)


def _issue_title(ctx: BugReportContext) -> str:
    if ctx.manual_report:
        return "[Bug] NeuroFlag — zgłoszenie użytkownika"
    if ctx.error_code is not None:
        return f"[Bug] NeuroFlag — {ctx.error_code}"
    return "[Bug] NeuroFlag — nieoczekiwany błąd"


def build_github_issue_url(ctx: BugReportContext) -> str:
    body = format_bug_report_body(ctx)
    params = urllib.parse.urlencode(
        {
            "template": "bug_report.md",
            "labels": "bug",
            "title": _issue_title(ctx),
            "body": body,
        },
        quote_via=urllib.parse.quote,
    )
    return f"{info_content.GITHUB_NEW_ISSUE_URL}?{params}"


def _copy_body_to_clipboard(body: str) -> None:
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    try:
        root.clipboard_clear()
        root.clipboard_append(body)
        root.update()
    finally:
        root.destroy()


def open_bug_report(ctx: BugReportContext) -> None:
    body = format_bug_report_body(ctx)
    url = build_github_issue_url(ctx)

    if len(url) > _GITHUB_URL_MAX_LEN:
        _copy_body_to_clipboard(body)
        short_params = urllib.parse.urlencode(
            {
                "template": "bug_report.md",
                "labels": "bug",
                "title": _issue_title(ctx),
                "body": (
                    "Diagnostyka skopiowana do schowka — wklej ją poniżej "
                    "w sekcji „Diagnostyka (auto-wypełnione)”.\n\n"
                    "Uzupełnij sekcje szablonu poniżej."
                ),
            },
            quote_via=urllib.parse.quote,
        )
        url = f"{info_content.GITHUB_NEW_ISSUE_URL}?{short_params}"
        try:
            webbrowser.open(url)
        except OSError:
            tkinter.messagebox.showerror(
                "Nie można otworzyć przeglądarki",
                "Skopiuj adres i otwórz go ręcznie w przeglądarce:\n\n"
                f"{url}\n\n"
                "Treść diagnostyki jest już w schowku.",
            )
        return

    try:
        webbrowser.open(url)
    except OSError:
        tkinter.messagebox.showerror(
            "Nie można otworzyć przeglądarki",
            "Skopiuj adres i otwórz go ręcznie w przeglądarce:\n\n"
            f"{url}",
        )
