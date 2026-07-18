from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from app.config.settings import clear_password, is_password_enabled, set_password, verify_password
from app.ui import theme as t
from app.ui.components import widgets as w


class PasswordSettingsDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        *,
        on_password_changed: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._on_password_changed = on_password_changed
        self._enabled = is_password_enabled()

        self.title("Hasło startowe")
        self.resizable(False, False)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.grid_columnconfigure(0, weight=1)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew", padx=24, pady=(20, 8))
        body.grid_columnconfigure(0, weight=1)

        w.section_title(body, "Hasło startowe").grid(row=0, column=0, sticky="w", pady=(0, 8))

        intro = (
            "Przy następnym uruchomieniu aplikacja poprosi o hasło przed rozpoczęciem pracy."
            if not self._enabled
            else "Aby zmienić lub wyłączyć hasło, podaj obecne hasło startowe."
        )
        w.body_label(body, intro, secondary=True, wraplength=360).grid(
            row=1, column=0, sticky="w", pady=(0, 12)
        )

        row = 2
        self._current_entry: ctk.CTkEntry | None = None
        if self._enabled:
            w.body_label(body, "Obecne hasło").grid(row=row, column=0, sticky="w", pady=(0, 2))
            self._current_entry = self._password_entry(body, row + 1)
            row += 2

        new_label = "Nowe hasło" if self._enabled else "Hasło"
        w.body_label(body, new_label).grid(row=row, column=0, sticky="w", pady=(0, 2))
        self._new_entry = self._password_entry(body, row + 1)
        row += 2

        w.body_label(body, "Powtórz hasło").grid(row=row, column=0, sticky="w", pady=(0, 2))
        self._confirm_entry = self._password_entry(body, row + 1)
        row += 2

        self._error_label = ctk.CTkLabel(
            body,
            text="",
            font=t.font_body(),
            text_color=t.COLOR_ERROR,
            anchor="nw",
            justify="left",
            wraplength=360,
        )
        self._error_label.grid(row=row, column=0, sticky="w", pady=(4, 8))
        row += 1

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 20))

        if self._enabled:
            w.danger_button(
                footer,
                text="Wyłącz hasło",
                command=self._disable_password,
                width=130,
            ).pack(side="left")

        w.primary_button(
            footer,
            text="Zapisz" if self._enabled else "Ustaw hasło",
            command=self._save_password,
            width=130,
        ).pack(side="right")
        w.secondary_button(
            footer,
            text="Anuluj",
            command=self.destroy,
            width=110,
        ).pack(side="right", padx=(0, 8))

        self.bind("<Return>", lambda _event: self._save_password())
        self.bind("<Escape>", lambda _event: self.destroy())

        self.update_idletasks()
        self.grab_set()
        focus_entry = self._new_entry if not self._enabled else self._current_entry
        if focus_entry is not None:
            focus_entry.focus_set()
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))

    def _password_entry(self, parent: ctk.CTkFrame, row: int) -> ctk.CTkEntry:
        entry = ctk.CTkEntry(parent, width=360, show="*", font=t.font_body())
        entry.grid(row=row, column=0, sticky="w", pady=(0, 8))
        return entry

    def _show_error(self, message: str) -> None:
        self._error_label.configure(text=message)

    def _clear_error(self) -> None:
        self._error_label.configure(text="")

    def _validate_new_password(self) -> str | None:
        new_password = str(self._new_entry.get())
        confirm_password = str(self._confirm_entry.get())
        if not new_password.strip():
            self._show_error("Hasło nie może być puste.")
            return None
        if new_password != confirm_password:
            self._show_error("Hasła nie są identyczne.")
            return None
        self._clear_error()
        return new_password

    def _verify_current(self) -> bool:
        if self._current_entry is None:
            return True
        current = self._current_entry.get()
        if not verify_password(current):
            self._show_error("Nieprawidłowe obecne hasło.")
            return False
        self._clear_error()
        return True

    def _save_password(self) -> None:
        if self._enabled and not self._verify_current():
            return
        new_password = self._validate_new_password()
        if new_password is None:
            return
        set_password(new_password)
        self._on_password_changed()
        self.destroy()

    def _disable_password(self) -> None:
        if not self._verify_current():
            return
        clear_password()
        self._on_password_changed()
        self.destroy()
