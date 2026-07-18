from __future__ import annotations

import customtkinter as ctk

from app.config.settings import verify_password
from app.ui import theme as ui_theme
from app.ui.components import widgets as w

_ERROR_MESSAGE = "Nieprawidłowe hasło. Spróbuj ponownie."
_ERROR_ROW_HEIGHT = 36


class SessionLockDialog(ctk.CTkToplevel):
    """Modalne odblokowanie w trakcie sesji — blokuje aplikację do czasu podania hasła."""

    def __init__(self, master: ctk.CTk) -> None:
        super().__init__(master)
        self.title("NeuroFlag — Zablokowano")
        self.resizable(False, False)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self._on_dismiss_attempt)

        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(padx=32, pady=28)

        w.section_title(container, "Aplikacja zablokowana").pack(anchor="w", pady=(0, 8))
        w.body_label(
            container,
            "Podaj hasło startowe, aby kontynuować pracę.",
            secondary=True,
        ).pack(anchor="w", pady=(0, 16))

        w.body_label(container, "Hasło").pack(anchor="w", pady=(0, 2))
        self._password_entry = ctk.CTkEntry(
            container,
            width=320,
            show="*",
            font=ui_theme.font_body(),
        )
        self._password_entry.pack(anchor="w", pady=(0, 8))

        error_row = ctk.CTkFrame(container, fg_color="transparent", height=_ERROR_ROW_HEIGHT)
        error_row.pack(anchor="w", fill="x", pady=(0, 12))
        error_row.pack_propagate(False)

        self._error_label = ctk.CTkLabel(
            error_row,
            text="",
            font=ui_theme.font_body(),
            text_color=ui_theme.COLOR_ERROR,
            anchor="nw",
            justify="left",
            wraplength=320,
        )
        self._error_label.pack(anchor="nw", fill="both", expand=True)

        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(anchor="e")
        w.primary_button(btn_row, text="Odblokuj", command=self._on_unlock, width=130).pack(
            side="right"
        )

        self.bind("<Return>", lambda _event: self._on_unlock())
        self.bind("<Escape>", lambda _event: self._on_dismiss_attempt())

        self.update_idletasks()
        width = 400
        height = 280
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w - width) // 2
        y = (screen_h - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        self.grab_set()
        self._password_entry.focus_set()
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))

    def _on_dismiss_attempt(self) -> None:
        self.focus_set()
        self.lift()

    def _on_unlock(self) -> None:
        if verify_password(self._password_entry.get()):
            self.grab_release()
            self.destroy()
            return
        self._error_label.configure(text=_ERROR_MESSAGE)
        self._password_entry.delete(0, "end")
        self._password_entry.focus_set()


def prompt_session_unlock(master: ctk.CTk) -> None:
    """Blokuje aplikację do czasu podania poprawnego hasła startowego."""
    dialog = SessionLockDialog(master)
    master.wait_window(dialog)
