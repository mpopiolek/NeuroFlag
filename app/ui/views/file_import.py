from __future__ import annotations

import threading
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.channels import get_missing_canonical
from app.domain.eeg_file import EEGFileError, get_channel_names, read_patient_header_info
from app.ui import theme as t
from app.ui.app_window import AppState
from app.ui.components import widgets as w

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow


class FileImportView(ctk.CTkFrame):
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
        self._app_state.eeg_path = None
        self._selected_path: Path | None = None
        self._validating = False

        container = w.page_container(self)

        w.page_title(container, "Wczytaj plik EEG").pack(anchor="w", pady=(0, 20))

        w.primary_button(
            container,
            text="Wybierz plik EEG",
            command=self._on_load_file,
            width=180,
        ).pack(anchor="w", pady=(0, 12))

        self._path_label = w.body_label(
            container,
            "Nie wybrano pliku",
            secondary=True,
            wraplength=t.WRAP_WIDTH,
            justify="left",
        )
        self._path_label.pack(anchor="w", pady=(0, 8))

        self._anonymize_var = ctk.BooleanVar(value=self._app_state.anonymize_header)
        self._anonymize_var.trace_add(
            "write",
            lambda *_: self._on_anonymize_change(),
        )
        _anon_text = (
            "Wyczyść dane identyfikacyjne z nagłówka pliku przed analizą"
            " (tylko w pamięci — plik nie jest modyfikowany)"
        )
        ctk.CTkCheckBox(
            container,
            text=_anon_text,
            variable=self._anonymize_var,
            font=t.font_body(),
        ).pack(anchor="w", pady=(0, 12))

        self._status_label = w.body_label(
            container,
            "",
            wraplength=t.WRAP_WIDTH,
            justify="left",
        )
        self._status_label.pack(anchor="w", pady=(0, 8))
        self._status_label.pack_forget()

        self._progress = ctk.CTkProgressBar(container, mode="indeterminate", width=420)
        self._progress.pack(anchor="w", pady=(0, 16))
        self._progress.pack_forget()
        self._progress.stop()

        self._id_frame = ctk.CTkFrame(
            container,
            fg_color=t.COLOR_SURFACE,
            corner_radius=t.CORNER_RADIUS,
            border_width=1,
            border_color=t.COLOR_BORDER,
        )
        w.section_title(self._id_frame, "Identyfikacja dziecka (opcjonalnie)").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 8)
        )

        w.body_label(self._id_frame, "Inicjały:").grid(
            row=1, column=0, sticky="w", padx=(14, 12), pady=5
        )
        self._initials_entry = ctk.CTkEntry(
            self._id_frame, width=180, placeholder_text="np. AN", font=t.font_body()
        )
        self._initials_entry.grid(row=1, column=1, sticky="w", pady=5, padx=(0, 14))

        w.body_label(self._id_frame, "Rok urodzenia:").grid(
            row=2, column=0, sticky="w", padx=(14, 12), pady=5
        )
        self._birth_year_entry = ctk.CTkEntry(
            self._id_frame, width=100, placeholder_text="np. 2018", font=t.font_body()
        )
        self._birth_year_entry.grid(row=2, column=1, sticky="w", pady=5, padx=(0, 14))

        w.body_label(self._id_frame, "Własna etykieta:").grid(
            row=3, column=0, sticky="w", padx=(14, 12), pady=(5, 12)
        )
        self._custom_label_entry = ctk.CTkEntry(
            self._id_frame, width=220, placeholder_text="np. klasa 2B", font=t.font_body()
        )
        self._custom_label_entry.grid(row=3, column=1, sticky="w", pady=(5, 12), padx=(0, 14))

        self._id_frame.pack_forget()

        button_row = ctk.CTkFrame(container, fg_color="transparent")
        button_row.pack(anchor="w", pady=(8, 0))

        self._analyze_button = w.primary_button(
            button_row,
            text="Analizuj",
            command=self._on_analyze,
            state="disabled",
            width=140,
        )
        self._analyze_button.pack(side="left", padx=(0, 12))

        w.secondary_button(
            button_row,
            text="← Wróć",
            command=self._on_back,
            width=120,
        ).pack(side="left")

    def _on_anonymize_change(self) -> None:
        self._app_state.anonymize_header = bool(self._anonymize_var.get())

    def _on_load_file(self) -> None:
        if self._validating:
            return
        chosen = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Wybierz plik EEG",
            filetypes=[
                ("Pliki EEG", "*.edf *.vhdr *.eeg *.EEG"),
                ("Wszystkie pliki", "*.*"),
            ],
        )
        if not chosen:
            return

        path = Path(chosen)
        self._selected_path = path
        self._app_state.eeg_path = None
        self._analyze_button.configure(state="disabled")
        self._path_label.configure(text=path.name, text_color=t.COLOR_TEXT)
        self._status_label.pack_forget()
        self._progress.pack(anchor="w", pady=(0, 16))
        self._progress.start()
        self._validating = True

        threading.Thread(
            target=self._validate_worker,
            args=(path,),
            daemon=True,
        ).start()

    def _validate_worker(self, path: Path) -> None:
        from app.domain import eeg_file

        error: EEGFileError | None = None
        channels: list[str] = []
        patient_info: tuple[str | None, str | None] = (None, None)
        try:
            eeg_file.validate_eeg_header(path)
            channels = get_channel_names(path)
            patient_info = read_patient_header_info(path)
        except EEGFileError as exc:
            error = exc
        self.after(0, self._on_result, path, error, channels, patient_info)

    def _on_result(
        self,
        path: Path,
        error: EEGFileError | None,
        channels: list[str],
        patient_info: tuple[str | None, str | None],
    ) -> None:
        self._validating = False
        self._progress.stop()
        self._progress.pack_forget()
        self._status_label.pack(anchor="w", pady=(0, 8))

        if error is not None:
            self._app_state.eeg_path = None
            self._status_label.configure(
                text=f"✗ {error}",
                text_color=t.COLOR_ERROR,
            )
            self._id_frame.pack_forget()
            self._analyze_button.configure(state="disabled")
            return

        self._app_state.eeg_path = path
        self._app_state.available_channels = channels
        self._app_state.channel_overrides = {}

        missing = get_missing_canonical(channels)
        if missing:
            self._status_label.configure(
                text="⚠ Brak C3/O1 — wybór kanału wymagany przed analizą",
                text_color=t.COLOR_WARNING,
            )
        else:
            self._status_label.configure(
                text="✓ Plik wczytany poprawnie",
                text_color=t.COLOR_SUCCESS,
            )

        self._show_identification_section(patient_info)
        self._analyze_button.configure(state="normal")

    def _show_identification_section(
        self, patient_info: tuple[str | None, str | None]
    ) -> None:
        """Pokazuje sekcję identyfikacji. Czyści pola i pre-fill z nagłówka pliku."""
        initials, birth_year = patient_info

        self._initials_entry.delete(0, "end")
        if initials:
            self._initials_entry.insert(0, initials)

        self._birth_year_entry.delete(0, "end")
        if birth_year:
            self._birth_year_entry.insert(0, birth_year)

        self._custom_label_entry.delete(0, "end")

        self._id_frame.pack(anchor="w", fill="x", pady=(0, 12), before=self._analyze_button.master)

    def _on_analyze(self) -> None:
        if not self._app_state.ready_for_analysis():
            return

        assert self._app_state.metadata is not None
        self._app_state.metadata = replace(
            self._app_state.metadata,
            initials=self._initials_entry.get().strip() or None,
            birth_year=self._birth_year_entry.get().strip() or None,
            custom_label=self._custom_label_entry.get().strip() or None,
        )

        missing = get_missing_canonical(self._app_state.available_channels)
        if missing:
            from app.ui.views.channel_mapping import ChannelMappingView

            self._app_window.show_view(ChannelMappingView, missing_channels=missing)
            return

        from app.ui.views.analysis import AnalysisView

        self._app_window.show_view(AnalysisView)

    def _on_back(self) -> None:
        from app.ui.views.metadata_form import MetadataFormView

        self._app_window.show_view(MetadataFormView)
