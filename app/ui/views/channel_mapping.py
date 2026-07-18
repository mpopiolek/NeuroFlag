from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.ui.app_window import AppState

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow


class ChannelMappingView(ctk.CTkFrame):
    """Kompatybilność wsteczna — przekierowuje do modala mapowania kanałów."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        app_window: AppWindow,
        app_state: AppState,
        missing_channels: list[str],
        **kwargs: object,
    ) -> None:
        super().__init__(master, **kwargs)
        self._app_window = app_window
        self._app_state = app_state
        self._missing_channels = missing_channels
        self.after_idle(self._open_dialog)

    def _open_dialog(self) -> None:
        from app.ui.components.channel_mapping_dialog import show_channel_mapping_dialog
        from app.ui.views.file_import import FileImportView

        self._app_window.show_view(FileImportView)
        show_channel_mapping_dialog(
            self._app_window,
            self._app_state,
            self._missing_channels,
            on_continue=self._app_window.start_analysis_overlay,
        )
