from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.errors import PipelineError
from app.domain.types import AnalysisResult
from app.ui import theme as t
from app.ui.app_window import AppState
from app.ui.components import widgets as w
from app.ui.views.analysis import AnalysisCallbacks, AnalysisRunner, persist_analysis_result

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow

_OVERLAY_SCRIM = "#D8E2EC"


class AnalysisOverlay(ctk.CTkFrame):
    """Półprzezroczysta nakładka analizy na aktywnym widoku importu."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        app_window: AppWindow,
        app_state: AppState,
    ) -> None:
        super().__init__(master, fg_color=_OVERLAY_SCRIM, corner_radius=0)
        self._app_window = app_window
        self._app_state = app_state

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        panel = w.surface_card(self)
        panel.grid(row=0, column=0, padx=48, pady=48)

        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(padx=32, pady=28)

        w.section_title(inner, "Trwa analiza EEG…").pack(anchor="w", pady=(0, 12))

        self._status_label = w.body_label(
            inner,
            "Przetwarzanie sygna\u0142u\u2026",
            wraplength=420,
            justify="left",
        )
        self._status_label.pack(anchor="w", pady=(0, 12))

        self._progress = ctk.CTkProgressBar(inner, mode="indeterminate", width=420)
        self._progress.pack(anchor="w", pady=(0, 16))
        self._progress.start()

        self._cancel_button = w.secondary_button(
            inner,
            text="Anuluj",
            command=self._on_cancel,
            width=120,
        )
        self._cancel_button.pack(anchor="w")

        self._runner = AnalysisRunner(
            app_state,
            self,
            AnalysisCallbacks(
                on_success=self._on_success,
                on_error=self._on_error,
                on_cancelled=self._on_cancelled,
            ),
        )
        self._runner.start()

    def _on_cancel(self) -> None:
        self._runner.request_cancel()
        self._cancel_button.configure(state="disabled", text="Anulowanie\u2026")

    def _on_cancelled(self) -> None:
        if not self.winfo_exists():
            return
        self._progress.stop()
        self._app_window.finish_analysis_overlay(cancelled=True)

    def _on_error(self, error: PipelineError) -> None:
        if not self.winfo_exists():
            return
        self._progress.stop()
        self._app_window.finish_analysis_overlay(error=error)

    def _on_success(self, result: AnalysisResult) -> None:
        if not self.winfo_exists():
            return
        self._progress.stop()
        persist_analysis_result(self._app_state, result)
        self._app_window.finish_analysis_overlay(result=result)
