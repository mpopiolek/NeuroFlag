from __future__ import annotations

import threading
from dataclasses import replace
from datetime import date
from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.channels import get_missing_canonical
from app.domain.eeg_file import (
    EEGFileError,
    get_channel_names,
    read_patient_header_info,
    read_recording_date,
)
from app.domain.errors import PipelineError
from app.ui import context_copy
from app.ui import theme as t
from app.ui.app_window import AppState
from app.ui.components import widgets as w
from app.ui.views.analysis import format_pipeline_error

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow

_ROW_TITLE = 0
_ROW_PICK = 1
_ROW_PATH = 2
_ROW_ANON = 3
_ROW_STATUS = 4
_ROW_PROGRESS = 5
_ROW_ID = 6


class FileImportView(ctk.CTkFrame):
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
        self._selected_path = self._app_state.eeg_path
        self._validating = False

        page = w.page_container(self)
        form_col, context_col = w.two_column_body(page)

        card = w.surface_card(form_col)
        card.pack(fill="both", expand=True)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=20)
        inner.columnconfigure(0, weight=1)

        w.section_title(inner, "Wczytaj plik EEG").grid(
            row=_ROW_TITLE, column=0, sticky="w", pady=(0, 16)
        )

        self._load_btn = w.primary_button(
            inner,
            text="Wybierz plik EEG",
            command=self._on_load_file,
            width=180,
        )
        self._load_btn.grid(row=_ROW_PICK, column=0, sticky="w", pady=(0, 12))

        self._path_label = w.body_label(
            inner,
            "Nie wybrano pliku",
            secondary=True,
            wraplength=t.WRAP_WIDTH,
            justify="left",
        )
        self._path_label.grid(row=_ROW_PATH, column=0, sticky="w", pady=(0, 8))

        self._anonymize_var = ctk.BooleanVar(value=self._app_state.anonymize_header)
        self._anonymize_var.trace_add(
            "write",
            lambda *_: self._on_anonymize_change(),
        )
        _anon_text = (
            "Wyczyść dane identyfikacyjne z nagłówka pliku przed analizą"
            " (tylko w pamięci — plik nie jest modyfikowany)"
        )
        anon_row = ctk.CTkFrame(inner, fg_color="transparent")
        anon_row.grid(row=_ROW_ANON, column=0, sticky="ew", pady=(0, 12))
        anon_row.columnconfigure(1, weight=1)

        ctk.CTkCheckBox(
            anon_row,
            text="",
            variable=self._anonymize_var,
            width=28,
        ).grid(row=0, column=0, sticky="nw", padx=(0, 8))

        anon_label = w.body_label(anon_row, _anon_text, wraplength=360)
        anon_label.grid(row=0, column=1, sticky="w")
        anon_label.bind(
            "<Button-1>",
            lambda _event: self._anonymize_var.set(not self._anonymize_var.get()),
        )

        self._status_label = w.body_label(
            inner,
            "",
            wraplength=t.WRAP_WIDTH,
            justify="left",
        )
        self._status_label.grid(row=_ROW_STATUS, column=0, sticky="w", pady=(0, 8))
        self._status_label.grid_remove()

        self._progress = ctk.CTkProgressBar(inner, mode="indeterminate")
        self._progress.grid(row=_ROW_PROGRESS, column=0, sticky="ew", pady=(0, 16))
        self._progress.grid_remove()
        self._progress.stop()

        self._id_frame = ctk.CTkFrame(
            inner,
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

        self._id_frame.grid(row=_ROW_ID, column=0, sticky="ew", pady=(0, 4))
        self._id_frame.grid_remove()

        w.context_panel(
            context_col,
            "Format pliku EEG",
            context_copy.CONTEXT_FILE_IMPORT,
            icon="📁",
        ).pack(fill="both", expand=True, anchor="n")

        self._app_window.set_footer(
            back_text="← Wróć",
            back_cmd=self._on_back,
            back_visible=True,
            primary_text="Analizuj",
            primary_cmd=self._on_analyze,
            primary_visible=True,
            primary_state="disabled",
        )

        self._restore_from_state()

    def restore_import_footer(self) -> None:
        self._app_window.set_footer(
            back_text="← Wróć",
            back_cmd=self._on_back,
            back_visible=True,
            primary_text="Analizuj",
            primary_cmd=self._on_analyze,
            primary_visible=True,
            primary_state="normal" if self._app_state.ready_for_analysis() else "disabled",
        )

    def restore_after_analysis_cancelled(self) -> None:
        self._status_label.grid(row=_ROW_STATUS, column=0, sticky="w", pady=(0, 8))
        self._status_label.configure(
            text="Analiza została anulowana.",
            text_color=t.COLOR_TEXT_MUTED,
        )
        self.restore_import_footer()

    def show_analysis_error(self, error: PipelineError) -> None:
        self._status_label.grid(row=_ROW_STATUS, column=0, sticky="w", pady=(0, 8))
        self._status_label.configure(
            text=f"✗ {format_pipeline_error(error)}",
            text_color=t.COLOR_ERROR,
        )
        self._set_analyze_enabled(True)
        self.restore_import_footer()

    def _restore_from_state(self) -> None:
        path = self._app_state.eeg_path
        if path is None:
            return

        self._path_label.configure(text=path.name, text_color=t.COLOR_TEXT)
        self._status_label.grid(row=_ROW_STATUS, column=0, sticky="w", pady=(0, 8))

        missing = get_missing_canonical(self._app_state.available_channels)
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

        metadata = self._app_state.metadata
        self._initials_entry.delete(0, "end")
        self._birth_year_entry.delete(0, "end")
        self._custom_label_entry.delete(0, "end")
        if metadata is not None:
            if metadata.initials:
                self._initials_entry.insert(0, metadata.initials)
            if metadata.birth_year:
                self._birth_year_entry.insert(0, metadata.birth_year)
            if metadata.custom_label:
                self._custom_label_entry.insert(0, metadata.custom_label)

        self._id_frame.grid(row=_ROW_ID, column=0, sticky="ew", pady=(0, 4))
        self._set_analyze_enabled(True)

    def _on_anonymize_change(self) -> None:
        self._app_state.anonymize_header = bool(self._anonymize_var.get())

    def _set_analyze_enabled(self, enabled: bool) -> None:
        self._app_window.set_footer_primary_state("normal" if enabled else "disabled")

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
        self._set_analyze_enabled(False)
        self._load_btn.configure(state="disabled")
        self._path_label.configure(text=path.name, text_color=t.COLOR_TEXT)
        self._status_label.configure(
            text="Wczytywanie pliku…",
            text_color=t.COLOR_TEXT_MUTED,
        )
        self._status_label.grid(row=_ROW_STATUS, column=0, sticky="w", pady=(0, 8))
        self._id_frame.grid_remove()
        self._progress.grid(row=_ROW_PROGRESS, column=0, sticky="ew", pady=(0, 16))
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
        recording_date: date | None = None
        try:
            eeg_file.validate_eeg_header(path)
            channels = get_channel_names(path)
            patient_info = read_patient_header_info(path)
            recording_date = read_recording_date(path)
        except EEGFileError as exc:
            error = exc
        self.after(
            0,
            self._on_result,
            path,
            error,
            channels,
            patient_info,
            recording_date,
        )

    def _on_result(
        self,
        path: Path,
        error: EEGFileError | None,
        channels: list[str],
        patient_info: tuple[str | None, str | None],
        recording_date: date | None,
    ) -> None:
        if not self.winfo_exists():
            return
        if path != self._selected_path:
            return
        self._validating = False
        self._load_btn.configure(state="normal")
        self._progress.stop()
        self._progress.grid_remove()
        self._status_label.grid(row=_ROW_STATUS, column=0, sticky="w", pady=(0, 8))

        if error is not None:
            self._status_label.configure(
                text=f"✗ {error}",
                text_color=t.COLOR_ERROR,
            )
            prior = self._app_state.eeg_path
            if prior is not None:
                self._path_label.configure(text=prior.name, text_color=t.COLOR_TEXT)
                self._id_frame.grid(row=_ROW_ID, column=0, sticky="ew", pady=(0, 4))
                self._set_analyze_enabled(True)
            else:
                self._id_frame.grid_remove()
                self._set_analyze_enabled(False)
            return

        self._app_state.eeg_path = path
        self._app_state.recording_date = recording_date
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
        self._set_analyze_enabled(True)

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

        self._id_frame.grid(row=_ROW_ID, column=0, sticky="ew", pady=(0, 4))

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
            from app.ui.components.channel_mapping_dialog import show_channel_mapping_dialog

            show_channel_mapping_dialog(
                self.winfo_toplevel(),
                self._app_state,
                missing,
                on_continue=self._app_window.start_analysis_overlay,
            )
            return

        self._app_window.start_analysis_overlay()

    def _on_back(self) -> None:
        from app.ui.views.metadata_form import MetadataFormView

        self._app_window.show_view(MetadataFormView)
