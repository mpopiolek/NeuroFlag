from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.domain.errors import PipelineError

if TYPE_CHECKING:
    import mne.io

_CANONICAL_CHANNELS = frozenset({"C3", "O1"})
_REQUIRED_CANONICAL = ("C3", "O1")


def _canonical_channel(name: str) -> str | None:
    upper = name.strip().upper()
    normalized = re.sub(r"^EEG\s+", "", upper)
    normalized = re.sub(r"-(REF|A1|LE)$", "", normalized)
    if normalized in _CANONICAL_CHANNELS:
        return normalized
    return None


def normalize_channel_names(raw: mne.io.BaseRaw) -> None:
    """Standaryzuje nazwy kanałów (np. EEG C3, C3-REF) do C3 / O1 — in-place."""
    renames: dict[str, str] = {}
    for ch in raw.ch_names:
        target = _canonical_channel(ch)
        if target is not None and ch != target:
            renames[ch] = target
    if renames:
        raw.rename_channels(renames)


def require_channels(raw: mne.io.BaseRaw, names: tuple[str, ...]) -> None:
    """Wymaga obecności kanałów po normalizacji; inaczej PipelineError (PL)."""
    available = set(raw.ch_names)
    missing = [n for n in names if n not in available]
    if missing:
        listed = ", ".join(sorted(raw.ch_names)) if raw.ch_names else "(brak)"
        missing_str = ", ".join(missing)
        raise PipelineError(
            "missing_channels",
            f"Brak wymaganych kanałów: {missing_str}. "
            f"Dostępne kanały w pliku: {listed}.",
        )


def apply_channel_overrides(
    raw: mne.io.BaseRaw, overrides: dict[str, str]
) -> None:
    """Stosuje ręczne mapowanie kanałów (np. {"C3": "EEG 4"}) — in-place.

    Klucz: nazwa kanoniczna (C3/O1), wartość: istniejąca nazwa w pliku.
    """
    if not overrides:
        return
    existing = set(raw.ch_names)
    renames: dict[str, str] = {}
    for canonical, source in overrides.items():
        if source in existing and source != canonical:
            renames[source] = canonical
    if renames:
        raw.rename_channels(renames)


def get_missing_canonical(ch_names: list[str]) -> list[str]:
    """Zwraca listę kanałów kanonicznych (C3/O1) niedostępnych po normalizacji.

    Przyjmuje surowe nazwy z nagłówka pliku (przed preload).
    """
    reachable: set[str] = set()
    for name in ch_names:
        target = _canonical_channel(name)
        if target is not None:
            reachable.add(target)
    return [c for c in _REQUIRED_CANONICAL if c not in reachable]
