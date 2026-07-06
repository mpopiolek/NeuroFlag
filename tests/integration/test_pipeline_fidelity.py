from __future__ import annotations

from pathlib import Path

import pytest

mne = pytest.importorskip("mne")

from app.domain.eeg_file import read_raw_digitrack

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_digitrack.eeg"
_MIN_DURATION_S = 480.0
# Zgodnie z pipeline._MIN_RECORDING_TOLERANCE_S — ostatnia próbka @ 250 Hz daje ~479.996 s
_MIN_DURATION_TOLERANCE_S = 1.0


@pytest.mark.skipif(not FIXTURE.exists(), reason="Brak fixture sample_digitrack.eeg")
def test_fixture_duration_at_least_eight_minutes() -> None:
    raw = read_raw_digitrack(FIXTURE)
    assert float(raw.times[-1]) >= _MIN_DURATION_S - _MIN_DURATION_TOLERANCE_S
