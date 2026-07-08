from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.types import CellResult
from app.ui import theme as t
from app.ui.app_window import AppState
from app.ui.components import widgets as w
from app.ui.components.rag_colors import (
    CATEGORY_COLOR as _CATEGORY_COLOR,
)
from app.ui.components.rag_colors import (
    RAG_COLOR_BG as _COLOR_BG,
)
from app.ui.components.rag_colors import (
    RAG_COLOR_FG as _COLOR_FG,
)
from app.ui.components.rag_colors import (
    TASK_LABELS as _TASK_LABELS,
)

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow

_CELL_W_MIN = 120
_CELL_H_MIN = 80
_CELL_W_MAX = 150
_CELL_H_MAX = 95
_CELL_PAD = 5
_GRID_COLS = 5


class ResultsGridView(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        app_window: AppWindow,
        app_state: AppState,
        **kwargs: object,
    ) -> None:
        super().__init__(master, **kwargs)
        self._app_window = app_window
        self._app_state = app_state
        self._grid_frame: ctk.CTkFrame | None = None
        self._cell_frames: list[ctk.CTkFrame] = []
        self._category_label: ctk.CTkLabel | None = None
        self._description_label: ctk.CTkLabel | None = None
        self._page: ctk.CTkFrame | None = None

        if app_state.analysis_result is None:
            container = w.page_container(self)
            error_label = w.body_label(
                container,
                "Brak wynik\u00f3w analizy. Wr\u00f3\u0107 do importu i spr\u00f3buj ponownie.",
                wraplength=t.WRAP_WIDTH,
            )
            error_label.configure(text_color=t.COLOR_ERROR)
            error_label.pack(anchor="w")
            self._app_window.set_footer(
                back_text="\u2190 Powr\u00f3t do importu",
                back_cmd=self._on_new_study,
                back_visible=True,
            )
            return
        result = app_state.analysis_result

        page = w.page_container(self)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)
        self._page = page

        cat_color = _CATEGORY_COLOR[result.category]
        summary_card = w.surface_card(page)
        summary_card.grid(row=0, column=0, sticky="ew", pady=(0, 16))

        summary_inner = ctk.CTkFrame(summary_card, fg_color="transparent")
        summary_inner.pack(fill="x")
        summary_inner.columnconfigure(1, weight=1)

        stripe = ctk.CTkFrame(
            summary_inner,
            fg_color=cat_color,
            width=4,
            corner_radius=0,
        )
        stripe.grid(row=0, column=0, rowspan=2, sticky="ns")
        stripe.grid_propagate(False)

        summary_content = ctk.CTkFrame(summary_inner, fg_color="transparent")
        summary_content.grid(row=0, column=1, sticky="ew", padx=(16, 20), pady=(16, 8))
        summary_content.columnconfigure(0, weight=1)

        self._category_label = ctk.CTkLabel(
            summary_content,
            text=result.category.value,
            font=t.font_heading(),
            text_color=t.COLOR_TEXT,
            anchor="w",
            justify="left",
        )
        self._category_label.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self._description_label = w.body_label(
            summary_content,
            result.description,
            justify="left",
        )
        self._description_label.grid(row=1, column=0, sticky="ew", pady=(0, 16))

        grid_card = w.surface_card(page)
        grid_card.grid(row=1, column=0, sticky="nsew")

        grid_inner = ctk.CTkFrame(grid_card, fg_color="transparent")
        grid_inner.pack(fill="both", expand=True, padx=12, pady=12)

        self._grid_frame = ctk.CTkFrame(grid_inner, fg_color="transparent")
        self._grid_frame.pack(fill="both", expand=True)

        for col in range(_GRID_COLS):
            self._grid_frame.columnconfigure(col, weight=1, minsize=_CELL_W_MIN + _CELL_PAD * 2)

        for idx, cell in enumerate(result.cells):
            self._make_cell(self._grid_frame, cell, row=idx // _GRID_COLS, col=idx % _GRID_COLS)

        page.bind("<Configure>", self._on_page_configure, add="+")
        self._grid_frame.bind("<Configure>", self._on_grid_configure, add="+")
        grid_card.bind("<Configure>", self._on_grid_configure, add="+")
        self.after_idle(self._sync_text_wrap)
        self.after_idle(self._update_cell_sizes)

        self._app_window.set_footer(
            back_text="\u2190 Nowe badanie",
            back_cmd=self._on_new_study,
            back_visible=True,
            primary_text="Zapisz raport PDF",
            primary_cmd=self._on_save_pdf,
            primary_visible=True,
        )

    def _on_page_configure(self, _event: object | None = None) -> None:
        self.after_idle(self._sync_text_wrap)

    def _sync_text_wrap(self) -> None:
        if self._page is None or self._category_label is None or self._description_label is None:
            return
        self._page.update_idletasks()
        width = self._page.winfo_width()
        if width <= 1:
            return
        wrap = max(200, width - 72)
        self._category_label.configure(wraplength=wrap)
        self._description_label.configure(wraplength=wrap)

    def _on_grid_configure(self, _event: object | None = None) -> None:
        self.after_idle(self._update_cell_sizes)

    def _update_cell_sizes(self) -> None:
        if self._grid_frame is None:
            return
        self._grid_frame.update_idletasks()
        frame_w = self._grid_frame.winfo_width()
        if frame_w <= 1:
            return
        pad_total = _CELL_PAD * 2 * _GRID_COLS
        cell_w = (frame_w - pad_total) // _GRID_COLS
        cell_w = max(_CELL_W_MIN, min(_CELL_W_MAX, cell_w))
        cell_h = max(_CELL_H_MIN, min(_CELL_H_MAX, int(cell_w * 0.65)))
        min_col = cell_w + _CELL_PAD * 2
        for col in range(_GRID_COLS):
            self._grid_frame.columnconfigure(col, weight=1, minsize=min_col)
        for cell_frame in self._cell_frames:
            cell_frame.configure(width=cell_w, height=cell_h)

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
            corner_radius=t.CORNER_RADIUS_SM,
            width=_CELL_W_MIN,
            height=_CELL_H_MIN,
        )
        cell_frame.grid(row=row, column=col, padx=_CELL_PAD, pady=_CELL_PAD, sticky="nsew")
        cell_frame.grid_propagate(False)
        self._cell_frames.append(cell_frame)

        ctk.CTkLabel(
            cell_frame,
            text=cell.channel,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=fg,
        ).place(relx=0.5, rely=0.2, anchor="center")

        ctk.CTkLabel(
            cell_frame,
            text=task_label,
            font=t.font_caption(),
            text_color=fg,
        ).place(relx=0.5, rely=0.52, anchor="center")

        ctk.CTkLabel(
            cell_frame,
            text=cell.band,
            font=t.font_small(),
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

            pdf_bytes = generate_report(
                metadata,
                result,
                norms_config,
                recording_date=self._app_state.recording_date,
            )
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
        self._app_state.recording_date = None
        self._app_state.metadata = None
        self._app_state.cancel_event.clear()

        from app.ui.views.metadata_form import MetadataFormView

        self._app_window.show_view(MetadataFormView)
