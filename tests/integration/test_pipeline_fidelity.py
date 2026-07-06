from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

mne = pytest.importorskip("mne")

from app.domain.eeg_file import read_raw_digitrack
from app.domain.errors import PipelineError
from app.domain.pipeline import run
from app.domain.types import NormsConfig

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sample_digitrack.eeg"
_MIN_DURATION_S = 480.0
# Zgodnie z pipeline._MIN_RECORDING_TOLERANCE_S — ostatnia próbka @ 250 Hz daje ~479.996 s
_MIN_DURATION_TOLERANCE_S = 1.0
_AMPLITUDE_FLOOR_UV = 5.0
_AMPLITUDE_CEILING_UV = 200.0


def _synthetic_raw_with_annotations(*, peak_uv: float = 50.0) -> mne.io.BaseRaw:
    """Raw 600 s z adnotacjami OO/OZ/ZP i energią we wszystkich pasmach norm."""
    sfreq = 250.0
    duration = 600.0
    n_samples = int(duration * sfreq)
    ch_names = ["C3", "O1", "EOG"]
    info = mne.create_info(ch_names, sfreq=sfreq, ch_types=["eeg", "eeg", "eog"])
    times = np.arange(n_samples, dtype=np.float64) / sfreq
    amp_v = peak_uv * 1e-6
    # Delta 2 Hz, Theta 6 Hz, Beta1 16 Hz, Beta2 22 Hz — pokrywa wszystkie pasma w norms.json
    signal = (
        np.sin(2 * np.pi * 2.0 * times)
        + np.sin(2 * np.pi * 6.0 * times)
        + np.sin(2 * np.pi * 16.0 * times)
        + np.sin(2 * np.pi * 22.0 * times)
    )
    eeg = amp_v * signal
    data = np.stack(
        [
            eeg,
            amp_v * (signal + 0.25),
            amp_v * np.sin(2 * np.pi * 10.0 * times),
        ]
    )
    raw = mne.io.RawArray(data, info)
    onsets = [0.0, 180.0, 360.0]
    durations = [180.0, 180.0, 180.0]
    descriptions = ["OO", "OZ", "ZP"]
    raw.set_annotations(mne.Annotations(onsets, durations, descriptions))
    return raw


@pytest.mark.skipif(not FIXTURE.exists(), reason="Brak fixture sample_digitrack.eeg")
def test_fixture_duration_at_least_eight_minutes() -> None:
    raw = read_raw_digitrack(FIXTURE)
    assert float(raw.times[-1]) >= _MIN_DURATION_S - _MIN_DURATION_TOLERANCE_S


@patch("app.domain.pipeline._load_raw")
def test_run_preserves_amplitude_bounds_on_clean_synthetic(
    mock_load: object,
    real_norms_config: NormsConfig,
) -> None:
    mock_load.return_value = _synthetic_raw_with_annotations()
    result = run(Path("synthetic.edf"), real_norms_config)
    assert len(result) == 10
    assert all(_AMPLITUDE_FLOOR_UV < v < _AMPLITUDE_CEILING_UV for v in result)


@patch("app.domain.pipeline._load_raw")
def test_run_raises_artifact_rejection_when_segment_exceeds_200_uv(
    mock_load: object,
    real_norms_config: NormsConfig,
) -> None:
    mock_load.return_value = _synthetic_raw_with_annotations(peak_uv=300.0)
    with pytest.raises(PipelineError) as exc_info:
        run(Path("synthetic.edf"), real_norms_config)
    assert exc_info.value.code == "artifact_rejection"
