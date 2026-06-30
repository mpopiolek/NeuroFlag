from __future__ import annotations

import sys
import threading
import tkinter.messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.errors import AnalysisCancelledError, PipelineError
from app.domain.types import AnalysisResult
from app.ui.app_window import AppState

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow

_RODO_NOTICE = (
    "Badanie zostało zapisane w lokalnej historii na tym urządzeniu.\n\n"
    "Historia zawiera inicjały i rok urodzenia dziecka.\n"
    "Dane nie opuszczają urządzenia."
)

_ERROR_CODE_PL: dict[str, str] = {
    "missing_channels": "Brak wymaganych kana\u0142\u00f3w (C3/O1)",
    "unsupported_format": "Nieobs\u0142ugiwany format pliku",
    "file_unreadable": "Nie mo\u017cna odczyta\u0107 pliku",
    "insufficient_duration": "Nagranie za kr\u00f3tkie",
    "missing_task_segments": "Brak segment\u00f3w zada\u0144",
    "artifact_rejection": "Odrzucenie artefakt\u00f3w",
    "invalid_segment": "Nieprawid\u0142owy segment",
    "empty_segment": "Pusty segment",
    "invalid_amplitude": "B\u0142\u0105d amplitudy",
    "amplitude_count": "Niezgodna liczba amplitud",
    "anonymize_failed": "Błąd czyszczenia nagłówka pliku EEG",
    "mne_missing": "Brak biblioteki MNE",
    "no_file": "Brak pliku EEG",
    "unexpected_error": "Nieoczekiwany b\u0142\u0105d",
    "analysis_cancelled": "Anulowano",
}


def _error_code_pl(code: str) -> str:
    return _ERROR_CODE_PL.get(code, code)


def format_pipeline_error(exc: PipelineError) -> str:
    """Zwraca jednolinijkowy komunikat b\u0142\u0119du pipeline po polsku dla pedagoga."""
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
        self._app_state.cancel_event.clear()
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
        self._app_state.cancel_event.set()
        self._cancel_button.configure(state="disabled", text="Anulowanie\u2026")

    def _analysis_worker(self) -> None:
        from app.domain import algorithm, pipeline

        if self._app_state.eeg_path is None:
            self.after(
                0,
                self._on_done,
                PipelineError("no_file", "Brak wybranego pliku EEG."),
                None,
            )
            return
        path = self._app_state.eeg_path
        config = self._app_state.norms_config

        overrides = self._app_state.channel_overrides or None
        error: PipelineError | None = None
        result: AnalysisResult | None = None
        try:
            amplitudes = pipeline.run(
                path,
                config,
                cancel_check=self._app_state.cancel_event.is_set,
                channel_overrides=overrides,
                step_delay_s=self._app_state.analysis_step_delay_s,
                anonymize_header=self._app_state.anonymize_header,
            )
            result = algorithm.classify(amplitudes, config)
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

        self.after(0, self._on_done, error, result)

    def _on_cancelled(self) -> None:
        self._progress.stop()
        self._status_label.configure(
            text="Analiza zosta\u0142a anulowana.",
            text_color="#888888",
        )
        self._cancel_button.pack_forget()
        self._show_back_button()

    def _on_done(
        self, error: PipelineError | None, result: AnalysisResult | None = None
    ) -> None:
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

        if result is not None:
            store = self._app_state.history_store
            assert store is not None
            try:
                if not store.is_notice_shown():
                    tkinter.messagebox.showinfo("Historia badań", _RODO_NOTICE)
                    store.mark_notice_shown()
                assert self._app_state.metadata is not None
                store.add(
                    self._app_state.metadata,
                    result,
                    eeg_path=self._app_state.eeg_path,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"[historia] Błąd zapisu: {exc}", file=sys.stderr)

        self._app_state.analysis_result = result

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
            text=f"Typ b\u0142\u0119du: {_error_code_pl(error.code)}",
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
