from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.domain.norms import NormsLoadError, load


def _write(tmp_path: Path, payload: object) -> Path:
    p = tmp_path / "norms.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def _valid_payload() -> dict[str, object]:
    return {
        "version": 1,
        "power_line_frequency": 50,
        "recommendation_rules": {
            "indication_min_red": 5,
            "indication_max_green": 3,
            "no_indication_min_green": 4,
            "no_indication_max_red": 3,
        },
        "category_descriptions": {
            "wskazanie": "Opis wskazania",
            "obserwacja": "Opis obserwacji",
            "brak": "Opis braku",
        },
        "band_ranges": {
            "Delta": {"l_freq": 0.5, "h_freq": 4.0},
            "Theta": {"l_freq": 4.0, "h_freq": 8.0},
            "Beta1": {"l_freq": 15.0, "h_freq": 18.0},
            "Beta2": {"l_freq": 18.0, "h_freq": 25.0},
        },
        "norms": [
            {"id": 1,  "channel": "C3", "task": "OZ", "band": "Theta",
             "mean_z": 30.35, "mean_k": 35.44},
            {"id": 2,  "channel": "C3", "task": "ZP", "band": "Theta",
             "mean_z": 20.32, "mean_k": 25.25},
            {"id": 3,  "channel": "C3", "task": "ZP", "band": "Beta1",
             "mean_z": 5.26,  "mean_k": 6.56},
            {"id": 4,  "channel": "C3", "task": "OO", "band": "Beta2",
             "mean_z": 5.18,  "mean_k": 6.29},
            {"id": 5,  "channel": "O1", "task": "OO", "band": "Delta",
             "mean_z": 25.5,  "mean_k": 28.63},
            {"id": 6,  "channel": "O1", "task": "OO", "band": "Theta",
             "mean_z": 18.23, "mean_k": 21.95},
            {"id": 7,  "channel": "O1", "task": "OZ", "band": "Theta",
             "mean_z": 27.02, "mean_k": 42.18},
            {"id": 8,  "channel": "O1", "task": "ZP", "band": "Theta",
             "mean_z": 18.04, "mean_k": 26.39},
            {"id": 9,  "channel": "O1", "task": "OO", "band": "Beta2",
             "mean_z": 3.51,  "mean_k": 5.36},
            {"id": 10, "channel": "O1", "task": "ZP", "band": "Beta2",
             "mean_z": 6.22,  "mean_k": 7.95},
        ],
    }


def _mutate_empty_json(p: dict[str, object]) -> dict[str, object]:
    p.clear()
    return p


def _mutate_wrong_type_power_line_frequency(p: dict[str, object]) -> dict[str, object]:
    p["power_line_frequency"] = "pięćdziesiąt"
    return p


def _mutate_missing_band_ranges(p: dict[str, object]) -> dict[str, object]:
    del p["band_ranges"]
    return p


def _mutate_missing_version(p: dict[str, object]) -> dict[str, object]:
    del p["version"]
    return p


def _mutate_invalid_band_range_l_freq_gt_h_freq(p: dict[str, object]) -> dict[str, object]:
    p["band_ranges"]["Delta"] = {"l_freq": 4.0, "h_freq": 0.5}  # type: ignore[index]
    return p


def _mutate_equal_l_freq_h_freq(p: dict[str, object]) -> dict[str, object]:
    p["band_ranges"]["Delta"] = {"l_freq": 4.0, "h_freq": 4.0}  # type: ignore[index]
    return p


def _mutate_mean_z_gte_mean_k(p: dict[str, object]) -> dict[str, object]:
    p["norms"][0]["mean_z"] = p["norms"][0]["mean_k"]  # type: ignore[index]
    return p


_VARIANTS: list[tuple[str, Any, str]] = [
    ("empty_json", _mutate_empty_json, "missing required key"),
    ("wrong_type_power_line_frequency", _mutate_wrong_type_power_line_frequency,
     "must be a number"),
    ("missing_band_ranges", _mutate_missing_band_ranges, "band_ranges"),
    ("missing_version", _mutate_missing_version, "version"),
    ("invalid_band_range_l_freq_gt_h_freq", _mutate_invalid_band_range_l_freq_gt_h_freq, "l_freq"),
    ("equal_l_freq_h_freq", _mutate_equal_l_freq_h_freq, "l_freq"),
    ("mean_z_gte_mean_k", _mutate_mean_z_gte_mean_k, "mean_z"),
]


@pytest.mark.parametrize(
    "mutator,expected_match",
    [(m, e) for _, m, e in _VARIANTS],
    ids=[name for name, _, _ in _VARIANTS],
)
def test_load_invalid_variant(
    tmp_path: Path,
    mutator: Any,
    expected_match: str,
) -> None:
    payload = mutator(_valid_payload())
    p = _write(tmp_path, payload)
    with pytest.raises(NormsLoadError, match=expected_match):
        load(p)
