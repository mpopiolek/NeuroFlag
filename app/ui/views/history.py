from __future__ import annotations

import tkinter.messagebox
from collections.abc import Callable
from functools import partial
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.types import ScreeningCategory
from app.storage.history import StudyRecord
from app.ui import theme as t
from app.ui.app_window import AppState
from app.ui.components import widgets as w
from app.ui.components.rag_colors import CATEGORY_COLOR as _CATEGORY_COLOR

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow

_CATEGORY_BG: dict[ScreeningCategory, str] = _CATEGORY_COLOR
_CATEGORY_FG: dict[ScreeningCategory, str] = {
    ScreeningCategory.WSKAZANIE: t.COLOR_ON_ACCENT,
    ScreeningCategory.OBSERWACJA: t.COLOR_ON_ACCENT,
    ScreeningCategory.BRAK: t.COLOR_ON_ACCENT,
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

        self._outer = w.page_container(self)
        self._outer.columnconfigure(0, weight=1)
        self._outer.rowconfigure(3, weight=1)

        header_row = ctk.CTkFrame(self._outer, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        w.page_title(header_row, "Historia badań").pack(side="left")

        w.secondary_button(
            header_row,
            text="← Wróć do wyników",
            command=self._on_back,
            width=160,
        ).pack(side="right")

        self._filter_label = ctk.CTkLabel(
            self._outer,
            text="",
            font=t.font_small(),
            text_color=t.COLOR_TEXT_SECONDARY,
            anchor="w",
        )
        self._filter_label.grid(row=1, column=0, sticky="ew", pady=(0, 4))

        self._controls_row = ctk.CTkFrame(self._outer, fg_color="transparent")
        self._controls_row.grid(row=2, column=0, sticky="w", pady=(0, 8))

        self._toggle_btn = w.secondary_button(
            self._controls_row,
            text="Pokaż wszystkie",
            width=150,
            command=self._on_toggle_all,
        )

        self._list_frame = ctk.CTkScrollableFrame(self._outer, fg_color="transparent")
        self._list_frame.grid(row=3, column=0, sticky="nsew")
        self._sync_scrollbar = w.bind_auto_hide_scrollbar(self._list_frame)

        self._outer.bind("<Configure>", self._on_outer_configure, add="+")
        self.bind("<Configure>", self._on_outer_configure, add="+")

        self._build_list()
        self.after_idle(self._fit_list_height)

    def _on_outer_configure(self, _event: object | None = None) -> None:
        self.after_idle(self._fit_list_height)

    def _fit_list_height(self) -> None:
        self.update_idletasks()
        list_y = self._list_frame.winfo_y()
        outer_h = self._outer.winfo_height()
        if list_y <= 0 or outer_h <= 0:
            return
        available = outer_h - list_y - 4
        if available < 80:
            return
        current = self._list_frame.cget("height")
        if current != available:
            self._list_frame.configure(height=available)
        self._sync_scrollbar()

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
            w.body_label(
                self._list_frame,
                "Brak zapisanych badań dla tego dziecka.",
                secondary=True,
            ).pack(anchor="w", pady=16)
            self.after_idle(self._fit_list_height)
            return

        for record in records:
            self._make_row(record)
        self.after_idle(self._fit_list_height)

    def _on_toggle_all(self) -> None:
        self._show_all = not self._show_all
        self._build_list()

    def _make_row(self, record: StudyRecord) -> None:
        row = ctk.CTkFrame(
            self._list_frame,
            fg_color=t.COLOR_ROW_BG,
            corner_radius=t.CORNER_RADIUS_SM,
            border_width=1,
            border_color=t.COLOR_BORDER,
        )
        row.pack(fill="x", pady=(0, 8))
        row.columnconfigure(1, weight=1)

        date_str = record.analyzed_at.strftime("%Y-%m-%d %H:%M")
        ctk.CTkLabel(
            row,
            text=date_str,
            font=t.font_small(),
            text_color=t.COLOR_TEXT_SECONDARY,
            width=130,
            anchor="w",
        ).grid(row=0, column=0, padx=(12, 6), pady=10, sticky="w")

        ctk.CTkLabel(
            row,
            text=record.display_name,
            font=t.font_body(),
            text_color=t.COLOR_TEXT,
            anchor="w",
        ).grid(row=0, column=1, padx=6, pady=10, sticky="w")

        category = _category_from_value(record.category)
        cat_bg = _CATEGORY_BG.get(category, t.COLOR_TEXT_MUTED) if category else t.COLOR_TEXT_MUTED
        cat_fg = _CATEGORY_FG.get(category, t.COLOR_ON_ACCENT) if category else t.COLOR_ON_ACCENT
        cat_short = record.category.split(" ")[0]
        ctk.CTkLabel(
            row,
            text=cat_short,
            font=t.font_caption(),
            text_color=cat_fg,
            fg_color=cat_bg,
            corner_radius=4,
            width=84,
        ).grid(row=0, column=2, padx=6, pady=10)

        edit_btn = w.secondary_button(
            row,
            text="Edytuj",
            width=68,
            command=partial(self._on_edit, record),
        )
        edit_btn.grid(row=0, column=3, padx=(0, 4), pady=10)

        delete_btn = w.danger_button(
            row,
            text="Usuń",
            width=68,
            command=partial(self._on_delete, record.id),
        )
        delete_btn.grid(row=0, column=4, padx=(0, 12), pady=10)

    def _on_edit(self, record: StudyRecord) -> None:
        dialog = _EditStudyDialog(
            self.winfo_toplevel(),
            record=record,
            on_save=self._save_identification,
        )
        dialog.wait_window()

    def _save_identification(
        self,
        study_id: int,
        *,
        initials: str | None,
        birth_year: str | None,
        custom_label: str | None,
    ) -> None:
        store = self._app_state.history_store
        assert store is not None
        updated = store.update_identification(
            study_id,
            initials=initials,
            birth_year=birth_year,
            custom_label=custom_label,
        )
        if not updated:
            tkinter.messagebox.showerror(
                "Edycja rekordu",
                "Nie znaleziono rekordu w historii.",
            )
            return
        self._show_all = True
        self._build_list()

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


class _EditStudyDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master: ctk.CTk,
        *,
        record: StudyRecord,
        on_save: Callable[..., None],
    ) -> None:
        super().__init__(master)
        self._record = record
        self._on_save = on_save

        self.title("Edytuj identyfikację")
        self.resizable(False, False)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew", padx=24, pady=(20, 8))

        w.section_title(body, "Identyfikacja dziecka").pack(anchor="w", pady=(0, 12))

        self._initials_entry = self._labeled_entry(
            body, "Inicjały", record.initials or ""
        )
        self._birth_year_entry = self._labeled_entry(
            body, "Rok urodzenia", record.birth_year or ""
        )
        self._custom_label_entry = self._labeled_entry(
            body, "Własna etykieta", record.custom_label or ""
        )

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 20))

        w.primary_button(footer, text="Zapisz", command=self._submit, width=110).pack(
            side="right"
        )
        w.secondary_button(
            footer,
            text="Anuluj",
            command=self.destroy,
            width=110,
        ).pack(side="right", padx=(0, 8))

        self.bind("<Return>", lambda _event: self._submit())
        self.bind("<Escape>", lambda _event: self.destroy())

        self.update_idletasks()
        self.grab_set()
        self._initials_entry.focus_set()
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))

    def _labeled_entry(self, parent: ctk.CTkFrame, label: str, value: str) -> ctk.CTkEntry:
        w.body_label(parent, label).pack(anchor="w", pady=(0, 2))
        entry = ctk.CTkEntry(parent, width=360, font=t.font_body())
        entry.pack(anchor="w", pady=(0, 8))
        entry.insert(0, value)
        return entry

    def _field_value(self, entry: ctk.CTkEntry) -> str | None:
        value = entry.get().strip()
        return value or None

    def _submit(self) -> None:
        save = self._on_save
        assert callable(save)
        save(
            self._record.id,
            initials=self._field_value(self._initials_entry),
            birth_year=self._field_value(self._birth_year_entry),
            custom_label=self._field_value(self._custom_label_entry),
        )
        self.destroy()
