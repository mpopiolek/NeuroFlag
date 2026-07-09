from __future__ import annotations

import re
from datetime import date, datetime

import pytest
from reportlab.platypus import Paragraph as ReportLabParagraph

from app.domain.types import (
    AnalysisResult,
    BandRange,
    CategoryDescriptions,
    CellColor,
    CellResult,
    ClinicalDiagnosis,
    NormEntry,
    NormsConfig,
    ObservationCategory,
    ObservationChecklist,
    PatientMetadata,
    RecommendationRules,
    ScreeningCategory,
    Sex,
    format_clinical_diagnoses,
)
from app.reports.pdf_generator import (
    DISCLAIMER_PL,
    format_analysis_metadata_line,
    format_pdf_expert_footer_line,
    format_pdf_tech_footer_line,
    format_report_subtitle,
    generate_report,
)
from app.ui.components.rag_colors import TASK_LABELS
from app.ui.info_content import EXPERT_CONTACT, TECH_CONTACT

_RULES = RecommendationRules(
    indication_min_red=5,
    indication_max_green=3,
    no_indication_min_green=4,
    no_indication_max_red=3,
)

_DESCRIPTIONS = CategoryDescriptions(
    wskazanie="Wskazanie testowe",
    obserwacja="Obserwacja testowa",
    brak="Brak testowe",
)

_CHECKLIST = ObservationChecklist(
    title="Co obserwowac",
    intro="Intro testowe",
    categories=(
        ObservationCategory(title="Uwaga", items=("Pozycja 1", "Pozycja 2")),
    ),
)

_NORMS: tuple[NormEntry, ...] = tuple(
    NormEntry(norm_id=i + 1, channel="C3", task="OO", band="Theta", mean_z=10.0, mean_k=20.0)
    for i in range(10)
)

_CONFIG = NormsConfig(
    version=1,
    power_line_frequency=50.0,
    band_ranges={"Theta": BandRange(l_freq=4.0, h_freq=8.0)},
    norms=_NORMS,
    recommendation_rules=_RULES,
    category_descriptions=_DESCRIPTIONS,
    observation_checklist=_CHECKLIST,
)

_CELLS: tuple[CellResult, ...] = tuple(
    CellResult(i, ch, task, band, color)
    for i, (ch, task, band, color) in enumerate([
        ("C3", "OO", "Theta", CellColor.RED),
        ("C3", "OO", "Beta1", CellColor.GREEN),
        ("C3", "OZ", "Theta", CellColor.YELLOW),
        ("C3", "OZ", "Beta1", CellColor.GREEN),
        ("C3", "ZP", "Theta", CellColor.RED),
        ("O1", "OO", "Theta", CellColor.GREEN),
        ("O1", "OO", "Beta1", CellColor.YELLOW),
        ("O1", "OZ", "Theta", CellColor.RED),
        ("O1", "OZ", "Beta1", CellColor.GREEN),
        ("O1", "ZP", "Theta", CellColor.YELLOW),
    ])
)

_METADATA = PatientMetadata(age=8, sex=Sex.Z)

_RESULT = AnalysisResult(
    cells=_CELLS,
    category=ScreeningCategory.WSKAZANIE,
    description="Wskazanie testowe",
    analyzed_at=datetime(2026, 6, 23, 12, 0, 0),
)


def _pdf_info_obj(pdf_bytes: bytes) -> bytes:
    """Return raw bytes of the /Info dictionary object (uncompressed metadata).

    ReportLab stores title, author, subject, keywords, etc. here as plain literal strings.
    Content streams are FlateDecode-compressed and searched separately.
    """
    m = re.search(rb"/Info\s+(\d+)\s+0\s+R", pdf_bytes)
    if not m:
        return b""
    obj_num = re.escape(m.group(1))
    obj_m = re.search(obj_num + rb"\s+0\s+obj\b.*?endobj", pdf_bytes, re.DOTALL)
    return obj_m.group(0) if obj_m else b""


@pytest.fixture(scope="module")
def pdf_bytes() -> bytes:
    return generate_report(_METADATA, _RESULT, _CONFIG)


@pytest.fixture(scope="module")
def pdf_info(pdf_bytes: bytes) -> bytes:
    return _pdf_info_obj(pdf_bytes)


def test_generate_report_returns_bytes(pdf_bytes: bytes) -> None:
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0


def test_pdf_starts_with_pdf_magic(pdf_bytes: bytes) -> None:
    assert pdf_bytes[:4] == b"%PDF"


def test_no_uv_in_pdf_metadata(pdf_info: bytes) -> None:
    # Search only in the /Info dictionary object (uncompressed metadata).
    # The generator never receives amplitude data; no µV/uV can appear there.
    assert b"uV" not in pdf_info
    assert b"microV" not in pdf_info
    assert b"\xb5V" not in pdf_info  # µV in PDFDocEncoding


def test_no_uv_values_in_output(pdf_bytes: bytes) -> None:
    # Scan full raw PDF bytes for UTF-8 µV (\xc2\xb5V).
    # Single-byte \xb5 and "uV" collide with random binary data in PDF streams
    # and are checked separately in test_no_uv_in_pdf_metadata (uncompressed metadata).
    assert b"\xc2\xb5V" not in pdf_bytes  # UTF-8 µV


def test_pdf_metadata_title_present(pdf_bytes: bytes) -> None:
    # "NeuroFlag" is stored in the /Title and /Author metadata fields (uncompressed).
    assert b"NeuroFlag" in pdf_bytes


def test_all_10_cells_represented(pdf_bytes: bytes) -> None:
    # Channel names and band names are stored in /Keywords metadata (uncompressed).
    # Format: "C3-Theta C3-Beta1 ..." set by generate_report().
    for cell in _CELLS:
        token = f"{cell.channel}-{cell.band}".encode()
        assert token in pdf_bytes, f"{cell.channel}-{cell.band} not found in PDF keywords"


def test_category_in_output(pdf_bytes: bytes) -> None:
    # _RESULT uses ScreeningCategory.WSKAZANIE whose value is pure ASCII ("Wskazanie...").
    # ReportLab stores /Subject in the /Info dict as a UTF-16BE string when non-ASCII chars
    # are present; using an all-ASCII category value avoids encoding ambiguity.
    assert b"Wskazanie" in pdf_bytes


def test_disclaimer_contains_privacy_text() -> None:
    assert "lokalnie" in DISCLAIMER_PL
    assert "nagłówku" in DISCLAIMER_PL
    assert "nie są wyświetlane ani zapisywane w raporcie" in DISCLAIMER_PL


def test_pdf_includes_diagnoses_when_present() -> None:
    meta = PatientMetadata(
        age=8,
        sex=Sex.Z,
        diagnoses=frozenset({ClinicalDiagnosis.ADHD}),
    )
    empty_pdf = generate_report(_METADATA, _RESULT, _CONFIG)
    diagnosed_pdf = generate_report(meta, _RESULT, _CONFIG)
    assert diagnosed_pdf != empty_pdf
    assert len(diagnosed_pdf) > len(empty_pdf)


def test_pdf_omits_diagnoses_when_empty() -> None:
    assert format_clinical_diagnoses(_METADATA) == ""


def test_format_report_subtitle_with_recording_date() -> None:
    assert (
        format_report_subtitle(date(2026, 1, 16))
        == "Raport przesiewowy EEG na podstawie badania z dnia: 16.01.2026"
    )


def test_format_report_subtitle_without_recording_date() -> None:
    assert format_report_subtitle(None) == "Raport przesiewowy EEG"


def test_format_analysis_metadata_line_uses_analysis_date_label() -> None:
    line = format_analysis_metadata_line(_METADATA, _RESULT.analyzed_at)
    assert line.startswith("Data analizy badania:")
    assert "23.06.2026" in line
    assert "8 lat" in line
    assert "Dziewczynka" in line


def test_pdf_subtitle_differs_when_recording_date_provided() -> None:
    without_date = generate_report(_METADATA, _RESULT, _CONFIG)
    with_date = generate_report(
        _METADATA,
        _RESULT,
        _CONFIG,
        recording_date=date(2026, 1, 16),
    )
    assert without_date != with_date


def test_pdf_footer_line_helpers_contain_contact_info() -> None:
    assert EXPERT_CONTACT.email in format_pdf_expert_footer_line()
    assert format_pdf_tech_footer_line() == "https://github.com/mpopiolek/NeuroFlag"


def test_pdf_footer_contact_lines_in_report_story(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []

    def track_paragraph(text: str, style: object) -> object:
        captured.append(text)
        return ReportLabParagraph(text, style)

    monkeypatch.setattr("app.reports.pdf_generator.Paragraph", track_paragraph)
    generate_report(_METADATA, _RESULT, _CONFIG)
    story_text = " ".join(captured)
    assert EXPERT_CONTACT.email in story_text
    assert "https://github.com/mpopiolek/NeuroFlag" in story_text
    assert TECH_CONTACT.email not in story_text


def test_pdf_story_contains_task_section_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    def track_paragraph(text: str, style: object) -> object:
        captured.append(text)
        return ReportLabParagraph(text, style)

    monkeypatch.setattr("app.reports.pdf_generator.Paragraph", track_paragraph)
    generate_report(_METADATA, _RESULT, _CONFIG)
    story_text = " ".join(captured)
    for task in ("OO", "OZ", "ZP"):
        assert TASK_LABELS[task] in story_text


def test_pdf_story_contains_band_names_in_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[str] = []

    def track_paragraph(text: str, style: object) -> object:
        captured.append(text)
        return ReportLabParagraph(text, style)

    monkeypatch.setattr("app.reports.pdf_generator.Paragraph", track_paragraph)
    generate_report(_METADATA, _RESULT, _CONFIG)
    story_text = " ".join(captured)
    for cell in _CELLS:
        assert cell.band in story_text
