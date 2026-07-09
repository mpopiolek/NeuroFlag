from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from app.ui import theme as t
from app.ui.app_window import AppState
from app.ui.components import widgets as w
from app.ui.components.info_dialog import build_info_content

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow


class InfoView(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTkBaseClass,
        app_window: AppWindow,
        app_state: AppState,
        *,
        return_view: type[ctk.CTkFrame] | None = None,
        **kwargs: object,
    ) -> None:
        from app.ui.navigation import back_label_for
        from app.ui.views.metadata_form import MetadataFormView

        super().__init__(master, **kwargs)
        self._app_window = app_window
        del app_state, kwargs
        self._return_view = return_view or MetadataFormView

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        page = w.page_container(self)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)

        w.page_title(page, "Informacje — NeuroFlag").grid(
            row=0, column=0, sticky="w", pady=(0, 12)
        )

        scroll = ctk.CTkScrollableFrame(page, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        w.bind_auto_hide_scrollbar(scroll)

        build_info_content(scroll, wraplength=t.WRAP_WIDTH - 80)

        self._app_window.set_footer(
            back_text=back_label_for(self._return_view),
            back_cmd=self._on_back,
            back_visible=True,
        )

    def _on_back(self) -> None:
        self._app_window.show_view(self._return_view)
