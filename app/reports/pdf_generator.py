from __future__ import annotations

import io
import os
from datetime import date, datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app import __version__
from app.domain.cell_layout import (
    CHANNEL_DISPLAY_ORDER,
    TASK_DISPLAY_ORDER,
    cells_for_task_channel,
)
from app.domain.types import (
    AnalysisResult,
    CellColor,
    CellResult,
    NormsConfig,
    PatientMetadata,
    format_clinical_diagnoses,
)
from app.presentation.rag_colors import RAG_COLOR_BG, RAG_COLOR_FG, TASK_LABELS
from app.ui.info_content import EXPERT_CONTACT, EXPERT_CONTACT_SHORT_ROLE, GITHUB_REPO_URL

_FONTS_DIR = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"

def _register_fonts() -> str:
    """Rejestruje Arial z systemu Windows; fallback na Helvetica."""
    if "Arial" in pdfmetrics.getRegisteredFontNames():
        return "Arial"
    regular = _FONTS_DIR / "arial.ttf"
    bold = _FONTS_DIR / "arialbd.ttf"
    italic = _FONTS_DIR / "ariali.ttf"
    if regular.exists() and bold.exists() and italic.exists():
        pdfmetrics.registerFont(TTFont("Arial", str(regular)))
        pdfmetrics.registerFont(TTFont("Arial-Bold", str(bold)))
        pdfmetrics.registerFont(TTFont("Arial-Italic", str(italic)))
        return "Arial"
    return "Helvetica"

try:
    _BASE_FONT = _register_fonts()
except Exception:
    _BASE_FONT = "Helvetica"

DISCLAIMER_PL: str = (
    "Analiza przeprowadzona wyłącznie lokalnie; żadne dane nie zostały wysłane poza to urządzenie. "
    "Identyfikatory zapisane w nagłówku pliku EEG przez aparat nie są wyświetlane "
    "ani zapisywane w raporcie. "
    "Raport jest narzędziem przesiewowym i nie stanowi diagnozy medycznej. "
    "Wyniki należy interpretować wyłącznie w połączeniu z pełną oceną kliniczną "
    "przez uprawnionego specjalisty. Autorzy aplikacji NeuroFlag nie ponoszą "
    "odpowiedzialności za decyzje podjęte wyłącznie na podstawie niniejszego raportu."
)

_PAGE_W, _PAGE_H = A4
_MARGIN = 2 * cm

_PDF_CELL_W = 2.1 * cm
_PDF_CELL_H = 1.4 * cm
_PDF_CELL_GAP = 0.15 * cm
_PDF_CHANNEL_GAP = 0.4 * cm
_PDF_SECTION_GAP = 0.12 * cm


def format_report_subtitle(recording_date: date | None) -> str:
    if recording_date is not None:
        rec_date_str = recording_date.strftime("%d.%m.%Y")
        return f"Raport przesiewowy EEG na podstawie badania z dnia: {rec_date_str}"
    return "Raport przesiewowy EEG"


def format_analysis_metadata_line(
    metadata: PatientMetadata,
    analyzed_at: datetime,
) -> str:
    date_str = analyzed_at.strftime("%d.%m.%Y")
    sex_label = "Dziewczynka" if metadata.sex.value == "Z" else "Ch\u0142opiec"
    return (
        f"Data analizy badania: <b>{date_str}</b> &nbsp;&nbsp; "
        f"Wiek: <b>{metadata.age} lat</b> &nbsp;&nbsp; "
        f"P\u0142e\u0107: <b>{sex_label}</b>"
    )


def format_pdf_expert_footer_line() -> str:
    expert = EXPERT_CONTACT
    phone = f"tel. {expert.phone}" if expert.phone is not None else ""
    return f"{expert.name}, {EXPERT_CONTACT_SHORT_ROLE}, {phone}, {expert.email}"


def format_pdf_tech_footer_line() -> str:
    return GITHUB_REPO_URL


def _cell_text_color(color: CellColor) -> colors.Color:
    return colors.HexColor(RAG_COLOR_FG[color])


def _make_band_cell_paragraph(
    cell: CellResult,
    *,
    bold_font_name: str,
    base_style: ParagraphStyle,
    slot_index: int,
) -> Paragraph:
    cell_style = ParagraphStyle(
        f"band_cell_{cell.cell_id}_{slot_index}",
        parent=base_style,
        fontSize=9,
        fontName=bold_font_name,
        alignment=1,
        textColor=_cell_text_color(cell.color),
        leading=12,
    )
    return Paragraph(cell.band, cell_style)


def _cluster_table_width(cell_count: int) -> float:
    if cell_count == 0:
        return float(_PDF_CELL_W)
    return float(cell_count * _PDF_CELL_W + (cell_count - 1) * _PDF_CELL_GAP)


def _build_channel_cluster_table(
    channel: str,
    channel_cells: list[CellResult],
    *,
    bold_font_name: str,
    base_style: ParagraphStyle,
    muted_style: ParagraphStyle,
) -> Table:
    if channel_cells:
        cell_cols: list[Paragraph | str] = [
            _make_band_cell_paragraph(
                cell,
                bold_font_name=bold_font_name,
                base_style=base_style,
                slot_index=idx,
            )
            for idx, cell in enumerate(channel_cells)
        ]
    else:
        cell_cols = [""]

    n = len(cell_cols)
    label_row: list[Paragraph | str] = [Paragraph(channel, muted_style)]
    if n > 1:
        label_row.extend([""] * (n - 1))

    table = Table(
        [label_row, cell_cols],
        colWidths=[_PDF_CELL_W] * n,
        rowHeights=[0.45 * cm, _PDF_CELL_H],
        hAlign="LEFT",
    )

    style_commands: list[tuple[object, ...]] = [
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-2, -1), _PDF_CELL_GAP),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]
    for idx, cell in enumerate(channel_cells):
        bg = colors.HexColor(RAG_COLOR_BG[cell.color])
        style_commands.append(("BACKGROUND", (idx, 1), (idx, 1), bg))
    table.setStyle(TableStyle(style_commands))
    return table


def _build_task_section_table(
    cells: tuple[CellResult, ...],
    task: str,
    *,
    bold_font_name: str,
    base_style: ParagraphStyle,
    muted_style: ParagraphStyle,
) -> Table:
    c3_cells = cells_for_task_channel(cells, task, CHANNEL_DISPLAY_ORDER[0])
    o1_cells = cells_for_task_channel(cells, task, CHANNEL_DISPLAY_ORDER[1])

    c3_table = _build_channel_cluster_table(
        CHANNEL_DISPLAY_ORDER[0],
        c3_cells,
        bold_font_name=bold_font_name,
        base_style=base_style,
        muted_style=muted_style,
    )
    o1_table = _build_channel_cluster_table(
        CHANNEL_DISPLAY_ORDER[1],
        o1_cells,
        bold_font_name=bold_font_name,
        base_style=base_style,
        muted_style=muted_style,
    )

    c3_w = _cluster_table_width(len(c3_cells))
    o1_w = _cluster_table_width(len(o1_cells))

    table = Table(
        [[c3_table, o1_table]],
        colWidths=[c3_w, o1_w],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (1, 0), (1, 0), _PDF_CHANNEL_GAP),
            ]
        )
    )
    return table


def _build_rag_grid_story(
    cells: tuple[CellResult, ...],
    *,
    style_h3: ParagraphStyle,
    style_normal: ParagraphStyle,
    bold_font_name: str,
) -> list[Flowable]:
    muted_style = ParagraphStyle(
        "channel_muted",
        parent=style_normal,
        fontSize=8,
        fontName=bold_font_name,
        textColor=colors.HexColor("#666666"),
        spaceAfter=2,
    )

    flowables: list[Flowable] = []
    for task_idx, task in enumerate(TASK_DISPLAY_ORDER):
        if task_idx > 0:
            flowables.append(Spacer(1, _PDF_SECTION_GAP))
        task_label = TASK_LABELS.get(task, task)
        flowables.append(Paragraph(task_label, style_h3))
        flowables.append(
            _build_task_section_table(
                cells,
                task,
                bold_font_name=bold_font_name,
                base_style=style_normal,
                muted_style=muted_style,
            )
        )
    return flowables


def generate_report(
    metadata: PatientMetadata,
    result: AnalysisResult,
    config: NormsConfig,
    *,
    recording_date: date | None = None,
) -> bytes:
    """Generuje raport PDF; nigdy nie zawiera wartości µV."""
    buf = io.BytesIO()
    keywords = " ".join(f"{c.channel}-{c.band}" for c in result.cells)
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=_MARGIN,
        rightMargin=_MARGIN,
        topMargin=_MARGIN,
        bottomMargin=_MARGIN,
        title="NeuroFlag",
        author="NeuroFlag",
        subject=result.category.value,
        keywords=keywords,
    )

    styles = getSampleStyleSheet()
    style_normal = styles["Normal"]
    _bold = f"{_BASE_FONT}-Bold" if _BASE_FONT == "Arial" else "Helvetica-Bold"
    _italic = f"{_BASE_FONT}-Italic" if _BASE_FONT == "Arial" else "Helvetica-Oblique"

    style_h1 = ParagraphStyle(
        "h1",
        parent=style_normal,
        fontSize=18,
        leading=22,
        fontName=_bold,
        spaceAfter=8,
    )
    style_h2 = ParagraphStyle(
        "h2",
        parent=style_normal,
        fontSize=13,
        fontName=_bold,
        spaceBefore=10,
        spaceAfter=4,
    )
    style_h3 = ParagraphStyle(
        "h3",
        parent=style_normal,
        fontSize=11,
        fontName=_bold,
        spaceBefore=6,
        spaceAfter=2,
    )
    style_body = ParagraphStyle(
        "body",
        parent=style_normal,
        fontSize=10,
        fontName=_BASE_FONT,
        leading=14,
        spaceAfter=4,
    )
    style_small_italic = ParagraphStyle(
        "small_italic",
        parent=style_normal,
        fontSize=8,
        fontName=_italic,
        leading=11,
        textColor=colors.HexColor("#555555"),
    )
    style_footer = ParagraphStyle(
        "footer",
        parent=style_normal,
        fontSize=7,
        fontName=_BASE_FONT,
        textColor=colors.HexColor("#888888"),
        alignment=2,  # right
    )

    story = []

    # ── Sekcja 1: Nagłówek / Intro ──────────────────────────────────────────
    story.append(Paragraph("NeuroFlag", style_h1))
    story.append(Paragraph(format_report_subtitle(recording_date), style_body))
    story.append(Spacer(1, 0.3 * cm))

    story.append(
        Paragraph(
            format_analysis_metadata_line(metadata, result.analyzed_at),
            style_body,
        )
    )
    diagnoses_label = format_clinical_diagnoses(metadata)
    if diagnoses_label:
        story.append(
            Paragraph(
                f"Diagnozy: <b>{diagnoses_label}</b>",
                style_body,
            )
        )
    story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(
            f"Analiza wynik\u00f3w wskazuje na: <b>{result.category.value}</b>",
            style_body,
        )
    )
    story.append(Paragraph(result.description, style_body))
    story.append(Spacer(1, 0.4 * cm))

    # ── Sekcja 2: Siatka 10 komórek RAG (Wariant A′) ─────────────────────────
    story.append(Paragraph("Wyniki analizy", style_h2))
    story.append(Spacer(1, 0.15 * cm))
    story.extend(
        _build_rag_grid_story(
            result.cells,
            style_h3=style_h3,
            style_normal=style_body,
            bold_font_name=_bold,
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    # ── Sekcja 3: Checklist "Co obserwować" ─────────────────────────────────
    cl = config.observation_checklist
    story.append(Paragraph(cl.title, style_h2))
    story.append(Paragraph(cl.intro, style_body))
    story.append(Spacer(1, 0.2 * cm))

    for cat in cl.categories:
        story.append(Paragraph(cat.title, style_h3))
        for item in cat.items:
            story.append(Paragraph(f"\u2022 {item}", style_body))

    story.append(Spacer(1, 0.5 * cm))

    # ── Sekcja 4: Klauzula odpowiedzialności ─────────────────────────────────
    story.append(Paragraph("Klauzula odpowiedzialno\u015bci", style_h2))
    story.append(Paragraph(DISCLAIMER_PL, style_small_italic))
    story.append(Spacer(1, 0.3 * cm))
    footer_date = result.analyzed_at.strftime("%d.%m.%Y")
    story.append(
        Paragraph(f"NeuroFlag v{__version__} | {footer_date}", style_footer)
    )
    story.append(
        Paragraph(format_pdf_expert_footer_line(), style_footer)
    )
    story.append(
        Paragraph(format_pdf_tech_footer_line(), style_footer)
    )

    doc.build(story)
    return buf.getvalue()
