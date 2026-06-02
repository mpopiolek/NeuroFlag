from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.ui.app_window import AppState

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow


class MetadataFormView(ctk.CTkFrame):
    """Formularz metryki dziecka — pełna implementacja w Phase 2."""

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
