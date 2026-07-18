from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent


def test_should_prompt_unlock_when_password_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.main.is_password_enabled", lambda: False)
    from app.main import should_prompt_unlock

    assert should_prompt_unlock() is False


def test_should_prompt_unlock_when_password_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.main.is_password_enabled", lambda: True)
    from app.main import should_prompt_unlock

    assert should_prompt_unlock() is True


def test_smoke_test_exits_zero_without_unlock_prompt() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app.main", "--smoke-test"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=60,
    )
    assert result.returncode == 0
