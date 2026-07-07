from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import customtkinter as ctk

from app.ui import theme as t

Justify = Literal["left", "center", "right"]
ButtonState = Literal["normal", "disabled"]


def page_container(parent: ctk.CTkBaseClass) -> ctk.CTkFrame:
    """Główny kontener widoku ze standardowymi marginesami."""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="both", expand=True, padx=t.PAGE_PAD_X, pady=t.PAGE_PAD_Y)
    return frame


def page_title(parent: ctk.CTkBaseClass, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent,
        text=text,
        font=t.font_title(),
        text_color=t.COLOR_TEXT,
        anchor="w",
    )


def section_title(parent: ctk.CTkBaseClass, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent,
        text=text,
        font=t.font_subheading(),
        text_color=t.COLOR_TEXT,
        anchor="w",
    )


def body_label(
    parent: ctk.CTkBaseClass,
    text: str,
    *,
    secondary: bool = False,
    wraplength: int | None = None,
    justify: Justify = "left",
) -> ctk.CTkLabel:
    color = t.COLOR_TEXT_SECONDARY if secondary else t.COLOR_TEXT
    label_kwargs: dict[str, str | int | ctk.CTkFont] = {
        "text": text,
        "font": t.font_body(),
        "text_color": color,
        "anchor": "w",
        "justify": justify,
    }
    if wraplength is not None:
        label_kwargs["wraplength"] = wraplength
    return ctk.CTkLabel(parent, **label_kwargs)


def info_box(
    parent: ctk.CTkBaseClass,
    text: str,
    *,
    wraplength: int = t.WRAP_WIDTH,
) -> ctk.CTkFrame:
    frame = ctk.CTkFrame(
        parent,
        fg_color=t.COLOR_SURFACE,
        corner_radius=t.CORNER_RADIUS_SM,
        border_width=1,
        border_color=t.COLOR_BORDER,
    )
    ctk.CTkLabel(
        frame,
        text=text,
        wraplength=wraplength,
        justify="left",
        font=t.font_small(),
        text_color=t.COLOR_TEXT_SECONDARY,
    ).pack(padx=14, pady=10, anchor="w")
    return frame


def primary_button(
    parent: ctk.CTkBaseClass,
    text: str,
    command: Callable[[], None] | None = None,
    *,
    width: int = 160,
    state: ButtonState = "normal",
) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        font=t.font_body(),
        state=state,
    )


def secondary_button(
    parent: ctk.CTkBaseClass,
    text: str,
    command: Callable[[], None] | None = None,
    *,
    width: int = 140,
    state: ButtonState = "normal",
) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        font=t.font_body(),
        fg_color="transparent",
        border_width=1,
        border_color=t.COLOR_BORDER,
        text_color=t.COLOR_TEXT,
        hover_color=t.COLOR_SURFACE,
        state=state,
    )


def danger_button(
    parent: ctk.CTkBaseClass,
    text: str,
    command: Callable[[], None] | None = None,
    *,
    width: int = 80,
) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        font=t.font_small(),
        fg_color=t.COLOR_DANGER,
        hover_color=t.COLOR_DANGER_HOVER,
    )


def bind_auto_hide_scrollbar(scrollable: ctk.CTkScrollableFrame) -> Callable[[], None]:
    """Ukrywa pasek CTkScrollableFrame, gdy treść mieści się w widocznym obszarze.

    CustomTkinter zawsze rezerwuje miejsce na scrollbar — ten helper porównuje
    wysokość zawartości z wysokością canvas i wywołuje grid_remove()/grid().
    """
    canvas = scrollable._parent_canvas
    scrollbar = scrollable._scrollbar

    def sync() -> None:
        scrollable.update_idletasks()
        bbox = canvas.bbox("all")
        if bbox is None:
            return
        content_height = bbox[3] - bbox[1]
        viewport_height = canvas.winfo_height()
        if viewport_height <= 1:
            return
        if content_height <= viewport_height:
            scrollbar.grid_remove()
            canvas.yview_moveto(0)
        else:
            scrollbar.grid()

    def on_configure(_event: object | None = None) -> None:
        scrollable.after_idle(sync)

    scrollable.bind("<Configure>", on_configure, add="+")
    canvas.bind("<Configure>", on_configure, add="+")
    scrollable.bind("<Map>", on_configure, add="+")
    scrollable.after_idle(sync)
    return sync
