from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.domain.errors import PipelineError

if TYPE_CHECKING:
    import mne.io

_CANONICAL_CHANNELS = frozenset({"C3", "O1"})


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
