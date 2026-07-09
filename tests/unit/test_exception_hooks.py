from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from app.ui import exception_hooks


@pytest.fixture(autouse=True)
def _reset_app_window_ref() -> None:
    exception_hooks._app_window_ref = None
    yield
    exception_hooks._app_window_ref = None


def test_gui_excepthook_schedules_dialog_for_runtime_error() -> None:
    app_window = MagicMock()
    exception_hooks.register_app_window(app_window)

    exception_hooks.gui_excepthook(RuntimeError, RuntimeError("boom"), None)

    app_window.after.assert_called_once()
    assert app_window.after.call_args[0][0] == 0


def test_gui_excepthook_passes_through_keyboard_interrupt() -> None:
    app_window = MagicMock()
    exception_hooks.register_app_window(app_window)

    with patch.object(sys, "__excepthook__") as mock_hook:
        exception_hooks.gui_excepthook(
            KeyboardInterrupt,
            KeyboardInterrupt(),
            None,
        )

    mock_hook.assert_called_once()
    app_window.after.assert_not_called()


def test_install_gui_exception_hooks_wires_sys_and_tk() -> None:
    app_window = MagicMock()
    exception_hooks.install_gui_exception_hooks(app_window)

    assert sys.excepthook is exception_hooks.gui_excepthook
    assert app_window.report_callback_exception is exception_hooks.gui_excepthook
