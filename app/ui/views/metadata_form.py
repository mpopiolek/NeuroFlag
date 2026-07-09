from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.types import (
    ClinicalDiagnosis,
    ExclusionDiagnosis,
    PatientMetadata,
    Sex,
)
from app.ui import context_copy
from app.ui import theme as t
from app.ui.app_window import AppState
from app.ui.components import widgets as w

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow

_OTHER_NOTE_MAX_LEN = 100

_CLINICAL_ROWS: tuple[tuple[str, ClinicalDiagnosis], ...] = (
    ("ASD / autyzm", ClinicalDiagnosis.ASD),
    ("ADHD", ClinicalDiagnosis.ADHD),
    ("Depresja lub zaburzenia lękowe", ClinicalDiagnosis.DEPRESSION_ANXIETY),
    ("Dysleksja", ClinicalDiagnosis.DYSLEXIA),
    ("Inne", ClinicalDiagnosis.OTHER),
)

_EXCLUSION_ROWS: tuple[tuple[str, ExclusionDiagnosis], ...] = (
    ("Uraz lub uszkodzenie mózgu", ExclusionDiagnosis.BRAIN_INJURY),
    ("Niepełnosprawność intelektualna", ExclusionDiagnosis.INTELLECTUAL_DISABILITY),
    ("Padaczka", ExclusionDiagnosis.EPILEPSY),
)

_ROW_AGE_SEX = 0
_ROW_CLINICAL_LABEL = 1
_ROW_CLINICAL_START = 2

_AGE_PLACEHOLDER = "Wybierz"
_AGE_VALUES = ("6", "7", "8", "9", "10")


class MetadataFormView(ctk.CTkFrame):
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

        page = w.page_container(self)
        form_col, context_col = w.two_column_body(page)

        card = w.surface_card(form_col)
        card.pack(fill="both", expand=True)

        card_inner = ctk.CTkFrame(card, fg_color="transparent")
        card_inner.pack(fill="both", expand=True, padx=20, pady=20)
        card_inner.rowconfigure(1, weight=1)
        card_inner.columnconfigure(0, weight=1)

        w.section_title(card_inner, "Dane dziecka").grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )

        body = ctk.CTkScrollableFrame(card_inner, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        self._body = body

        age_sex_frame = ctk.CTkFrame(body, fg_color="transparent")
        age_sex_frame.grid(row=_ROW_AGE_SEX, column=0, sticky="w", pady=(0, 8))

        w.body_label(age_sex_frame, "Wiek:").pack(side="left")
        self._age_var = ctk.StringVar(value=_AGE_PLACEHOLDER)
        self._age_var.trace_add("write", lambda *_: self._update_continue_state())
        ctk.CTkOptionMenu(
            age_sex_frame,
            values=[_AGE_PLACEHOLDER, *_AGE_VALUES],
            variable=self._age_var,
            width=96,
            font=t.font_body(),
        ).pack(side="left", padx=(4, 20))

        w.body_label(age_sex_frame, "Płeć:").pack(side="left")
        self._sex_var = ctk.StringVar(value="")
        self._sex_var.trace_add("write", lambda *_: self._update_continue_state())
        ctk.CTkRadioButton(
            age_sex_frame,
            text="Dziewczynka",
            variable=self._sex_var,
            value="Z",
            font=t.font_body(),
        ).pack(side="left", padx=(8, 12))
        ctk.CTkRadioButton(
            age_sex_frame,
            text="Chłopiec",
            variable=self._sex_var,
            value="M",
            font=t.font_body(),
        ).pack(side="left")

        w.body_label(body, "Zdiagnozowane wcześniej (opcjonalnie):").grid(
            row=_ROW_CLINICAL_LABEL,
            column=0,
            sticky="w",
            pady=(8, 6),
        )

        self._clinical_vars: dict[ClinicalDiagnosis, ctk.BooleanVar] = {}
        for row_offset, (label, diagnosis) in enumerate(
            _CLINICAL_ROWS, start=_ROW_CLINICAL_START
        ):
            var = ctk.BooleanVar(value=False)
            self._clinical_vars[diagnosis] = var
            var.trace_add("write", lambda *_: self._on_clinical_change())
            ctk.CTkCheckBox(
                body,
                text=label,
                variable=var,
                font=t.font_body(),
            ).grid(
                row=row_offset,
                column=0,
                sticky="w",
                pady=2,
            )

        self._other_note_frame = ctk.CTkFrame(body, fg_color="transparent")
        w.body_label(self._other_note_frame, "Opis (Inne):").grid(
            row=0, column=0, sticky="w", padx=(20, 8)
        )
        self._other_note_entry = ctk.CTkEntry(
            self._other_note_frame,
            width=300,
            font=t.font_body(),
            placeholder_text="Krótki opis diagnozy",
        )
        self._other_note_entry.grid(row=0, column=1, sticky="w")

        exclusion_label_row = _ROW_CLINICAL_START + len(_CLINICAL_ROWS) + 1
        w.body_label(body, "Diagnozy wykluczające:").grid(
            row=exclusion_label_row,
            column=0,
            sticky="w",
            pady=(12, 6),
        )

        self._exclusion_vars: dict[ExclusionDiagnosis, ctk.BooleanVar] = {}
        for row_offset, (label, exclusion) in enumerate(
            _EXCLUSION_ROWS, start=exclusion_label_row + 1
        ):
            var = ctk.BooleanVar(value=False)
            self._exclusion_vars[exclusion] = var
            var.trace_add("write", lambda *_: self._on_exclusion_change())
            ctk.CTkCheckBox(
                body,
                text=label,
                variable=var,
                font=t.font_body(),
            ).grid(
                row=row_offset,
                column=0,
                sticky="w",
                pady=2,
            )

        warning_row = exclusion_label_row + 1 + len(_EXCLUSION_ROWS)
        self._warning_label = ctk.CTkLabel(
            body,
            text="Zaznaczone diagnozy wykluczają udział w badaniu przesiewowym.",
            text_color=t.COLOR_ERROR,
            font=t.font_body(),
            wraplength=320,
            justify="left",
            anchor="w",
        )
        self._warning_label.grid(
            row=warning_row, column=0, sticky="ew", pady=(8, 6)
        )
        self._warning_label.grid_remove()

        self._sync_scrollbar = w.bind_auto_hide_scrollbar(body)
        body.bind("<Configure>", self._on_body_configure, add="+")
        self.after_idle(self._sync_warning_wrap)

        w.context_panel(
            context_col,
            "Prywatność i dane lokalne",
            context_copy.CONTEXT_METADATA,
        ).pack(fill="both", expand=True, anchor="n")

        self._app_window.set_footer(
            primary_text="Dalej →",
            primary_cmd=self._on_continue,
            primary_visible=True,
            back_visible=False,
        )

        self._restore_from_state()
        self._update_continue_state()

    def _is_age_selected(self) -> bool:
        return self._age_var.get() in _AGE_VALUES

    def _is_sex_selected(self) -> bool:
        return self._sex_var.get() in {Sex.Z.value, Sex.M.value}

    def _update_continue_state(self) -> None:
        blocked = (
            not self._is_age_selected()
            or not self._is_sex_selected()
            or any(var.get() for var in self._exclusion_vars.values())
        )
        self._app_window.set_footer_primary_state("disabled" if blocked else "normal")

    def _on_body_configure(self, _event: object | None = None) -> None:
        self.after_idle(self._sync_warning_wrap)

    def _sync_warning_wrap(self) -> None:
        self._body.update_idletasks()
        width = self._body.winfo_width()
        if width <= 1:
            return
        wrap = max(200, width - 16)
        self._warning_label.configure(wraplength=wrap)

    def _on_clinical_change(self) -> None:
        other_var = self._clinical_vars[ClinicalDiagnosis.OTHER]
        if other_var.get():
            self._other_note_frame.grid(
                row=_ROW_CLINICAL_START + len(_CLINICAL_ROWS),
                column=0,
                sticky="w",
                pady=(0, 6),
            )
        else:
            self._other_note_frame.grid_remove()
            self._other_note_entry.delete(0, "end")
        self._sync_scrollbar()

    def _restore_from_state(self) -> None:
        metadata = self._app_state.metadata
        if metadata is None:
            return
        self._age_var.set(str(metadata.age))
        self._sex_var.set(metadata.sex.value)
        for diagnosis, var in self._clinical_vars.items():
            var.set(diagnosis in metadata.diagnoses)
        self._other_note_entry.delete(0, "end")
        if metadata.other_diagnosis_note:
            self._other_note_entry.insert(0, metadata.other_diagnosis_note)
        self._on_clinical_change()
        for exclusion, var in self._exclusion_vars.items():
            var.set(exclusion in metadata.exclusions)
        self._on_exclusion_change()

    def _on_exclusion_change(self) -> None:
        any_checked = any(var.get() for var in self._exclusion_vars.values())
        if any_checked:
            self._warning_label.grid()
            self.after_idle(self._sync_warning_wrap)
            self._sync_scrollbar()
        else:
            self._warning_label.grid_remove()
            self._sync_scrollbar()
        self._update_continue_state()

    def _read_other_note(self) -> str | None:
        if not self._clinical_vars[ClinicalDiagnosis.OTHER].get():
            return None
        note = self._other_note_entry.get().strip()
        if not note:
            return None
        return str(note[:_OTHER_NOTE_MAX_LEN])

    def _on_continue(self) -> None:
        if not self._is_age_selected() or not self._is_sex_selected():
            return
        exclusions = frozenset(
            exclusion
            for exclusion, var in self._exclusion_vars.items()
            if var.get()
        )
        diagnoses = frozenset(
            clinical
            for clinical, var in self._clinical_vars.items()
            if var.get()
        )
        self._app_state.metadata = PatientMetadata(
            age=int(self._age_var.get()),
            sex=Sex(self._sex_var.get()),
            exclusions=exclusions,
            diagnoses=diagnoses,
            other_diagnosis_note=self._read_other_note(),
        )
        from app.ui.views.file_import import FileImportView

        self._app_window.show_view(FileImportView)
