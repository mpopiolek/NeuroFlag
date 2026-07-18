from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.config.settings import clear_password, set_password


def _mock_app_window() -> MagicMock:
    app = MagicMock()
    app._lock_btn = MagicMock()
    app._history_btn = MagicMock()
    return app


def test_refresh_lock_button_hidden_without_password() -> None:
    from app.ui.app_window import AppWindow

    clear_password()
    app = _mock_app_window()
    AppWindow.refresh_lock_button(app)
    app._lock_btn.pack_forget.assert_called_once()


def test_refresh_lock_button_visible_with_password(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.ui.app_window import AppWindow

    settings_path = tmp_path / "settings.json"
    monkeypatch.setattr("app.config.settings.resolve_settings_path", lambda: settings_path)
    set_password("secret", settings_path)

    app = _mock_app_window()
    AppWindow.refresh_lock_button(app)
    app._lock_btn.pack.assert_called_once_with(
        side="right", padx=(8, 0), before=app._history_btn
    )
    app._lock_btn.configure.assert_called_once_with(state="normal")

    clear_password(settings_path)
