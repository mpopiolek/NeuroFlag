from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from app.domain.types import BandRange, NormEntry, NormsConfig

REQUIRED_NORM_COUNT = 10
VALID_BANDS: frozenset[str] = frozenset({"Delta", "Theta", "Beta1", "Beta2"})

_TOP_LEVEL_KEYS = frozenset(
    {"version", "power_line_frequency", "recommendation_threshold", "band_ranges", "norms"}
)
_NORM_ENTRY_KEYS = frozenset({"id", "channel", "task", "band", "mean_z", "mean_k"})


class NormsLoadError(Exception):
    pass


def resolve_norms_path() -> Path:
    base = Path(getattr(sys, "_MEIPASS", None) or Path(__file__).parent.parent.parent)
    return base / "norms.json"


def _parse_band_ranges(raw: Any) -> dict[str, BandRange]:
    if not isinstance(raw, dict):
        raise NormsLoadError("'band_ranges' must be a JSON object")
    result: dict[str, BandRange] = {}
    for name, entry in raw.items():
        if not isinstance(entry, dict):
            raise NormsLoadError(f"band_ranges['{name}'] must be a JSON object")
        for key in ("l_freq", "h_freq"):
            if key not in entry:
                raise NormsLoadError(f"band_ranges['{name}'] missing key '{key}'")
        result[name] = BandRange(l_freq=float(entry["l_freq"]), h_freq=float(entry["h_freq"]))
    return result


def _parse_norm_entry(raw: Any, index: int) -> NormEntry:
    if not isinstance(raw, dict):
        raise NormsLoadError(f"norms[{index}] must be a JSON object")
    for key in _NORM_ENTRY_KEYS:
        if key not in raw:
            raise NormsLoadError(f"norms[{index}] missing key '{key}'")
    band = raw["band"]
    if band not in VALID_BANDS:
        raise NormsLoadError(
            f"norms[{index}] has unknown band '{band}'; valid: {sorted(VALID_BANDS)}"
        )
    return NormEntry(
        norm_id=int(raw["id"]),
        channel=str(raw["channel"]),
        task=str(raw["task"]),
        band=str(band),
        mean_z=float(raw["mean_z"]),
        mean_k=float(raw["mean_k"]),
    )


def load(path: Path | None = None) -> NormsConfig:
    resolved = path if path is not None else resolve_norms_path()
    try:
        text = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        raise NormsLoadError(f"Cannot read norms file '{resolved}': {exc}") from exc
    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise NormsLoadError(f"Invalid JSON in '{resolved}': {exc}") from exc

    if not isinstance(data, dict):
        raise NormsLoadError("norms.json root must be a JSON object")

    for key in _TOP_LEVEL_KEYS:
        if key not in data:
            raise NormsLoadError(f"norms.json missing required key '{key}'")

    raw_norms: Any = data["norms"]
    if not isinstance(raw_norms, list):
        raise NormsLoadError("'norms' must be a JSON array")
    if len(raw_norms) != REQUIRED_NORM_COUNT:
        raise NormsLoadError(
            f"'norms' must contain exactly {REQUIRED_NORM_COUNT} entries, got {len(raw_norms)}"
        )

    band_ranges = _parse_band_ranges(data["band_ranges"])
    norm_entries = tuple(_parse_norm_entry(entry, i) for i, entry in enumerate(raw_norms))

    return NormsConfig(
        version=int(data["version"]),
        power_line_frequency=float(data["power_line_frequency"]),
        recommendation_threshold=int(data["recommendation_threshold"]),
        band_ranges=band_ranges,
        norms=norm_entries,
    )
