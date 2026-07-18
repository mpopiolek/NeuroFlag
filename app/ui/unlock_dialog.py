from __future__ import annotations

import tkinter
from dataclasses import dataclass

import customtkinter as ctk

from app.config.settings import verify_password
from app.ui import theme as ui_theme
from app.ui.components import widgets as w

_ERROR_MESSAGE = "Nieprawidłowe hasło. Spróbuj ponownie."
_ERROR_ROW_HEIGHT = 36
_SHUTDOWN_DELAY_MS = 80


@dataclass
class _UnlockState:
    success: bool = False
    closing: bool = False


def _center_window(root: ctk.CTk, *, width: int, height: int) -> None:
    root.update_idletasks()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")


def _cancel_pending_after(root: ctk.CTk) -> None:
    try:
        pending = root.tk.call("after", "info")
    except tkinter.TclError:
        return
    if not pending:
        return
    for after_id in pending:
        try:
            root.after_cancel(after_id)
        except tkinter.TclError:
            pass


def _prepare_shutdown(root: ctk.CTk) -> None:
    if not root.winfo_exists():
        return
    try:
        root.withdraw()
        root.update_idletasks()
    except tkinter.TclError:
        return
    _cancel_pending_after(root)


def _destroy_root(root: ctk.CTk) -> None:
    _prepare_shutdown(root)
    if not root.winfo_exists():
        return
    try:
        root.destroy()
    except tkinter.TclError:
        pass


def prompt_unlock() -> bool:
    """Pokazuje bramkę odblokowania. True = kontynuuj, False = zakończ aplikację."""
    ui_theme.apply_app_theme()

    state = _UnlockState()
    root = ctk.CTk()
    root.title("NeuroFlag — Odblokuj")
    root.resizable(False, False)

    container = ctk.CTkFrame(root, fg_color="transparent")
    container.pack(padx=32, pady=28)

    w.section_title(container, "Odblokuj aplikację").pack(anchor="w", pady=(0, 8))
    w.body_label(
        container,
        "Aplikacja jest chroniona hasłem startowym.",
        secondary=True,
    ).pack(anchor="w", pady=(0, 16))

    w.body_label(container, "Hasło").pack(anchor="w", pady=(0, 2))
    password_entry = ctk.CTkEntry(container, width=320, show="*", font=ui_theme.font_body())
    password_entry.pack(anchor="w", pady=(0, 8))

    error_row = ctk.CTkFrame(container, fg_color="transparent", height=_ERROR_ROW_HEIGHT)
    error_row.pack(anchor="w", fill="x", pady=(0, 12))
    error_row.pack_propagate(False)

    error_label = ctk.CTkLabel(
        error_row,
        text="",
        font=ui_theme.font_body(),
        text_color=ui_theme.COLOR_ERROR,
        anchor="nw",
        justify="left",
        wraplength=320,
    )
    error_label.pack(anchor="nw", fill="both", expand=True)

    def leave_mainloop() -> None:
        _prepare_shutdown(root)
        root.quit()

    def finish(success: bool) -> None:
        if state.closing:
            return
        state.closing = True
        state.success = success
        root.after(_SHUTDOWN_DELAY_MS, leave_mainloop)

    def on_unlock() -> None:
        if verify_password(password_entry.get()):
            finish(True)
            return
        error_label.configure(text=_ERROR_MESSAGE)
        password_entry.delete(0, "end")
        password_entry.focus_set()

    def on_close() -> None:
        finish(False)

    btn_row = ctk.CTkFrame(container, fg_color="transparent")
    btn_row.pack(anchor="e")
    w.primary_button(btn_row, text="Odblokuj", command=on_unlock, width=130).pack(side="right")

    root.bind("<Return>", lambda _event: on_unlock())
    root.protocol("WM_DELETE_WINDOW", on_close)

    _center_window(root, width=400, height=280)

    password_entry.focus_set()
    root.mainloop()

    success = state.success
    _destroy_root(root)
    return success
