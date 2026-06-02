from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import customtkinter as ctk

from app.domain.types import PatientMetadata


@dataclass
class AppState:
    metadata: PatientMetadata | None = None
    eeg_path: Path | None = None

    def ready_for_analysis(self) -> bool:
        return self.metadata is not None and self.eeg_path is not None


class AppWindow(ctk.CTk):
    def __init__(self) -> None:
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        super().__init__()
        self.title("NeuroFlag — Badanie przesiewowe EEG")
        self.geometry("900x650")
        self._state = AppState()
        self._current_view: ctk.CTkFrame | None = None

    @property
    def app_state(self) -> AppState:
        return self._state

    def show_view(self, view_class: type[ctk.CTkFrame], **kwargs: object) -> None:
        if self._current_view is not None:
            self._current_view.destroy()
            self._current_view = None
        self._current_view = view_class(
            master=self,
            app_window=self,
            app_state=self._state,
            **kwargs,
        )
        self._current_view.pack(fill="both", expand=True)
