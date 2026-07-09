from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from app.ui import theme as t
from app.ui.app_window import AppState
from app.ui.components import widgets as w

_PLACEHOLDER = "— wybierz —"


class ChannelMappingDialog(ctk.CTkToplevel):
    _DIALOG_WIDTH = 480
    _DIALOG_HEIGHT = 320

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        app_state: AppState,
        missing_channels: list[str],
        *,
        on_continue: Callable[[], None],
    ) -> None:
        super().__init__(master)
        self._app_state = app_state
        self._missing_channels = missing_channels
        self._on_continue = on_continue

        self.title("Mapowanie kanałów EEG")
        self.resizable(False, False)
        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=0, column=0, sticky="nsew", padx=24, pady=(20, 8))

        w.section_title(body, "Mapowanie kanałów EEG").pack(anchor="w", pady=(0, 8))

        w.body_label(
            body,
            (
                "Nie znaleziono kanałów C3/O1 pod standardowymi nazwami.\n"
                "Przypisz kanały z pliku do wymaganych pozycji."
            ),
            secondary=True,
            wraplength=self._DIALOG_WIDTH - 48,
            justify="left",
        ).pack(anchor="w", pady=(0, 16))

        available = [ch for ch in self._app_state.available_channels if ch]
        option_values = [_PLACEHOLDER] + sorted(available)
        self._menus: dict[str, ctk.CTkOptionMenu] = {}

        for canonical in missing_channels:
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(anchor="w", pady=(0, 10))

            w.body_label(row, f"{canonical}:").pack(side="left", padx=(0, 12))

            menu = ctk.CTkOptionMenu(
                row,
                values=option_values,
                width=240,
                font=t.font_body(),
                command=lambda _val: self._refresh_continue_button(),
            )
            menu.set(_PLACEHOLDER)
            menu.pack(side="left")
            self._menus[canonical] = menu

        self._status_label = ctk.CTkLabel(
            body,
            text="",
            text_color=t.COLOR_ERROR,
            font=t.font_small(),
            wraplength=self._DIALOG_WIDTH - 48,
        )
        self._status_label.pack(anchor="w", pady=(4, 0))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 20))

        self._continue_btn = w.primary_button(
            footer,
            text="Kontynuuj",
            command=self._submit,
            width=110,
            state="disabled",
        )
        self._continue_btn.pack(side="right")

        w.secondary_button(
            footer,
            text="Anuluj",
            command=self._on_cancel,
            width=110,
        ).pack(side="right", padx=(0, 8))

        self.bind("<Escape>", lambda _event: self._on_cancel())

        self.update_idletasks()
        self.geometry(f"{self._DIALOG_WIDTH}x{self._DIALOG_HEIGHT}")
        self.grab_set()
        self.lift()
        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))
        self._center_on_window(master)

    def _center_on_window(self, master: ctk.CTkBaseClass) -> None:
        self.update_idletasks()
        window_x = master.winfo_x()
        window_y = master.winfo_y()
        window_w = master.winfo_width()
        window_h = master.winfo_height()
        dialog_w = self.winfo_width()
        dialog_h = self.winfo_height()
        x = window_x + max(0, (window_w - dialog_w) // 2)
        y = window_y + max(0, (window_h - dialog_h) // 2)
        self.geometry(f"+{x}+{y}")

    def _refresh_continue_button(self) -> None:
        all_set = all(
            self._menus[ch].get() != _PLACEHOLDER for ch in self._missing_channels
        )
        self._continue_btn.configure(state="normal" if all_set else "disabled")

    def _submit(self) -> None:
        overrides: dict[str, str] = {}
        for canonical, menu in self._menus.items():
            chosen = menu.get()
            if chosen == _PLACEHOLDER:
                self._status_label.configure(
                    text="Wybierz kanał dla każdej pozycji przed kontynuacją."
                )
                return
            overrides[canonical] = chosen

        if len(set(overrides.values())) != len(overrides):
            self._status_label.configure(
                text="Każda pozycja (C3, O1) musi wskazywać inny kanał fizyczny."
            )
            return

        self._app_state.channel_overrides = overrides
        self.grab_release()
        self.destroy()
        self._on_continue()

    def _on_cancel(self) -> None:
        self._app_state.channel_overrides = {}
        self.grab_release()
        self.destroy()


def show_channel_mapping_dialog(
    master: ctk.CTkBaseClass,
    app_state: AppState,
    missing_channels: list[str],
    *,
    on_continue: Callable[[], None],
) -> ChannelMappingDialog:
    """Otwiera modal mapowania kanałów C3/O1."""
    dialog = ChannelMappingDialog(
        master,
        app_state,
        missing_channels,
        on_continue=on_continue,
    )
    return dialog
