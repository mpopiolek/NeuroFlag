from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent


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
        "band_ranges": {
            "Delta": {"l_freq": 0.5, "h_freq": 4.0},
            "Theta": {"l_freq": 4.0, "h_freq": 8.0},
            "Beta1": {"l_freq": 15.0, "h_freq": 18.0},
            "Beta2": {"l_freq": 18.0, "h_freq": 25.0},
        },
        "norms": [
            {"id": 1, "channel": "C3", "task": "OZ", "band": "Theta", "mean_z": 30.35, "mean_k": 35.44},
            {"id": 2, "channel": "C3", "task": "ZP", "band": "Theta", "mean_z": 20.32, "mean_k": 25.25},
            {"id": 3, "channel": "C3", "task": "ZP", "band": "Beta1", "mean_z": 5.26, "mean_k": 6.56},
            {"id": 4, "channel": "C3", "task": "OO", "band": "Beta2", "mean_z": 5.18, "mean_k": 6.29},
            {"id": 5, "channel": "O1", "task": "OO", "band": "Delta", "mean_z": 25.5, "mean_k": 28.63},
            {"id": 6, "channel": "O1", "task": "OO", "band": "Theta", "mean_z": 18.23, "mean_k": 21.95},
            {"id": 7, "channel": "O1", "task": "OZ", "band": "Theta", "mean_z": 27.02, "mean_k": 42.18},
            {"id": 8, "channel": "O1", "task": "ZP", "band": "Theta", "mean_z": 18.04, "mean_k": 26.39},
            {"id": 9, "channel": "O1", "task": "OO", "band": "Beta2", "mean_z": 3.51, "mean_k": 5.36},
            {"id": 10, "channel": "O1", "task": "ZP", "band": "Beta2", "mean_z": 6.22, "mean_k": 7.95},
        ],
    }


def _run_validate(tmp_path: Path, payload: object) -> subprocess.CompletedProcess[str]:
    p = tmp_path / "norms.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "app.main", "--validate-norms", str(p)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=30,
    )


def test_validate_norms_valid(tmp_path: Path) -> None:
    result = _run_validate(tmp_path, _valid_payload())
    assert result.returncode == 0
    assert "OK" in result.stdout


def test_validate_norms_invalid_missing_key(tmp_path: Path) -> None:
    payload = {k: v for k, v in _valid_payload().items() if k != "norms"}
    result = _run_validate(tmp_path, payload)
    assert result.returncode == 1
    assert "BŁĄD" in result.stderr


def test_validate_norms_file_not_found(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    result = subprocess.run(
        [sys.executable, "-m", "app.main", "--validate-norms", str(missing)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=30,
    )
    assert result.returncode == 1
    assert "BŁĄD" in result.stderr


def test_validate_norms_missing_path_arg() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app.main", "--validate-norms"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 2
