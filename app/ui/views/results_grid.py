from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.cell_layout import (
    CHANNEL_DISPLAY_ORDER,
    TASK_DISPLAY_ORDER,
    cells_for_task_channel,
)
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

_CELL_W = 88
_CELL_H = 56
_CELL_GAP = 6
_CHANNEL_RULE_GAP = 8
_TASK_SECTION_PADY = 4


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
        self._summary_col: ctk.CTkFrame | None = None

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
        self._page = page

        summary_col, grid_col = w.two_column_body(page, left_weight=2, right_weight=3)
        self._summary_col = summary_col

        cat_color = _CATEGORY_COLOR[result.category]
        summary_card = w.surface_card(summary_col)
        summary_card.pack(fill="both", expand=True)

        summary_inner = ctk.CTkFrame(summary_card, fg_color="transparent")
        summary_inner.pack(fill="both", expand=True)
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
        summary_content.grid(row=0, column=1, sticky="nsew", padx=(16, 20), pady=(16, 16))
        summary_content.columnconfigure(0, weight=1)
        summary_inner.rowconfigure(0, weight=1)

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
        self._description_label.grid(row=1, column=0, sticky="ew")

        grid_card = w.surface_card(grid_col)
        grid_card.pack(fill="both", expand=True)

        grid_inner = ctk.CTkFrame(grid_card, fg_color="transparent")
        grid_inner.pack(fill="both", expand=True, padx=12, pady=12)

        self._grid_frame = ctk.CTkFrame(grid_inner, fg_color="transparent")
        self._grid_frame.pack(anchor="n", fill="x")

        self._build_task_grouped_grid(self._grid_frame, result.cells)

        page.bind("<Configure>", self._on_page_configure, add="+")
        summary_col.bind("<Configure>", self._on_page_configure, add="+")
        self.after_idle(self._sync_text_wrap)

        self._app_window.set_footer(
            back_text="\u2190 Nowe badanie",
            back_cmd=self._on_new_study,
            back_visible=True,
            primary_text="Zapisz raport PDF",
            primary_cmd=self._on_save_pdf,
            primary_visible=True,
        )

    def _build_task_grouped_grid(
        self,
        parent: ctk.CTkFrame,
        cells: tuple[CellResult, ...],
    ) -> None:
        parent.grid_columnconfigure(0, weight=1)
        row = 0

        for task_idx, task in enumerate(TASK_DISPLAY_ORDER):
            if task_idx > 0:
                ctk.CTkFrame(
                    parent,
                    height=1,
                    fg_color=t.COLOR_BORDER,
                    corner_radius=0,
                ).grid(row=row, column=0, sticky="ew", pady=(_TASK_SECTION_PADY, _TASK_SECTION_PADY))
                row += 1

            task_label = _TASK_LABELS.get(task, task)
            w.section_title(parent, task_label).grid(
                row=row,
                column=0,
                sticky="w",
                pady=(0, 2),
            )
            row += 1

            clusters = ctk.CTkFrame(parent, fg_color="transparent")
            clusters.grid(row=row, column=0, sticky="w")
            for col in range(3):
                clusters.grid_columnconfigure(col, weight=0)

            for channel_idx, channel in enumerate(CHANNEL_DISPLAY_ORDER):
                channel_cells = cells_for_task_channel(cells, task, channel)
                self._build_channel_cluster(
                    clusters,
                    channel,
                    channel_cells,
                    channel_idx=channel_idx,
                )
            row += 1

    def _build_channel_cluster(
        self,
        parent: ctk.CTkFrame,
        channel: str,
        cells: list[CellResult],
        *,
        channel_idx: int,
    ) -> None:
        grid_col = 0 if channel_idx == 0 else 2
        if channel_idx == 1:
            ctk.CTkFrame(
                parent,
                width=1,
                height=_CELL_H + 22,
                fg_color=t.COLOR_BORDER,
                corner_radius=0,
            ).grid(
                row=0,
                column=1,
                rowspan=2,
                sticky="ns",
                padx=(_CHANNEL_RULE_GAP, _CHANNEL_RULE_GAP),
            )

        ctk.CTkLabel(
            parent,
            text=channel,
            font=t.font_small(),
            text_color=t.COLOR_TEXT_MUTED,
        ).grid(row=0, column=grid_col, sticky="w", pady=(0, 4))

        cells_row = ctk.CTkFrame(parent, fg_color="transparent")
        cells_row.grid(row=1, column=grid_col, sticky="w")

        for cell_idx, cell in enumerate(cells):
            self._make_band_cell(
                cells_row,
                cell,
                pad_right=cell_idx < len(cells) - 1,
            )

    def _make_band_cell(
        self,
        parent: ctk.CTkFrame,
        cell: CellResult,
        *,
        pad_right: bool,
    ) -> None:
        bg = _COLOR_BG[cell.color]
        fg = _COLOR_FG[cell.color]

        cell_frame = ctk.CTkFrame(
            parent,
            fg_color=bg,
            corner_radius=t.CORNER_RADIUS_SM,
            width=_CELL_W,
            height=_CELL_H,
        )
        cell_frame.pack(
            side="left",
            padx=(0, _CELL_GAP if pad_right else 0),
            pady=0,
        )
        cell_frame.pack_propagate(False)
        self._cell_frames.append(cell_frame)

        ctk.CTkLabel(
            cell_frame,
            text=cell.band,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=fg,
        ).place(relx=0.5, rely=0.5, anchor="center")

    def _on_page_configure(self, _event: object | None = None) -> None:
        self.after_idle(self._sync_text_wrap)

    def _sync_text_wrap(self) -> None:
        if self._category_label is None or self._description_label is None:
            return
        width_source = self._summary_col if self._summary_col is not None else self._page
        if width_source is None:
            return
        width_source.update_idletasks()
        width = width_source.winfo_width()
        if width <= 1:
            return
        wrap = max(160, width - 56)
        self._category_label.configure(wraplength=wrap)
        self._description_label.configure(wraplength=wrap)

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
        self._app_state.anonymize_header = True
        self._app_state.cancel_event.clear()

        from app.ui.views.metadata_form import MetadataFormView

        self._app_window.show_view(MetadataFormView)
