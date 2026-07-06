from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path

import customtkinter as ctk

from app.domain.types import AnalysisResult, NormsConfig, PatientMetadata
from app.storage.history import HistoryStore, resolve_history_db_path
from app.ui import theme as ui_theme


@dataclass
class AppState:
    norms_config: NormsConfig
    metadata: PatientMetadata | None = None
    eeg_path: Path | None = None
    analysis_result: AnalysisResult | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    channel_overrides: dict[str, str] = field(default_factory=dict)
    available_channels: list[str] = field(default_factory=list)
    analysis_step_delay_s: float = 0.0
    anonymize_header: bool = False
    history_store: HistoryStore | None = None

    def ready_for_analysis(self) -> bool:
        return self.metadata is not None and self.eeg_path is not None


class AppWindow(ctk.CTk):
    def __init__(
        self,
        norms_config: NormsConfig,
        *,
        analysis_step_delay_s: float = 0.0,
    ) -> None:
        ui_theme.apply_app_theme()
        super().__init__()
        self.title("NeuroFlag — Badanie przesiewowe EEG")
        self.geometry("920x680")
        self.minsize(820, 600)
        self.configure(fg_color=ui_theme.COLOR_SURFACE_ELEVATED)
        self._state = AppState(
            norms_config=norms_config,
            analysis_step_delay_s=analysis_step_delay_s,
        )
        self._state.history_store = HistoryStore(resolve_history_db_path())
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
