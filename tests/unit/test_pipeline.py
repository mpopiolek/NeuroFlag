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


def test_detect_task_segments_fallback_at_eight_minutes() -> None:
    sfreq = 250.0
    n_samples = int(480 * sfreq)
    info = mne.create_info(["C3", "O1"], sfreq=sfreq, ch_types=["eeg", "eeg"])
    raw = mne.io.RawArray(np.zeros((2, n_samples)), info)
    segments = detect_task_segments(raw)
    assert segments["OO"] == (0.0, 180.0)
    assert segments["OZ"] == (180.0, 360.0)
    assert segments["ZP"][0] == 360.0
    assert segments["ZP"][1] == pytest.approx(480.0, abs=0.01)


def test_detect_task_segments_rejects_partial_markers() -> None:
    sfreq = 250.0
    n_samples = int(600 * sfreq)
    info = mne.create_info(["C3", "O1"], sfreq=sfreq, ch_types=["eeg", "eeg"])
    raw = mne.io.RawArray(np.zeros((2, n_samples)), info)
    raw.set_annotations(
        mne.Annotations(
            [60.0, 240.0],
            [0.0, 0.0],
            ["Oczy otwarte", "Oczy zamknięte"],
        )
    )
    with pytest.raises(PipelineError) as exc_info:
        detect_task_segments(raw)
    assert exc_info.value.code == "missing_task_segments"


def test_detect_task_segments_rejects_short_recording() -> None:
    sfreq = 250.0
    n_samples = int(420 * sfreq)  # 7 min
    info = mne.create_info(["C3", "O1"], sfreq=sfreq, ch_types=["eeg", "eeg"])
    raw = mne.io.RawArray(np.zeros((2, n_samples)), info)
    raw.set_annotations(
        mne.Annotations(
            [60.0, 180.0, 300.0],
            [0.0, 0.0, 0.0],
            ["Oczy otwarte", "Oczy zamknięte", "Zadanie poznawcze"],
        )
    )
    with pytest.raises(PipelineError) as exc_info:
        detect_task_segments(raw)
    assert exc_info.value.code == "insufficient_duration"


def test_detect_task_segments_polish_markers_with_zero_duration() -> None:
    sfreq = 250.0
    duration = 900.0
    n_samples = int(duration * sfreq)
    info = mne.create_info(["C3", "O1"], sfreq=sfreq, ch_types=["eeg", "eeg"])
    raw = mne.io.RawArray(np.zeros((2, n_samples)), info)
    onsets = [157.4, 305.9, 459.1]
    durations = [0.0, 0.0, 0.0]
    descriptions = [
        "10:51:38 Oczy otwarte",
        "10:54:06 Oczy zamknięte",
        "10:56:40 zadanie poznawcze matematyka",
    ]
    raw.set_annotations(mne.Annotations(onsets, durations, descriptions))
    segments = detect_task_segments(raw)
    assert segments["OO"] == (157.4, 305.9)
    assert segments["OZ"] == (305.9, 459.1)
    assert segments["ZP"] == (459.1, 639.1)


def test_detect_task_segments_zp_aliases_matematyka_poznawcza_and_mat() -> None:
    sfreq = 250.0
    duration = 900.0
    n_samples = int(duration * sfreq)
    info = mne.create_info(["C3", "O1"], sfreq=sfreq, ch_types=["eeg", "eeg"])
    raw = mne.io.RawArray(np.zeros((2, n_samples)), info)
    raw.set_annotations(
        mne.Annotations(
            [100.0, 280.0, 460.0],
            [0.0, 0.0, 0.0],
            ["Oczy otwarte", "Oczy zamknięte", "11:02:00 matematyka poznawcza"],
        )
    )
    segments = detect_task_segments(raw)
    assert segments["ZP"][0] == 460.0

    raw2 = mne.io.RawArray(np.zeros((2, n_samples)), info)
    raw2.set_annotations(
        mne.Annotations(
            [100.0, 280.0, 460.0],
            [0.0, 0.0, 0.0],
            ["Oczy otwarte", "Oczy zamknięte", "Mat."],
        )
    )
    segments2 = detect_task_segments(raw2)
    assert segments2["ZP"][0] == 460.0


def test_detect_task_segments_oo_starts_at_first_marker_not_zero() -> None:
    sfreq = 250.0
    duration = 900.0
    n_samples = int(duration * sfreq)
    info = mne.create_info(["C3", "O1"], sfreq=sfreq, ch_types=["eeg", "eeg"])
    raw = mne.io.RawArray(np.zeros((2, n_samples)), info)
    raw.set_annotations(
        mne.Annotations(
            [45.0, 240.0, 420.0],
            [0.0, 0.0, 0.0],
            ["Oczy otwarte", "Oczy zamknięte", "Matematyka"],
        )
    )
    segments = detect_task_segments(raw)
    assert segments["OO"] == (45.0, 240.0)
    assert segments["OZ"] == (240.0, 420.0)


def test_detect_task_segments_skips_wrong_order_then_finds_oo_oz_zp() -> None:
    sfreq = 250.0
    duration = 900.0
    n_samples = int(duration * sfreq)
    info = mne.create_info(["C3", "O1"], sfreq=sfreq, ch_types=["eeg", "eeg"])
    raw = mne.io.RawArray(np.zeros((2, n_samples)), info)
    raw.set_annotations(
        mne.Annotations(
            [30.0, 120.0, 240.0, 360.0, 500.0],
            [0.0, 0.0, 0.0, 0.0, 0.0],
            [
                "Oczy zamknięte",
                "Oczy otwarte",
                "Oczy zamknięte",
                "Zadanie poznawcze",
                "Oczy otwarte",
            ],
        )
    )
    segments = detect_task_segments(raw)
    assert segments["OO"] == (120.0, 240.0)
    assert segments["OZ"] == (240.0, 360.0)
    assert segments["ZP"] == (360.0, 500.0)


def test_detect_task_segments_zp_ends_at_next_unrelated_marker() -> None:
    sfreq = 250.0
    duration = 900.0
    n_samples = int(duration * sfreq)
    info = mne.create_info(["C3", "O1"], sfreq=sfreq, ch_types=["eeg", "eeg"])
    raw = mne.io.RawArray(np.zeros((2, n_samples)), info)
    raw.set_annotations(
        mne.Annotations(
            [100.0, 280.0, 460.0, 620.0],
            [0.0, 0.0, 0.0, 0.0],
            [
                "Oczy otwarte",
                "Oczy zamknięte",
                "Zadanie poznawcze",
                "Czynność podstawowa",
            ],
        )
    )
    segments = detect_task_segments(raw)
    assert segments["ZP"] == (460.0, 620.0)


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


def test_run_step_delay_respects_cancel() -> None:
    config = load(resolve_norms_path())

    def cancel_after_start() -> bool:
        cancel_after_start.calls += 1
        return cancel_after_start.calls > 1

    cancel_after_start.calls = 0

    with patch("app.domain.pipeline._load_raw") as mock_load:
        mock_load.return_value = _synthetic_raw_with_annotations()
        with pytest.raises(AnalysisCancelledError):
            run(
                Path("synthetic.edf"),
                config,
                cancel_check=cancel_after_start,
                step_delay_s=5.0,
            )


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
