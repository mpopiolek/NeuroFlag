from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import customtkinter as ctk

from app.domain.errors import PipelineError
from app.domain.types import AnalysisDiagnostics, AnalysisResult, NormsConfig, PatientMetadata
from app.storage.history import HistoryStore, resolve_history_db_path
from app.config.settings import is_password_enabled
from app.ui import theme as ui_theme
from app.ui.components import widgets as w
from app.ui.components.stepper import WorkflowStepper


@dataclass
class AppState:
    norms_config: NormsConfig
    metadata: PatientMetadata | None = None
    eeg_path: Path | None = None
    recording_date: date | None = None
    analysis_result: AnalysisResult | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    analysis_in_progress: bool = False
    channel_overrides: dict[str, str] = field(default_factory=dict)
    available_channels: list[str] = field(default_factory=list)
    analysis_step_delay_s: float = 0.0
    anonymize_header: bool = True
    history_store: HistoryStore | None = None
    last_analysis_diagnostics: AnalysisDiagnostics | None = None
    last_exception_type_name: str | None = None
    last_pipeline_error: PipelineError | None = None

    def ready_for_analysis(self) -> bool:
        return self.metadata is not None and self.eeg_path is not None


class AppWindow(ctk.CTk):
    def __init__(
        self,
        norms_config: NormsConfig,
        *,
        analysis_step_delay_s: float = 0.0,
        debug_crash_gui: bool = False,
    ) -> None:
        ui_theme.apply_app_theme()
        super().__init__()
        self._debug_crash_gui = debug_crash_gui
        self.title("NeuroFlag — Badanie przesiewowe EEG")
        self.geometry("1000x720")
        self.minsize(900, 640)
        self.configure(fg_color=ui_theme.COLOR_ROW_BG)
        self._state = AppState(
            norms_config=norms_config,
            analysis_step_delay_s=analysis_step_delay_s,
        )
        self._state.history_store = HistoryStore(resolve_history_db_path())
        self._current_view: ctk.CTkFrame | None = None
        self._analysis_overlay: ctk.CTkFrame | None = None

        self._shell = ctk.CTkFrame(self, fg_color="transparent")
        self._shell.pack(fill="both", expand=True)

        self._header = ctk.CTkFrame(
            self._shell,
            fg_color=ui_theme.COLOR_HEADER_BG,
            corner_radius=0,
        )
        self._header.pack(fill="x")

        header_inner = ctk.CTkFrame(self._header, fg_color="transparent")
        header_inner.pack(fill="x", padx=ui_theme.PAGE_PAD_X, pady=(14, 12))

        ctk.CTkLabel(
            header_inner,
            text="NeuroFlag",
            font=ui_theme.font_heading(),
            text_color=ui_theme.COLOR_NAVY,
            anchor="w",
        ).pack(side="left")

        stepper_host = ctk.CTkFrame(header_inner, fg_color="transparent")
        stepper_host.pack(side="left", expand=True, fill="x", padx=(24, 24))
        self._stepper = WorkflowStepper(stepper_host)
        self._stepper.pack(anchor="center")

        header_actions = ctk.CTkFrame(header_inner, fg_color="transparent")
        header_actions.pack(side="right")

        self._history_btn = w.secondary_button(
            header_actions,
            text="Historia",
            command=self._on_history,
            width=110,
        )
        self._history_btn.pack(side="right", padx=(8, 0))

        self._lock_btn = w.secondary_button(
            header_actions,
            text="Zablokuj",
            command=self._on_lock,
            width=110,
        )
        self._lock_btn.pack(side="right", padx=(8, 0))

        w.secondary_button(
            header_actions,
            text="Informacje",
            command=self._show_info,
            width=110,
        ).pack(side="right")

        self._mint_stripe = ctk.CTkFrame(
            self._shell,
            fg_color=ui_theme.COLOR_MINT_STRIPE,
            height=4,
            corner_radius=0,
        )
        self._mint_stripe.pack(fill="x")
        self._mint_stripe.pack_propagate(False)

        self._view_host = ctk.CTkFrame(self._shell, fg_color=ui_theme.COLOR_ROW_BG)
        self._view_host.pack(fill="both", expand=True)

        self._footer = ctk.CTkFrame(
            self._shell,
            fg_color=ui_theme.COLOR_HEADER_BG,
            corner_radius=0,
        )
        self._footer.pack(fill="x")

        footer_inner = ctk.CTkFrame(self._footer, fg_color="transparent")
        footer_inner.pack(fill="x", padx=ui_theme.PAGE_PAD_X, pady=12)

        self._back_btn = w.secondary_button(
            footer_inner,
            text="← Wstecz",
            width=140,
        )
        self._primary_btn = w.primary_button(
            footer_inner,
            text="Dalej →",
            width=160,
        )
        self._clear_footer()
        self.refresh_lock_button()

    def refresh_lock_button(self) -> None:
        if is_password_enabled():
            self._lock_btn.pack(side="right", padx=(8, 0), before=self._history_btn)
            self._lock_btn.configure(state="normal")
        else:
            self._lock_btn.pack_forget()

    def _on_lock(self) -> None:
        if not is_password_enabled():
            return
        from app.ui.session_lock_dialog import prompt_session_unlock

        prompt_session_unlock(self)

    def _show_info(self) -> None:
        if self._debug_crash_gui:
            raise RuntimeError("DEV: test nieobsłużonego błędu GUI (--debug-crash-gui)")
        self.open_info()

    def open_info(self) -> None:
        """Otwiera Informacje jako widok główny; powrót wraca na poprzedni ekran."""
        from app.ui.views.info_view import InfoView
        from app.ui.views.metadata_form import MetadataFormView

        if isinstance(self._current_view, InfoView):
            return
        return_view: type[ctk.CTkFrame] = (
            type(self._current_view) if self._current_view is not None else MetadataFormView
        )
        self.show_view(InfoView, return_view=return_view, preserve_stepper=True)

    def open_history(self) -> None:
        """Otwiera historię; powrót wraca na widok aktywny w momencie kliknięcia."""
        from app.ui.views.history import HistoryView
        from app.ui.views.metadata_form import MetadataFormView

        if isinstance(self._current_view, HistoryView):
            return
        return_view: type[ctk.CTkFrame] = (
            type(self._current_view) if self._current_view is not None else MetadataFormView
        )
        self.show_view(HistoryView, return_view=return_view, preserve_stepper=True)

    def _on_history(self) -> None:
        self.open_history()

    def _update_history_button_state(self) -> None:
        """Historia zawsze dostępna — pusty stan obsługuje HistoryView."""
        self._history_btn.configure(state="normal")

    def set_footer(
        self,
        *,
        back_text: str = "← Wstecz",
        back_cmd: Callable[[], None] | None = None,
        back_visible: bool = False,
        primary_text: str = "Dalej →",
        primary_cmd: Callable[[], None] | None = None,
        primary_visible: bool = False,
        primary_state: w.ButtonState = "normal",
    ) -> None:
        if back_visible:
            self._back_btn.configure(text=back_text, command=back_cmd, state="normal")
            self._back_btn.pack(side="left")
        else:
            self._back_btn.pack_forget()

        if primary_visible:
            self._primary_btn.configure(
                text=primary_text,
                command=primary_cmd,
                state=primary_state,
            )
            self._primary_btn.pack(side="right")
        else:
            self._primary_btn.pack_forget()

    def set_footer_primary_state(self, state: w.ButtonState) -> None:
        self._primary_btn.configure(state=state)

    def _clear_footer(self) -> None:
        self._back_btn.configure(command=None, state="disabled")
        self._primary_btn.configure(command=None, state="disabled")
        self._back_btn.pack_forget()
        self._primary_btn.pack_forget()

    def _update_stepper_for_view(self, view_class: type[ctk.CTkFrame]) -> None:
        from app.ui.navigation import VIEW_STEP

        step = VIEW_STEP.get(view_class, 1)
        self._stepper.set_active_step(step)
        self._stepper.set_completed_through(max(0, step - 1))

    @property
    def app_state(self) -> AppState:
        return self._state

    @property
    def current_view(self) -> ctk.CTkFrame | None:
        return self._current_view

    def show_view(
        self,
        view_class: type[ctk.CTkFrame],
        *,
        preserve_stepper: bool = False,
        **kwargs: object,
    ) -> None:
        self._dismiss_analysis_overlay()
        self._clear_footer()
        if self._current_view is not None:
            self._current_view.destroy()
            self._current_view = None
        self._current_view = view_class(
            master=self._view_host,
            app_window=self,
            app_state=self._state,
            **kwargs,
        )
        self._current_view.pack(fill="both", expand=True)
        if not preserve_stepper:
            self._update_stepper_for_view(view_class)
        self._update_history_button_state()
        self.refresh_lock_button()

    def start_analysis_overlay(self) -> None:
        """Uruchamia nakładkę analizy nad aktywnym widokiem (bez zmiany widoku)."""
        if self._analysis_overlay is not None or self._state.analysis_in_progress:
            return
        self._state.cancel_event.clear()
        self._state.analysis_result = None
        self._state.last_pipeline_error = None
        self._clear_footer()
        self._stepper.set_active_step(3)
        self._stepper.set_completed_through(2)

        from app.ui.components.analysis_overlay import AnalysisOverlay

        self._analysis_overlay = AnalysisOverlay(
            master=self._view_host,
            app_window=self,
            app_state=self._state,
        )
        self._analysis_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._analysis_overlay.lift()

    def _dismiss_analysis_overlay(self) -> None:
        if self._analysis_overlay is not None:
            self._state.cancel_event.set()
            self._analysis_overlay.destroy()
            self._analysis_overlay = None

    def finish_analysis_overlay(
        self,
        *,
        result: AnalysisResult | None = None,
        error: PipelineError | None = None,
        cancelled: bool = False,
    ) -> None:
        """Kończy overlay: sukces → wyniki; błąd/anulowanie → powrót do importu."""
        self._dismiss_analysis_overlay()

        if result is not None:
            self._state.analysis_result = result
            self._state.last_pipeline_error = None
            self._stepper.set_active_step(4)
            self._stepper.set_completed_through(3)
            from app.ui.views.results_grid import ResultsGridView

            self.show_view(ResultsGridView)
            return

        from app.ui.views.file_import import FileImportView

        self._stepper.set_active_step(2)
        self._stepper.set_completed_through(1)
        if isinstance(self._current_view, FileImportView):
            if error is not None:
                self._state.last_pipeline_error = error
                self._current_view.show_analysis_error(error)
            elif cancelled:
                self._state.last_pipeline_error = None
                self._current_view.restore_after_analysis_cancelled()
            else:
                self._state.last_pipeline_error = None
                self._current_view.restore_import_footer()
