from __future__ import annotations

import sys
import threading
import tkinter.messagebox
from collections.abc import Callable
from dataclasses import dataclass

import customtkinter as ctk

from app.domain.errors import AnalysisCancelledError, PipelineError
from app.domain.types import AnalysisResult
from app.ui.app_window import AppState

_RODO_NOTICE = (
    "Badanie zostało zapisane w lokalnej historii na tym urządzeniu.\n\n"
    "Historia zawiera inicjały, rok urodzenia oraz — jeśli podane — wcześniejsze "
    "diagnozy dziecka.\n"
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


def persist_analysis_result(app_state: AppState, result: AnalysisResult) -> None:
    """Zapisuje wynik w historii lokalnej (z jednorazowym komunikatem RODO)."""
    store = app_state.history_store
    assert store is not None
    try:
        if not store.is_notice_shown():
            tkinter.messagebox.showinfo("Historia badań", _RODO_NOTICE)
            store.mark_notice_shown()
        assert app_state.metadata is not None
        store.add(
            app_state.metadata,
            result,
            eeg_path=app_state.eeg_path,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[historia] Błąd zapisu: {exc}", file=sys.stderr)
        tkinter.messagebox.showwarning(
            "Historia badań",
            "Nie udało się zapisać badania w lokalnej historii.\n"
            "Wynik analizy jest dostępny, ale wpis nie trafił do bazy.",
        )


@dataclass
class AnalysisCallbacks:
    on_success: Callable[[AnalysisResult], None]
    on_error: Callable[[PipelineError], None]
    on_cancelled: Callable[[], None]


class AnalysisRunner:
    """Wątek analizy EEG — współdzielony przez overlay i legacy AnalysisView."""

    def __init__(
        self,
        app_state: AppState,
        root: ctk.CTkBaseClass,
        callbacks: AnalysisCallbacks,
    ) -> None:
        self._app_state = app_state
        self._root = root
        self._callbacks = callbacks

    def start(self) -> None:
        self._app_state.cancel_event.clear()
        self._app_state.analysis_result = None
        self._app_state.analysis_in_progress = True
        threading.Thread(target=self._worker, daemon=True).start()

    def request_cancel(self) -> None:
        self._app_state.cancel_event.set()

    def _worker(self) -> None:
        from app.domain import algorithm, pipeline

        try:
            if self._app_state.eeg_path is None:
                self._root.after(
                    0,
                    self._callbacks.on_error,
                    PipelineError("no_file", "Brak wybranego pliku EEG."),
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
                self._root.after(0, self._callbacks.on_cancelled)
                return
            except PipelineError as exc:
                error = exc
            except Exception as exc:  # noqa: BLE001
                error = PipelineError(
                    "unexpected_error",
                    f"Nieoczekiwany b\u0142\u0105d analizy: {type(exc).__name__}",
                )

            if error is not None:
                self._root.after(0, self._callbacks.on_error, error)
                return
            if result is not None:
                self._root.after(0, self._callbacks.on_success, result)
        finally:
            self._app_state.analysis_in_progress = False


class AnalysisView(ctk.CTkFrame):
    """Legacy — nawigacja zastąpiona przez AnalysisOverlay (Phase 5)."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        app_window: object,
        app_state: AppState,
        **kwargs: object,
    ) -> None:
        super().__init__(master, **kwargs)
        del app_window, app_state, kwargs
