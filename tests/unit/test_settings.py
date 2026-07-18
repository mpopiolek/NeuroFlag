from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from app.config.settings import (
    clear_password,
    is_password_enabled,
    resolve_settings_path,
    set_password,
    verify_password,
)


def test_resolve_settings_path_dev() -> None:
    path = resolve_settings_path()
    assert path.name == "settings.json"
    assert "app" not in path.parts[:-1] or path.parent.name != "app"


def test_resolve_settings_path_frozen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    exe_path = tmp_path / "neuroflag.exe"
    exe_path.touch()
    expected = tmp_path / "settings.json"

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe_path))

    assert resolve_settings_path() == expected


def test_no_file_password_disabled(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    assert not is_password_enabled(settings_path)
    assert not verify_password("secret", settings_path)


def test_set_password_creates_hash_not_plaintext(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    set_password("moje-haslo", settings_path)

    raw = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "password_hash" in raw
    assert "salt" in raw
    assert "iterations" in raw
    assert "moje-haslo" not in settings_path.read_text(encoding="utf-8")


def test_set_password_verify_ok_and_wrong(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    set_password("correct", settings_path)

    assert is_password_enabled(settings_path)
    assert verify_password("correct", settings_path)
    assert not verify_password("wrong", settings_path)


def test_clear_password_disables(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    set_password("secret", settings_path)
    assert is_password_enabled(settings_path)

    clear_password(settings_path)
    assert not settings_path.exists()
    assert not is_password_enabled(settings_path)
    assert not verify_password("secret", settings_path)


def test_corrupted_file_treated_as_disabled(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{not valid json", encoding="utf-8")

    assert not is_password_enabled(settings_path)
    assert not verify_password("anything", settings_path)


def test_incomplete_fields_treated_as_disabled(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps({"password_hash": "abc"}),
        encoding="utf-8",
    )

    assert not is_password_enabled(settings_path)
    assert not verify_password("anything", settings_path)
