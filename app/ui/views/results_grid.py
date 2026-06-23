from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.types import CellColor, CellResult, ScreeningCategory
from app.ui.app_window import AppState
from app.ui.components.rag_colors import (
    CATEGORY_COLOR as _CATEGORY_COLOR,
    RAG_COLOR_BG as _COLOR_BG,
    RAG_COLOR_FG as _COLOR_FG,
    TASK_LABELS as _TASK_LABELS,
)

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow

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
            ctk.CTkLabel(
                self,
                text="Brak wynik\u00f3w analizy. "
                "Wr\u00f3\u0107 do importu i spr\u00f3buj ponownie.",
                text_color="#CC0000",
            ).pack(padx=40, pady=40, anchor="w")
            ctk.CTkButton(
                self,
                text="\u2190 Powr\u00f3t do importu",
                command=self._on_new_study,
                width=160,
            ).pack(padx=40, anchor="w")
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

        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(anchor="w", pady=(0, 0))

        ctk.CTkButton(
            btn_row,
            text="\u2190 Nowe badanie",
            command=self._on_new_study,
            width=160,
        ).pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            btn_row,
            text="Zapisz raport PDF",
            command=self._on_save_pdf,
            width=200,
        ).pack(side="left")

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

    def _on_save_pdf(self) -> None:
        if self._app_state.analysis_result is None or self._app_state.metadata is None:
            return  # structurally unreachable; satisfies mypy --strict

        result = self._app_state.analysis_result
        metadata = self._app_state.metadata
        norms_config = self._app_state.norms_config

        default_name = f"neuroflag_{result.analyzed_at.strftime('%Y-%m-%d')}.pdf"
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=default_name,
        )
        if not path:
            return

        try:
            from app.reports.pdf_generator import generate_report

            pdf_bytes = generate_report(metadata, result, norms_config)
            Path(path).write_bytes(pdf_bytes)
            messagebox.showinfo("Raport zapisany", f"Raport PDF zapisano w:\n{path}")
        except Exception as exc:
            messagebox.showerror(
                "B\u0142\u0105d zapisu PDF",
                f"Nie mo\u017cna zapisa\u0107 raportu:\n{exc}",
            )

    def _on_new_study(self) -> None:
        self._app_state.analysis_result = None
        self._app_state.eeg_path = None
        self._app_state.metadata = None
        self._app_state.cancel_event.clear()

        from app.ui.views.metadata_form import MetadataFormView

        self._app_window.show_view(MetadataFormView)
