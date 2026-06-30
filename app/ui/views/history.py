from __future__ import annotations

import tkinter.messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.types import ScreeningCategory
from app.storage.history import StudyRecord
from app.ui.app_window import AppState
from app.ui.components.rag_colors import CATEGORY_COLOR as _CATEGORY_COLOR

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow

_CATEGORY_BG: dict[ScreeningCategory, str] = _CATEGORY_COLOR
_CATEGORY_FG: dict[ScreeningCategory, str] = {
    ScreeningCategory.WSKAZANIE: "#FFFFFF",
    ScreeningCategory.OBSERWACJA: "#FFFFFF",
    ScreeningCategory.BRAK: "#FFFFFF",
}


def _category_from_value(value: str) -> ScreeningCategory | None:
    try:
        return ScreeningCategory(value)
    except ValueError:
        return None


class HistoryView(ctk.CTkFrame):
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
        self._show_all = False

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=40, pady=30)

        header_row = ctk.CTkFrame(outer, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(
            header_row,
            text="Historia badań",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(side="left")

        ctk.CTkButton(
            header_row,
            text="← Wróć do wyników",
            command=self._on_back,
            width=160,
        ).pack(side="right")

        self._filter_label = ctk.CTkLabel(
            outer,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#555555",
            anchor="w",
        )
        self._filter_label.pack(fill="x", pady=(0, 4))

        # Stały wiersz na przycisk toggle — unika problemu z before= i CTkScrollableFrame
        self._controls_row = ctk.CTkFrame(outer, fg_color="transparent")
        self._controls_row.pack(anchor="w", pady=(0, 8))

        self._toggle_btn = ctk.CTkButton(
            self._controls_row,
            text="Pokaż wszystkie",
            width=140,
            fg_color="transparent",
            border_width=1,
            text_color="#333333",
            hover_color="#EBEBEB",
            command=self._on_toggle_all,
        )

        self._list_frame = ctk.CTkScrollableFrame(outer, fg_color="transparent")
        self._list_frame.pack(fill="both", expand=True)

        self._build_list()

    def _patient_filter_label(self) -> str:
        metadata = self._app_state.metadata
        if metadata is None:
            return ""
        parts: list[str] = []
        if metadata.initials:
            parts.append(metadata.initials)
        if metadata.birth_year:
            parts.append(metadata.birth_year)
        if metadata.custom_label:
            parts.append(metadata.custom_label)
        return " / ".join(parts) if parts else ""

    def _build_list(self) -> None:
        for widget in self._list_frame.winfo_children():
            widget.destroy()

        store = self._app_state.history_store
        assert store is not None
        metadata = self._app_state.metadata

        if self._show_all or metadata is None:
            records = store.list_recent()
            filter_desc = "Wszystkie badania"
            self._toggle_btn.configure(text="Pokaż tylko to dziecko")
        else:
            records = store.list_for_patient(
                initials=metadata.initials,
                birth_year=metadata.birth_year,
                custom_label=metadata.custom_label,
            )
            label = self._patient_filter_label()
            filter_desc = f"Badania: {label}" if label else "Wszystkie badania"

        self._filter_label.configure(text=filter_desc)

        has_patient_fields = metadata is not None and (
            metadata.initials or metadata.birth_year or metadata.custom_label
        )
        if has_patient_fields:
            self._toggle_btn.pack(anchor="w")
        else:
            self._toggle_btn.pack_forget()

        if not records:
            ctk.CTkLabel(
                self._list_frame,
                text="Brak zapisanych badań dla tego dziecka.",
                text_color="#888888",
            ).pack(anchor="w", pady=16)
            return

        for record in records:
            self._make_row(record)

    def _on_toggle_all(self) -> None:
        self._show_all = not self._show_all
        self._build_list()

    def _make_row(self, record: StudyRecord) -> None:
        row = ctk.CTkFrame(
            self._list_frame,
            fg_color="#F5F5F5",
            corner_radius=6,
        )
        row.pack(fill="x", pady=(0, 6))
        row.columnconfigure(1, weight=1)

        date_str = record.analyzed_at.strftime("%Y-%m-%d %H:%M")
        ctk.CTkLabel(
            row,
            text=date_str,
            font=ctk.CTkFont(size=12),
            text_color="#555555",
            width=130,
            anchor="w",
        ).grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")

        ctk.CTkLabel(
            row,
            text=record.display_name,
            font=ctk.CTkFont(size=13),
            anchor="w",
        ).grid(row=0, column=1, padx=6, pady=8, sticky="w")

        category = _category_from_value(record.category)
        cat_bg = _CATEGORY_BG.get(category, "#888888") if category else "#888888"
        cat_fg = _CATEGORY_FG.get(category, "#FFFFFF") if category else "#FFFFFF"
        cat_short = record.category.split(" ")[0]  # "Wskazanie" / "Uważna" / "Brak"
        ctk.CTkLabel(
            row,
            text=cat_short,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=cat_fg,
            fg_color=cat_bg,
            corner_radius=4,
            width=80,
        ).grid(row=0, column=2, padx=6, pady=8)

        ctk.CTkButton(
            row,
            text="Usuń",
            width=60,
            fg_color="#CC3333",
            hover_color="#AA2222",
            command=lambda rid=record.id: self._on_delete(rid),
        ).grid(row=0, column=3, padx=(6, 10), pady=8)

    def _on_delete(self, study_id: int) -> None:
        confirmed = tkinter.messagebox.askyesno(
            "Usuń badanie",
            "Czy na pewno chcesz usunąć ten rekord z historii?\nOperacji nie można cofnąć.",
        )
        if not confirmed:
            return
        store = self._app_state.history_store
        assert store is not None
        store.delete(study_id)
        self._build_list()

    def _on_back(self) -> None:
        from app.ui.views.results_grid import ResultsGridView

        self._app_window.show_view(ResultsGridView)
