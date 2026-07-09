from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.domain.errors import PipelineError
from app.ui.bug_report import collect_bug_report_context, open_bug_report
from app.ui.components import widgets as w

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow


class UncaughtErrorDialog(ctk.CTkToplevel):
    """Modal dla nieobsłużonego wyjątku w wątku GUI (bez tracebacku)."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        app_window: AppWindow,
        exc_type_name: str,
    ) -> None:
        super().__init__(parent)
        self._app_window = app_window
        self._exc_type_name = exc_type_name

        self.title("NeuroFlag — Błąd aplikacji")
        self.geometry("480x260")
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        panel = w.surface_card(self)
        panel.pack(fill="both", expand=True, padx=20, pady=20)

        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=20, pady=16)

        w.section_title(inner, "Wystąpił nieoczekiwany błąd").pack(
            anchor="w", pady=(0, 12)
        )

        w.body_label(
            inner,
            (
                "Aplikacja napotkała problem, którego nie udało się obsłużyć.\n"
                f"Typ błędu: {exc_type_name}\n\n"
                "Możesz zgłosić problem deweloperowi — otworzy się strona GitHub "
                "z wstępnie wypełnioną diagnostyką sesji."
            ),
            wraplength=420,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))

        buttons = ctk.CTkFrame(inner, fg_color="transparent")
        buttons.pack(anchor="w")

        w.primary_button(
            buttons,
            text="Zgłoś błąd na GitHubie",
            command=self._on_report,
            width=220,
        ).pack(side="left", padx=(0, 8))

        w.secondary_button(
            buttons,
            text="Zamknij",
            command=self.destroy,
            width=120,
        ).pack(side="left")

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _on_report(self) -> None:
        synthetic_error = PipelineError(
            "unexpected_error",
            "Nieobsłużony błąd aplikacji.",
        )
        ctx = collect_bug_report_context(
            self._app_window,
            error=synthetic_error,
            exception_type_name=self._exc_type_name,
        )
        open_bug_report(ctx)
