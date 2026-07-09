from __future__ import annotations

import sys
import traceback
import types
import weakref
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.ui.app_window import AppWindow

_app_window_ref: weakref.ReferenceType[AppWindow] | None = None


def register_app_window(app_window: AppWindow) -> None:
    global _app_window_ref
    _app_window_ref = weakref.ref(app_window)


def _schedule_uncaught_dialog(exc_type_name: str) -> None:
    if _app_window_ref is None:
        return
    app_window = _app_window_ref()
    if app_window is None:
        return

    def _show() -> None:
        from app.ui.components.uncaught_error_dialog import UncaughtErrorDialog

        UncaughtErrorDialog(app_window, app_window, exc_type_name)

    app_window.after(0, _show)


def gui_excepthook(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: types.TracebackType | None,
) -> None:
    if exc_type in (KeyboardInterrupt, SystemExit):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
    _schedule_uncaught_dialog(exc_type.__name__)


def install_gui_exception_hooks(app_window: AppWindow) -> None:
    register_app_window(app_window)
    sys.excepthook = gui_excepthook
    app_window.report_callback_exception = gui_excepthook
