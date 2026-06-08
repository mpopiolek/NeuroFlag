from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

mne = pytest.importorskip("mne")

from app.domain.errors import AnalysisCancelledError, PipelineError
from app.domain.norms import load, resolve_norms_path
from app.domain.pipeline import detect_task_segments, run


def _synthetic_raw_with_annotations() -> mne.io.BaseRaw:
    sfreq = 250.0
    duration = 600.0
    n_samples = int(duration * sfreq)
    ch_names = ["C3", "O1", "EOG"]
    info = mne.create_info(ch_names, sfreq=sfreq, ch_types=["eeg", "eeg", "eog"])
    times = np.arange(n_samples, dtype=np.float64) / sfreq
    amp_v = 50e-6  # 50 µV — poniżej progu odrzucenia 200 µV
    data = np.stack(
        [
            amp_v * np.sin(2 * np.pi * 6.0 * times),
            amp_v * np.sin(2 * np.pi * 6.0 * times + 0.5),
            amp_v * np.sin(2 * np.pi * 10.0 * times),
        ]
    )
    raw = mne.io.RawArray(data, info)
    onsets = [0.0, 180.0, 360.0]
    durations = [180.0, 180.0, 180.0]
    descriptions = ["OO", "OZ", "ZP"]
    raw.set_annotations(mne.Annotations(onsets, durations, descriptions))
    return raw


def test_detect_task_segments_from_annotations() -> None:
    raw = _synthetic_raw_with_annotations()
    segments = detect_task_segments(raw)
    assert set(segments) == {"OO", "OZ", "ZP"}
    assert segments["OO"] == (0.0, 180.0)
    assert segments["OZ"] == (180.0, 360.0)
    assert segments["ZP"] == (360.0, 540.0)


def test_detect_task_segments_fallback_without_annotations() -> None:
    sfreq = 250.0
    n_samples = int(600 * sfreq)
    info = mne.create_info(["C3", "O1"], sfreq=sfreq, ch_types=["eeg", "eeg"])
    raw = mne.io.RawArray(np.zeros((2, n_samples)), info)
    segments = detect_task_segments(raw)
    assert segments["OO"] == (0.0, 180.0)
    assert segments["ZP"][1] == 540.0


@patch("app.domain.pipeline._load_raw")
def test_run_returns_ten_finite_amplitudes(mock_load: object) -> None:
    mock_load.return_value = _synthetic_raw_with_annotations()
    config = load(resolve_norms_path())
    result = run(Path("synthetic.edf"), config)
    assert len(result) == 10
    assert all(np.isfinite(v) for v in result)


def test_run_cancel_check_raises() -> None:
    config = load(resolve_norms_path())
    with pytest.raises(AnalysisCancelledError):
        run(Path("dummy.edf"), config, cancel_check=lambda: True)


@patch("app.domain.pipeline._load_raw")
def test_run_missing_channels_after_normalize(mock_load: object) -> None:
    sfreq = 250.0
    n_samples = int(600 * sfreq)
    info = mne.create_info(["Fp1", "Fp2"], sfreq=sfreq, ch_types=["eeg", "eeg"])
    raw = mne.io.RawArray(np.zeros((2, n_samples)), info)
    onsets = [0.0, 180.0, 360.0]
    raw.set_annotations(mne.Annotations(onsets, [180.0] * 3, ["OO", "OZ", "ZP"]))
    mock_load.return_value = raw
    config = load(resolve_norms_path())
    with pytest.raises(PipelineError) as exc_info:
        run(Path("no_c3.edf"), config)
    assert exc_info.value.code == "missing_channels"
