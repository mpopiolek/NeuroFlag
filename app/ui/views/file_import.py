from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.ui.app_window import AppState

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow


class FileImportView(ctk.CTkFrame):
    """Import pliku EEG — pełna implementacja w Phase 3."""

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

        ctk.CTkLabel(
            self,
            text="Wczytaj plik EEG",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", padx=40, pady=40)

        ctk.CTkButton(
            self,
            text="← Wróć",
            command=self._on_back,
            width=120,
        ).pack(anchor="w", padx=40)

    def _on_back(self) -> None:
        from app.ui.views.metadata_form import MetadataFormView

        self._app_window.show_view(MetadataFormView)
