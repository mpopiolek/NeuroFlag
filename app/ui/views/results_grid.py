from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.types import CellColor, CellResult, ScreeningCategory
from app.ui.app_window import AppState

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow

_TASK_LABELS: dict[str, str] = {
    "OO": "Oczy otwarte",
    "OZ": "Oczy zamkni\u0119te",
    "ZP": "Zadanie pami\u0119ciowe",
}

_COLOR_BG: dict[CellColor, str] = {
    CellColor.RED: "#CC0000",
    CellColor.YELLOW: "#F5A800",
    CellColor.GREEN: "#00AA00",
}

_COLOR_FG: dict[CellColor, str] = {
    CellColor.RED: "#FFFFFF",
    CellColor.YELLOW: "#1A1A1A",
    CellColor.GREEN: "#FFFFFF",
}

_CATEGORY_COLOR: dict[ScreeningCategory, str] = {
    ScreeningCategory.WSKAZANIE: "#CC0000",
    ScreeningCategory.OBSERWACJA: "#A07000",
    ScreeningCategory.BRAK: "#007700",
}

_CELL_W = 130
_CELL_H = 82


class ResultsGridView(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTk,
        app_window: AppWindow,
        app_state: AppState,
        **kwargs: object,
    ) -> None:
        super().__init__(master, **kwargs)
        self._app_window = app_window
        self._app_state = app_state

        if app_state.analysis_result is None:
            return
        result = app_state.analysis_result

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=30)

        cat_color = _CATEGORY_COLOR[result.category]
        ctk.CTkLabel(
            container,
            text=result.category.value,
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=cat_color,
        ).pack(anchor="w", pady=(0, 8))

        ctk.CTkLabel(
            container,
            text=result.description,
            wraplength=820,
            justify="left",
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", pady=(0, 22))

        grid_frame = ctk.CTkFrame(container, fg_color="transparent")
        grid_frame.pack(anchor="w", pady=(0, 24))

        for col in range(5):
            grid_frame.columnconfigure(col, weight=1, minsize=_CELL_W + 8)

        for idx, cell in enumerate(result.cells):
            self._make_cell(grid_frame, cell, row=idx // 5, col=idx % 5)

        ctk.CTkButton(
            container,
            text="\u2190 Nowe badanie",
            command=self._on_new_study,
            width=160,
        ).pack(anchor="w")

    def _make_cell(
        self,
        parent: ctk.CTkFrame,
        cell: CellResult,
        row: int,
        col: int,
    ) -> None:
        bg = _COLOR_BG[cell.color]
        fg = _COLOR_FG[cell.color]
        task_label = _TASK_LABELS.get(cell.task, cell.task)

        cell_frame = ctk.CTkFrame(
            parent,
            fg_color=bg,
            corner_radius=8,
            width=_CELL_W,
            height=_CELL_H,
        )
        cell_frame.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        cell_frame.grid_propagate(False)

        ctk.CTkLabel(
            cell_frame,
            text=cell.channel,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=fg,
        ).place(relx=0.5, rely=0.2, anchor="center")

        ctk.CTkLabel(
            cell_frame,
            text=task_label,
            font=ctk.CTkFont(size=9),
            text_color=fg,
        ).place(relx=0.5, rely=0.52, anchor="center")

        ctk.CTkLabel(
            cell_frame,
            text=cell.band,
            font=ctk.CTkFont(size=10),
            text_color=fg,
        ).place(relx=0.5, rely=0.8, anchor="center")

    def _on_new_study(self) -> None:
        self._app_state.analysis_result = None
        self._app_state.eeg_path = None
        self._app_state.metadata = None
        self._app_state.cancel_event.clear()

        from app.ui.views.metadata_form import MetadataFormView

        self._app_window.show_view(MetadataFormView)
