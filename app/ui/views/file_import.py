from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.channels import get_missing_canonical
from app.domain.eeg_file import EEGFileError, get_channel_names
from app.ui.app_window import AppState

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

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=40, pady=40)

        ctk.CTkLabel(
            container,
            text="Wczytaj plik EEG",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", pady=(0, 20))

        ctk.CTkButton(
            container,
            text="Wczytaj plik",
            command=self._on_load_file,
            width=160,
        ).pack(anchor="w", pady=(0, 12))

        self._path_label = ctk.CTkLabel(
            container,
            text="Nie wybrano pliku",
            wraplength=700,
            justify="left",
        )
        self._path_label.pack(anchor="w", pady=(0, 8))

        self._status_label = ctk.CTkLabel(container, text="", wraplength=700, justify="left")
        self._status_label.pack(anchor="w", pady=(0, 8))
        self._status_label.pack_forget()

        self._progress = ctk.CTkProgressBar(container, mode="indeterminate", width=400)
        self._progress.pack(anchor="w", pady=(0, 16))
        self._progress.pack_forget()
        self._progress.stop()

        button_row = ctk.CTkFrame(container, fg_color="transparent")
        button_row.pack(anchor="w", pady=(8, 0))

        self._analyze_button = ctk.CTkButton(
            button_row,
            text="Analizuj",
            command=self._on_analyze,
            state="disabled",
            width=140,
        )
        self._analyze_button.pack(side="left", padx=(0, 12))

        ctk.CTkButton(
            button_row,
            text="← Wróć",
            command=self._on_back,
            width=120,
        ).pack(side="left")

    def _on_load_file(self) -> None:
        if self._validating:
            return
        chosen = filedialog.askopenfilename(
            parent=self.winfo_toplevel(),
            title="Wybierz plik EEG",
            filetypes=[
                ("Pliki EEG", "*.edf *.vhdr"),
                ("Wszystkie pliki", "*.*"),
            ],
        )
        if not chosen:
            return

        path = Path(chosen)
        self._selected_path = path
        self._app_state.eeg_path = None
        self._analyze_button.configure(state="disabled")
        self._path_label.configure(text=str(path))
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
        try:
            eeg_file.validate_eeg_header(path)
            channels = get_channel_names(path)
        except EEGFileError as exc:
            error = exc
        self.after(0, self._on_result, path, error, channels)

    def _on_result(
        self, path: Path, error: EEGFileError | None, channels: list[str]
    ) -> None:
        self._validating = False
        self._progress.stop()
        self._progress.pack_forget()
        self._status_label.pack(anchor="w", pady=(0, 8))

        if error is not None:
            self._app_state.eeg_path = None
            self._status_label.configure(
                text=f"✗ {error}",
                text_color="#CC0000",
            )
            self._analyze_button.configure(state="disabled")
            return

        self._app_state.eeg_path = path
        self._app_state.available_channels = channels
        self._app_state.channel_overrides = {}

        missing = get_missing_canonical(channels)
        if missing:
            self._status_label.configure(
                text="⚠ Brak C3/O1 — wybór kanału wymagany przed analizą",
                text_color="#A07000",
            )
        else:
            self._status_label.configure(
                text="✓ Plik wczytany poprawnie",
                text_color="#008800",
            )
        self._analyze_button.configure(state="normal")

    def _on_analyze(self) -> None:
        if not self._app_state.ready_for_analysis():
            return

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
