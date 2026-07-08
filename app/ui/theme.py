from __future__ import annotations

import sys
from pathlib import Path

import customtkinter as ctk

# --- Layout ---
PAGE_PAD_X = 48
PAGE_PAD_Y = 36
CORNER_RADIUS = 8
CORNER_RADIUS_SM = 6
CORNER_RADIUS_CARD = 12
WRAP_WIDTH = 720
CONTENT_MAX_WIDTH = 960
COL_FORM_WEIGHT = 3
COL_CONTEXT_WEIGHT = 2
BREAKPOINT_STACK_COLS = 900

# --- Semantic colors (explicit overrides beyond CTk theme JSON) ---
COLOR_TEXT = "#1A2B3C"
COLOR_TEXT_SECONDARY = "#5A6B7C"
COLOR_TEXT_MUTED = "#8899AA"
COLOR_SUCCESS = "#2D7A4F"
COLOR_WARNING = "#A07000"
COLOR_ERROR = "#C53030"
COLOR_SURFACE = "#EDF2F7"
COLOR_SURFACE_ELEVATED = "#FFFFFF"
COLOR_CARD = "#FFFFFF"
COLOR_ROW_BG = "#F7F9FC"
COLOR_BORDER = "#D8E2EC"
COLOR_HEADER_BG = "#FFFFFF"
COLOR_MINT_STRIPE = "#B8D8D0"
COLOR_NAVY = "#1E3A5F"
COLOR_CONTROL_ACTIVE = "#1E3A5F"
COLOR_CONTROL_HOVER = "#152E4A"
COLOR_CONTROL_BORDER = "#CBD5E0"
COLOR_ACCENT = "#F9A825"
COLOR_ACCENT_HOVER = "#E09000"
COLOR_ACCENT_HOVER_DEEP = "#C87F00"
COLOR_SECTION_NAVY = "#283593"
COLOR_ON_NAVY = "#FFFFFF"
COLOR_DANGER = "#C53030"
COLOR_DANGER_HOVER = "#9B2C2C"
COLOR_ON_ACCENT = "#FFFFFF"


def resolve_theme_path() -> Path:
    """Ścieżka do neuroflag.json — obok modułu w dev i w paczce PyInstaller."""
    local = Path(__file__).parent / "assets" / "themes" / "neuroflag.json"
    if local.is_file():
        return local
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass is not None:
            bundled = Path(str(meipass)) / "app" / "ui" / "assets" / "themes" / "neuroflag.json"
            if bundled.is_file():
                return bundled
    return local


def apply_app_theme() -> None:
    """Stosuje tryb jasny i motyw NeuroFlag."""
    ctk.set_appearance_mode("light")
    theme_path = resolve_theme_path()
    if theme_path.is_file():
        ctk.set_default_color_theme(str(theme_path))
    else:
        ctk.set_default_color_theme("blue")


def font_title() -> ctk.CTkFont:
    return ctk.CTkFont(size=24, weight="bold")


def font_heading() -> ctk.CTkFont:
    return ctk.CTkFont(size=20, weight="bold")


def font_subheading() -> ctk.CTkFont:
    return ctk.CTkFont(size=15, weight="bold")


def font_body() -> ctk.CTkFont:
    return ctk.CTkFont(size=13)


def font_small() -> ctk.CTkFont:
    return ctk.CTkFont(size=12)


def font_caption() -> ctk.CTkFont:
    return ctk.CTkFont(size=11)
