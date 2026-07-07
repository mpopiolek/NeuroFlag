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
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app import __version__
from app.domain.types import (
    AnalysisResult,
    CellColor,
    NormsConfig,
    PatientMetadata,
    format_clinical_diagnoses,
)
from app.ui.components.rag_colors import RAG_COLOR_BG, TASK_LABELS

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

    # ── Sekcja 2: Siatka 10 komórek RAG (2 × 5) ────────────────────────────
    story.append(Paragraph("Wyniki analizy", style_h2))
    story.append(Spacer(1, 0.15 * cm))

    cell_w = (_PAGE_W - 2 * _MARGIN) / 5
    cell_h = 1.8 * cm

    grid_data: list[list[Paragraph]] = [[], []]
    for idx, cell in enumerate(result.cells):
        task_label = TASK_LABELS.get(cell.task, cell.task)
        if cell.color in (CellColor.RED, CellColor.GREEN):
            fg = colors.white
        else:
            fg = colors.HexColor("#1A1A1A")
        cell_style = ParagraphStyle(
            f"cell_{idx}",
            parent=style_normal,
            fontSize=8,
            fontName=_bold,
            alignment=1,  # center
            textColor=fg,
            leading=11,
        )
        text = (
            f"{cell.channel}<br/>"
            f"<font size='7'>{task_label}</font><br/>"
            f"<font size='7'>{cell.band}</font>"
        )
        para = Paragraph(text, cell_style)
        grid_data[idx // 5].append(para)

    grid_table = Table(
        grid_data,
        colWidths=[cell_w] * 5,
        rowHeights=[cell_h, cell_h],
    )

    ts = TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.white)])
    for idx, cell in enumerate(result.cells):
        row, col = idx // 5, idx % 5
        bg = colors.HexColor(RAG_COLOR_BG[cell.color])
        ts.add("BACKGROUND", (col, row), (col, row), bg)
        ts.add("VALIGN", (col, row), (col, row), "MIDDLE")
        ts.add("ALIGN", (col, row), (col, row), "CENTRE")

    grid_table.setStyle(ts)
    story.append(grid_table)
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

    doc.build(story)
    return buf.getvalue()
