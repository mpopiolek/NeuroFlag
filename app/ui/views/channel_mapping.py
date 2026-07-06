from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.ui import theme as t
from app.ui.app_window import AppState
from app.ui.components import widgets as w

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow

_PLACEHOLDER = "— wybierz —"


class ChannelMappingView(ctk.CTkFrame):
    """Dialog ręcznego mapowania kanałów C3/O1 na kanały z pliku EEG."""

    def __init__(
        self,
        master: ctk.CTk,
        app_window: AppWindow,
        app_state: AppState,
        missing_channels: list[str],
        **kwargs: object,
    ) -> None:
        super().__init__(master, **kwargs)
        self._app_window = app_window
        self._app_state = app_state
        self._missing_channels = missing_channels

        container = w.page_container(self)

        w.page_title(container, "Mapowanie kanałów EEG").pack(anchor="w", pady=(0, 8))

        w.body_label(
            container,
            (
                "Nie znaleziono kanałów C3/O1 pod standardowymi nazwami.\n"
                'Przypisz kanały z pliku do wymaganych pozycji i kliknij "Kontynuuj".'
            ),
            secondary=True,
            wraplength=t.WRAP_WIDTH,
            justify="left",
        ).pack(anchor="w", pady=(0, 20))

        available = [ch for ch in self._app_state.available_channels if ch]
        option_values = [_PLACEHOLDER] + sorted(available)

        self._menus: dict[str, ctk.CTkOptionMenu] = {}

        for canonical in missing_channels:
            row = ctk.CTkFrame(container, fg_color="transparent")
            row.pack(anchor="w", pady=(0, 12))

            label = w.section_title(row, f"{canonical}:")
            label.pack(side="left", padx=(0, 12))

            menu = ctk.CTkOptionMenu(
                row,
                values=option_values,
                width=260,
                font=t.font_body(),
                command=lambda _val: self._refresh_continue_button(),
            )
            menu.set(_PLACEHOLDER)
            menu.pack(side="left")
            self._menus[canonical] = menu

        self._status_label = ctk.CTkLabel(
            container,
            text="",
            text_color=t.COLOR_ERROR,
            font=t.font_body(),
            wraplength=t.WRAP_WIDTH,
        )
        self._status_label.pack(anchor="w", pady=(4, 0))

        button_row = ctk.CTkFrame(container, fg_color="transparent")
        button_row.pack(anchor="w", pady=(16, 0))

        self._continue_button = w.primary_button(
            button_row,
            text="Kontynuuj",
            command=self._on_continue,
            state="disabled",
            width=140,
        )
        self._continue_button.pack(side="left", padx=(0, 12))

        w.secondary_button(
            button_row,
            text="← Anuluj",
            command=self._on_cancel,
            width=120,
        ).pack(side="left")

    def _refresh_continue_button(self) -> None:
        all_set = all(
            self._menus[ch].get() != _PLACEHOLDER for ch in self._missing_channels
        )
        self._continue_button.configure(state="normal" if all_set else "disabled")

    def _on_continue(self) -> None:
        overrides: dict[str, str] = {}
        for canonical, menu in self._menus.items():
            chosen = menu.get()
            if chosen == _PLACEHOLDER:
                self._status_label.configure(
                    text="Wybierz kanał dla każdej pozycji przed kontynuacją."
                )
                return
            overrides[canonical] = chosen

        self._app_state.channel_overrides = overrides

        from app.ui.views.analysis import AnalysisView

        self._app_window.show_view(AnalysisView)

    def _on_cancel(self) -> None:
        self._app_state.channel_overrides = {}

        from app.ui.views.file_import import FileImportView

        self._app_window.show_view(FileImportView)
