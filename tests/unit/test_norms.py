from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain.norms import NormsLoadError, load

_VALID_NORMS: list[dict[str, object]] = [
    {"id": 1,  "channel": "C3", "task": "OZ", "band": "Theta", "mean_z": 30.35, "mean_k": 35.44},
    {"id": 2,  "channel": "C3", "task": "ZP", "band": "Theta", "mean_z": 20.32, "mean_k": 25.25},
    {"id": 3,  "channel": "C3", "task": "ZP", "band": "Beta1", "mean_z": 5.26,  "mean_k": 6.56},
    {"id": 4,  "channel": "C3", "task": "OO", "band": "Beta2", "mean_z": 5.18,  "mean_k": 6.29},
    {"id": 5,  "channel": "O1", "task": "OO", "band": "Delta", "mean_z": 25.5,  "mean_k": 28.63},
    {"id": 6,  "channel": "O1", "task": "OO", "band": "Theta", "mean_z": 18.23, "mean_k": 21.95},
    {"id": 7,  "channel": "O1", "task": "OZ", "band": "Theta", "mean_z": 27.02, "mean_k": 42.18},
    {"id": 8,  "channel": "O1", "task": "ZP", "band": "Theta", "mean_z": 18.04, "mean_k": 26.39},
    {"id": 9,  "channel": "O1", "task": "OO", "band": "Beta2", "mean_z": 3.51,  "mean_k": 5.36},
    {"id": 10, "channel": "O1", "task": "ZP", "band": "Beta2", "mean_z": 6.22,  "mean_k": 7.95},
]

_VALID_PAYLOAD: dict[str, object] = {
    "version": 1,
    "power_line_frequency": 50,
    "recommendation_threshold": 3,
    "band_ranges": {
        "Delta": {"l_freq": 0.5,  "h_freq": 4.0},
        "Theta": {"l_freq": 4.0,  "h_freq": 8.0},
        "Beta1": {"l_freq": 15.0, "h_freq": 18.0},
        "Beta2": {"l_freq": 18.0, "h_freq": 25.0},
    },
    "norms": _VALID_NORMS,
}


def _write(tmp_path: Path, payload: object) -> Path:
    p = tmp_path / "norms.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_load_valid(tmp_path: Path) -> None:
    p = _write(tmp_path, _VALID_PAYLOAD)
    cfg = load(p)
    assert cfg.version == 1
    assert len(cfg.norms) == 10
    assert cfg.band_ranges["Theta"].l_freq == 4.0


def test_missing_norms_key(tmp_path: Path) -> None:
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "norms"}
    p = _write(tmp_path, payload)
    with pytest.raises(NormsLoadError, match="norms"):
        load(p)


def test_missing_power_line_frequency(tmp_path: Path) -> None:
    payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "power_line_frequency"}
    p = _write(tmp_path, payload)
    with pytest.raises(NormsLoadError, match="power_line_frequency"):
        load(p)


def test_too_few_norms(tmp_path: Path) -> None:
    payload = dict(_VALID_PAYLOAD)
    payload["norms"] = _VALID_NORMS[:9]
    p = _write(tmp_path, payload)
    with pytest.raises(NormsLoadError, match="9"):
        load(p)


def test_norm_entry_missing_mean_z(tmp_path: Path) -> None:
    bad_entry = {k: v for k, v in _VALID_NORMS[0].items() if k != "mean_z"}
    payload = dict(_VALID_PAYLOAD)
    payload["norms"] = [bad_entry] + list(_VALID_NORMS[1:])
    p = _write(tmp_path, payload)
    with pytest.raises(NormsLoadError, match="mean_z"):
        load(p)


def test_norm_entry_unknown_band(tmp_path: Path) -> None:
    bad_entry = dict(_VALID_NORMS[0])
    bad_entry["band"] = "Alpha"
    payload = dict(_VALID_PAYLOAD)
    payload["norms"] = [bad_entry] + list(_VALID_NORMS[1:])
    p = _write(tmp_path, payload)
    with pytest.raises(NormsLoadError, match="Alpha"):
        load(p)


def test_invalid_json(tmp_path: Path) -> None:
    p = tmp_path / "norms.json"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(NormsLoadError, match="Invalid JSON"):
        load(p)


def test_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(NormsLoadError, match="Cannot read"):
        load(tmp_path / "nonexistent.json")
