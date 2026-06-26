from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.types import ExclusionDiagnosis, PatientMetadata, Sex
from app.ui.app_window import AppState

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow

_EXCLUSION_ROWS: tuple[tuple[str, ExclusionDiagnosis], ...] = (
    ("Uraz lub uszkodzenie mózgu", ExclusionDiagnosis.BRAIN_INJURY),
    ("Niepełnosprawność intelektualna", ExclusionDiagnosis.INTELLECTUAL_DISABILITY),
    ("Padaczka", ExclusionDiagnosis.EPILEPSY),
)


class MetadataFormView(ctk.CTkFrame):
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

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="both", expand=True, padx=40, pady=40)

        ctk.CTkLabel(
            form,
            text="Dane dziecka",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 24))

        ctk.CTkLabel(form, text="Wiek:").grid(row=1, column=0, sticky="w", pady=8)
        self._age_var = ctk.StringVar(value="6")
        ctk.CTkOptionMenu(
            form,
            values=["6", "7", "8", "9", "10"],
            variable=self._age_var,
            width=120,
        ).grid(row=1, column=1, sticky="w", pady=8)

        ctk.CTkLabel(form, text="Płeć:").grid(row=2, column=0, sticky="w", pady=8)
        sex_frame = ctk.CTkFrame(form, fg_color="transparent")
        sex_frame.grid(row=2, column=1, sticky="w", pady=8)
        self._sex_var = ctk.StringVar(value="Z")
        ctk.CTkRadioButton(
            sex_frame,
            text="Dziewczynka",
            variable=self._sex_var,
            value="Z",
        ).pack(side="left", padx=(0, 16))
        ctk.CTkRadioButton(
            sex_frame,
            text="Chłopiec",
            variable=self._sex_var,
            value="M",
        ).pack(side="left")

        ctk.CTkLabel(form, text="Diagnozy wykluczające:").grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(16, 8),
        )

        self._exclusion_vars: dict[ExclusionDiagnosis, ctk.BooleanVar] = {}
        for row_offset, (label, diagnosis) in enumerate(_EXCLUSION_ROWS, start=4):
            var = ctk.BooleanVar(value=False)
            self._exclusion_vars[diagnosis] = var
            var.trace_add("write", lambda *_: self._on_exclusion_change())
            ctk.CTkCheckBox(form, text=label, variable=var).grid(
                row=row_offset,
                column=0,
                columnspan=2,
                sticky="w",
                pady=4,
            )

        self._warning_label = ctk.CTkLabel(
            form,
            text="Zaznaczone diagnozy wykluczają udział w badaniu przesiewowym.",
            text_color="#CC0000",
            wraplength=520,
            justify="left",
        )
        self._warning_label.grid(row=7, column=0, columnspan=2, sticky="w", pady=(12, 8))
        self._warning_label.grid_remove()

        self._next_button = ctk.CTkButton(
            form,
            text="Dalej →",
            command=self._on_next,
            width=160,
        )
        self._next_button.grid(row=8, column=0, columnspan=2, sticky="w", pady=(16, 0))

        info_frame = ctk.CTkFrame(form, fg_color="#EBEBEB", corner_radius=6)
        info_frame.grid(row=9, column=0, columnspan=2, sticky="w", pady=(16, 0))
        ctk.CTkLabel(
            info_frame,
            text=(
                "Analiza odbywa się wyłącznie na tym komputerze. Aplikacja nie wysyła żadnych danych do internetu. "
                "Do wyniku przesiewowego wykorzystywany jest sygnał EEG oraz znaczniki zadań; "
                "identyfikatory pacjenta zapisane w nagłówku pliku przez aparat EEG nie są wyświetlane ani zapisywane."
            ),
            wraplength=520,
            justify="left",
            text_color="#555555",
        ).pack(padx=12, pady=8)

        self._restore_from_state()

    def _restore_from_state(self) -> None:
        metadata = self._app_state.metadata
        if metadata is None:
            return
        self._age_var.set(str(metadata.age))
        self._sex_var.set(metadata.sex.value)
        for diagnosis, var in self._exclusion_vars.items():
            var.set(diagnosis in metadata.exclusions)
        self._on_exclusion_change()

    def _on_exclusion_change(self) -> None:
        any_checked = any(var.get() for var in self._exclusion_vars.values())
        if any_checked:
            self._warning_label.grid()
            self._next_button.configure(state="disabled")
        else:
            self._warning_label.grid_remove()
            self._next_button.configure(state="normal")

    def _on_next(self) -> None:
        exclusions = frozenset(
            diagnosis
            for diagnosis, var in self._exclusion_vars.items()
            if var.get()
        )
        self._app_state.metadata = PatientMetadata(
            age=int(self._age_var.get()),
            sex=Sex(self._sex_var.get()),
            exclusions=exclusions,
        )
        from app.ui.views.file_import import FileImportView

        self._app_window.show_view(FileImportView)
