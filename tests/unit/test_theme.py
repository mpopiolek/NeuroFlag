from __future__ import annotations

import json
from typing import Any

from app.ui.theme import (
    COLOR_ACCENT,
    COLOR_ACCENT_HOVER,
    COLOR_CONTROL_ACTIVE,
    COLOR_CONTROL_HOVER,
    COLOR_ON_NAVY,
    resolve_theme_path,
)


def _accent_pairs(theme: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Widget key paths whose light-mode values must match theme.py accent constants."""
    return [
        ("CTkButton", "fg_color", COLOR_ACCENT),
        ("CTkButton", "hover_color", COLOR_ACCENT_HOVER),
        ("CTkProgressBar", "progress_color", COLOR_ACCENT),
        ("CTkSlider", "button_color", COLOR_ACCENT),
        ("CTkSlider", "button_hover_color", COLOR_ACCENT_HOVER),
    ]


def _control_pairs(theme: dict[str, Any]) -> list[tuple[str, str, str]]:
    """Form controls use navy — not the orange CTA accent."""
    return [
        ("CTkCheckBox", "fg_color", COLOR_CONTROL_ACTIVE),
        ("CTkCheckBox", "hover_color", COLOR_CONTROL_HOVER),
        ("CTkRadioButton", "fg_color", COLOR_CONTROL_ACTIVE),
        ("CTkRadioButton", "hover_color", COLOR_CONTROL_HOVER),
        ("CTkOptionMenu", "fg_color", COLOR_CONTROL_ACTIVE),
        ("CTkOptionMenu", "button_color", COLOR_CONTROL_HOVER),
        ("CTkOptionMenu", "button_hover_color", COLOR_CONTROL_HOVER),
        ("CTkOptionMenu", "text_color", COLOR_ON_NAVY),
        ("CTkSegmentedButton", "selected_color", COLOR_CONTROL_ACTIVE),
        ("CTkSegmentedButton", "selected_hover_color", COLOR_CONTROL_HOVER),
    ]


def test_neuroflag_json_accent_colors_match_theme_constants() -> None:
    theme_path = resolve_theme_path()
    data = json.loads(theme_path.read_text(encoding="utf-8"))

    for widget, key, expected in _accent_pairs(data):
        actual = data[widget][key][0]
        assert actual == expected, f"{widget}.{key}[0]: expected {expected}, got {actual}"


def test_neuroflag_json_control_colors_match_theme_constants() -> None:
    theme_path = resolve_theme_path()
    data = json.loads(theme_path.read_text(encoding="utf-8"))

    for widget, key, expected in _control_pairs(data):
        actual = data[widget][key][0]
        assert actual == expected, f"{widget}.{key}[0]: expected {expected}, got {actual}"
