from __future__ import annotations

from app.domain.types import CellColor, ScreeningCategory

RAG_COLOR_BG: dict[CellColor, str] = {
    CellColor.RED: "#CC0000",
    CellColor.YELLOW: "#F5A800",
    CellColor.GREEN: "#00AA00",
}

RAG_COLOR_FG: dict[CellColor, str] = {
    CellColor.RED: "#FFFFFF",
    CellColor.YELLOW: "#1A1A1A",
    CellColor.GREEN: "#FFFFFF",
}

TASK_LABELS: dict[str, str] = {
    "OO": "Oczy otwarte",
    "OZ": "Oczy zamkni\u0119te",
    "ZP": "Zadanie pami\u0119ciowe",
}

CATEGORY_COLOR: dict[ScreeningCategory, str] = {
    ScreeningCategory.WSKAZANIE: "#CC0000",
    ScreeningCategory.OBSERWACJA: "#A07000",
    ScreeningCategory.BRAK: "#007700",
}
