from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.errors import AnalysisCancelledError, PipelineError

if TYPE_CHECKING:
    from app.ui.app_window import AppState, AppWindow


def format_pipeline_error(exc: PipelineError) -> str:
    """Zwraca jednolinijkowy komunikat błędu pipeline po polsku dla pedagoga."""
    return exc.user_message_pl


class AnalysisView(ctk.CTkFrame):
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
        self._app_state.cancel_requested = False
        self._app_state.analysis_result = None

        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True, padx=40, pady=40)

        ctk.CTkLabel(
            self._container,
            text="Trwa analiza EEG\u2026",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", pady=(0, 20))

        self._status_label = ctk.CTkLabel(
            self._container,
            text="Przetwarzanie sygna\u0142u\u2026",
            wraplength=700,
            justify="left",
        )
        self._status_label.pack(anchor="w", pady=(0, 12))

        self._progress = ctk.CTkProgressBar(
            self._container, mode="indeterminate", width=500
        )
        self._progress.pack(anchor="w", pady=(0, 20))
        self._progress.start()

        self._cancel_button = ctk.CTkButton(
            self._container,
            text="Anuluj",
            command=self._on_cancel,
            width=120,
        )
        self._cancel_button.pack(anchor="w")

        threading.Thread(target=self._analysis_worker, daemon=True).start()

    def _on_cancel(self) -> None:
        self._app_state.cancel_requested = True
        self._cancel_button.configure(state="disabled", text="Anulowanie\u2026")

    def _analysis_worker(self) -> None:
        from app.domain import algorithm, pipeline

        assert self._app_state.eeg_path is not None
        path = self._app_state.eeg_path
        config = self._app_state.norms_config

        error: PipelineError | None = None
        try:
            amplitudes = pipeline.run(
                path,
                config,
                cancel_check=lambda: self._app_state.cancel_requested,
            )
            result = algorithm.classify(amplitudes, config)
            self._app_state.analysis_result = result
        except AnalysisCancelledError:
            self.after(0, self._on_cancelled)
            return
        except PipelineError as exc:
            error = exc
        except Exception as exc:  # noqa: BLE001
            error = PipelineError(
                "unexpected_error",
                f"Nieoczekiwany b\u0142\u0105d analizy: {type(exc).__name__}",
            )

        self.after(0, self._on_done, error)

    def _on_cancelled(self) -> None:
        self._progress.stop()
        self._status_label.configure(
            text="Analiza zosta\u0142a anulowana.",
            text_color="#888888",
        )
        self._cancel_button.pack_forget()
        self._show_back_button()

    def _on_done(self, error: PipelineError | None) -> None:
        self._progress.stop()
        self._cancel_button.pack_forget()

        if error is not None:
            self._status_label.configure(
                text=f"\u2717 {format_pipeline_error(error)}",
                text_color="#CC0000",
            )
            self._show_error_details(error)
            self._show_back_button()
            return

        from app.ui.views.results_grid import ResultsGridView

        self._app_window.show_view(ResultsGridView)

    def _show_error_details(self, error: PipelineError) -> None:
        details_frame = ctk.CTkFrame(
            self._container,
            fg_color="#F0F0F0",
            corner_radius=6,
        )
        details_frame.pack(anchor="w", pady=(8, 0), fill="x")
        ctk.CTkLabel(
            details_frame,
            text="Szczeg\u00f3\u0142y",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=8, pady=(6, 2))
        ctk.CTkLabel(
            details_frame,
            text=f"Kod b\u0142\u0119du: {error.code}",
            font=ctk.CTkFont(size=11),
            text_color="#555555",
        ).pack(anchor="w", padx=16, pady=(0, 6))

    def _show_back_button(self) -> None:
        ctk.CTkButton(
            self._container,
            text="\u2190 Wr\u00f3\u0107 do importu",
            command=self._on_back,
            width=160,
        ).pack(anchor="w", pady=(16, 0))

    def _on_back(self) -> None:
        from app.ui.views.file_import import FileImportView

        self._app_window.show_view(FileImportView)
