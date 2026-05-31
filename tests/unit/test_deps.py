from __future__ import annotations

import sys

import pytest


def test_prod_deps_importable() -> None:
    import numpy
    import reportlab
    import scipy

    assert isinstance(numpy.__version__, str)
    assert isinstance(scipy.__version__, str)
    assert isinstance(reportlab.Version, str)

    mne = pytest.importorskip("mne", reason="mne nie zainstalowane lokalnie; weryfikowane przez CI")
    assert isinstance(mne.__version__, str)


@pytest.mark.skipif(
    sys.platform != "win32",
    reason="customtkinter wymaga Tcl/Tk; weryfikowane przez Windows smoke-test",
)
def test_customtkinter_importable() -> None:
    import customtkinter

    assert customtkinter is not None
