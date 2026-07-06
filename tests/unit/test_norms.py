from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from app.domain.norms import NormsLoadError, load, resolve_norms_path

def _valid_norms() -> list[dict[str, object]]:
    return [
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
            "Delta": {"l_freq": 0.5,  "h_freq": 4.0},
            "Theta": {"l_freq": 4.0,  "h_freq": 8.0},
            "Beta1": {"l_freq": 15.0, "h_freq": 18.0},
            "Beta2": {"l_freq": 18.0, "h_freq": 25.0},
        },
        "norms": _valid_norms(),
    }


def _legacy_payload() -> dict[str, object]:
    """Stary schemat z recommendation_threshold — używany do testu migracji."""
    return {
        "version": 1,
        "power_line_frequency": 50,
        "recommendation_threshold": 3,
        "band_ranges": {
            "Delta": {"l_freq": 0.5,  "h_freq": 4.0},
            "Theta": {"l_freq": 4.0,  "h_freq": 8.0},
            "Beta1": {"l_freq": 15.0, "h_freq": 18.0},
            "Beta2": {"l_freq": 18.0, "h_freq": 25.0},
        },
        "norms": _valid_norms(),
    }


def _write(tmp_path: Path, payload: object) -> Path:
    p = tmp_path / "norms.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_load_valid(tmp_path: Path) -> None:
    p = _write(tmp_path, _valid_payload())
    cfg = load(p)
    assert cfg.version == 1
    assert len(cfg.norms) == 10
    assert cfg.band_ranges["Theta"].l_freq == 4.0


def test_missing_norms_key(tmp_path: Path) -> None:
    payload = {k: v for k, v in _valid_payload().items() if k != "norms"}
    p = _write(tmp_path, payload)
    with pytest.raises(NormsLoadError, match="norms"):
        load(p)


def test_missing_power_line_frequency(tmp_path: Path) -> None:
    payload = {k: v for k, v in _valid_payload().items() if k != "power_line_frequency"}
    p = _write(tmp_path, payload)
    with pytest.raises(NormsLoadError, match="power_line_frequency"):
        load(p)


def test_too_few_norms(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["norms"] = _valid_norms()[:9]
    p = _write(tmp_path, payload)
    with pytest.raises(NormsLoadError, match="9"):
        load(p)


def test_norm_entry_missing_mean_z(tmp_path: Path) -> None:
    norms = _valid_norms()
    bad_entry = {k: v for k, v in norms[0].items() if k != "mean_z"}
    payload = _valid_payload()
    payload["norms"] = [bad_entry] + norms[1:]
    p = _write(tmp_path, payload)
    with pytest.raises(NormsLoadError, match="mean_z"):
        load(p)


def test_norm_entry_unknown_band(tmp_path: Path) -> None:
    norms = _valid_norms()
    bad_entry = dict(norms[0])
    bad_entry["band"] = "Alpha"
    payload = _valid_payload()
    payload["norms"] = [bad_entry] + norms[1:]
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


def test_resolve_norms_path_prefers_exe_dir_when_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe_path = tmp_path / "neuroflag.exe"
    exe_path.touch()
    norms_file = tmp_path / "norms.json"
    norms_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_path))
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "_internal"), raising=False)

    assert resolve_norms_path() == norms_file


def test_resolve_norms_path_falls_back_to_meipass_when_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe_path = tmp_path / "neuroflag.exe"
    exe_path.touch()
    meipass = tmp_path / "_internal"
    meipass.mkdir()
    bundled = meipass / "norms.json"
    bundled.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_path))
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)

    assert resolve_norms_path() == bundled


def test_load_new_schema_recommendation_rules(tmp_path: Path) -> None:
    p = _write(tmp_path, _valid_payload())
    cfg = load(p)
    assert cfg.recommendation_rules.indication_min_red == 5
    assert cfg.recommendation_rules.indication_max_green == 3
    assert cfg.recommendation_rules.no_indication_min_green == 4
    assert cfg.recommendation_rules.no_indication_max_red == 3


def test_load_new_schema_category_descriptions(tmp_path: Path) -> None:
    p = _write(tmp_path, _valid_payload())
    cfg = load(p)
    assert cfg.category_descriptions.wskazanie == "Opis wskazania"
    assert cfg.category_descriptions.obserwacja == "Opis obserwacji"
    assert cfg.category_descriptions.brak == "Opis braku"


def test_load_migrates_legacy_threshold_to_defaults(tmp_path: Path) -> None:
    p = _write(tmp_path, _legacy_payload())
    cfg = load(p)
    # Migracja mapuje stary klucz na domyślne progi 5/3/4/3
    assert cfg.recommendation_rules.indication_min_red == 5
    assert cfg.recommendation_rules.no_indication_min_green == 4


def test_load_legacy_uses_default_category_descriptions(tmp_path: Path) -> None:
    p = _write(tmp_path, _legacy_payload())
    cfg = load(p)
    # Stary schemat bez category_descriptions — używa domyślnych
    assert cfg.category_descriptions.wskazanie != ""
    assert cfg.category_descriptions.obserwacja != ""
    assert cfg.category_descriptions.brak != ""


def test_load_missing_both_rules_keys_raises(tmp_path: Path) -> None:
    payload = {k: v for k, v in _valid_payload().items()
               if k not in ("recommendation_rules", "recommendation_threshold")}
    p = _write(tmp_path, payload)
    with pytest.raises(NormsLoadError, match="recommendation_rules"):
        load(p)


def test_load_recommendation_rules_missing_field_raises(tmp_path: Path) -> None:
    payload = _valid_payload()
    rules = dict(payload["recommendation_rules"])  # type: ignore[arg-type]
    del rules["indication_min_red"]
    payload["recommendation_rules"] = rules
    p = _write(tmp_path, payload)
    with pytest.raises(NormsLoadError, match="indication_min_red"):
        load(p)


def test_load_category_descriptions_empty_string_raises(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["category_descriptions"] = {  # type: ignore[assignment]
        "wskazanie": "",
        "obserwacja": "ok",
        "brak": "ok",
    }
    p = _write(tmp_path, payload)
    with pytest.raises(NormsLoadError, match="wskazanie"):
        load(p)


def test_load_prefers_exe_dir_norms_when_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe_path = tmp_path / "neuroflag.exe"
    exe_path.touch()
    meipass = tmp_path / "_internal"
    meipass.mkdir()

    bundled_payload = _valid_payload()
    bundled_payload["version"] = 99
    (meipass / "norms.json").write_text(json.dumps(bundled_payload), encoding="utf-8")

    exe_payload = _valid_payload()
    exe_payload["version"] = 1
    (tmp_path / "norms.json").write_text(json.dumps(exe_payload), encoding="utf-8")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_path))
    monkeypatch.setattr(sys, "_MEIPASS", str(meipass), raising=False)

    cfg = load()
    assert cfg.version == 1
