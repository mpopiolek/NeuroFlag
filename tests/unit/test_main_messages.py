from __future__ import annotations

from app.domain.norms import NormsLoadError
from app.main import format_norms_error_message


def test_format_norms_error_message() -> None:
    message = format_norms_error_message(NormsLoadError("test"))
    assert "norms.json" in message
    assert "neuroflag.exe" in message
    assert "norms.json.template" in message
