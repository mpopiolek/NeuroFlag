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


def _as_float(value: object, label: str) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (ValueError, TypeError) as exc:
        raise NormsLoadError(f"'{label}' must be a number, got {value!r}") from exc


def _as_int(value: object, label: str) -> int:
    try:
        return int(float(value))  # type: ignore[arg-type]
    except (ValueError, TypeError) as exc:
        raise NormsLoadError(f"'{label}' must be an integer, got {value!r}") from exc


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
        result[name] = BandRange(
            l_freq=_as_float(entry["l_freq"], f"band_ranges.{name}.l_freq"),
            h_freq=_as_float(entry["h_freq"], f"band_ranges.{name}.h_freq"),
        )
    return result


def _parse_norm_entry(raw: Any, index: int) -> NormEntry:
    if not isinstance(raw, dict):
        raise NormsLoadError(f"norms[{index}] must be a JSON object")
    for key in _NORM_ENTRY_KEYS:
        if key not in raw:
            raise NormsLoadError(f"norms[{index}] missing key '{key}'")
    band = raw["band"]
    return NormEntry(
        norm_id=_as_int(raw["id"], f"norms[{index}].id"),
        channel=str(raw["channel"]),
        task=str(raw["task"]),
        band=str(band),
        mean_z=_as_float(raw["mean_z"], f"norms[{index}].mean_z"),
        mean_k=_as_float(raw["mean_k"], f"norms[{index}].mean_k"),
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

    for i, entry in enumerate(norm_entries):
        if entry.band not in band_ranges:
            raise NormsLoadError(
                f"norms[{i}] references band '{entry.band}' not defined in band_ranges"
            )

    return NormsConfig(
        version=_as_int(data["version"], "version"),
        power_line_frequency=_as_float(data["power_line_frequency"], "power_line_frequency"),
        recommendation_threshold=_as_int(
            data["recommendation_threshold"], "recommendation_threshold"
        ),
        band_ranges=band_ranges,
        norms=norm_entries,
    )
