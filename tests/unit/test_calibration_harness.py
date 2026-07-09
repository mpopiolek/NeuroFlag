from __future__ import annotations

import numpy as np
import pytest

from app.domain.amplitude import AmplitudeMethod
from app.domain.errors import PipelineError
from app.domain.signal_amplitude import (
    LEGACY_PIPELINE_PARAMS,
    SignalAmplitudeParams,
    _extract_clean_samples,
    _pass1_epoch_mask,
    compute_cell_amplitude,
)
from app.domain.types import BandRange, NormEntry, NormsConfig


def _synthetic_config() -> NormsConfig:
    from app.domain.types import (
        CategoryDescriptions,
        ObservationCategory,
        ObservationChecklist,
        RecommendationRules,
    )

    band_ranges = {
        "Theta": BandRange(l_freq=4.0, h_freq=8.0),
        "Beta1": BandRange(l_freq=15.0, h_freq=18.0),
        "Beta2": BandRange(l_freq=18.0, h_freq=25.0),
        "Delta": BandRange(l_freq=0.5, h_freq=4.0),
    }
    norms = tuple(
        NormEntry(i + 1, "C3", "OO", "Theta", 10.0, 20.0) for i in range(10)
    )
    return NormsConfig(
        version=1,
        power_line_frequency=50.0,
        band_ranges=band_ranges,
        norms=norms,
        recommendation_rules=RecommendationRules(5, 3, 4, 3),
        category_descriptions=CategoryDescriptions("w", "o", "b"),
        observation_checklist=ObservationChecklist(
            "t",
            "i",
            (ObservationCategory("c", ("x",)),),
        ),
    )


def _make_raw_sine(
    *,
    sfreq: float = 256.0,
    duration_s: float = 20.0,
    amplitude_uv: float = 10.0,
    freq_hz: float = 6.0,
    spike_at_s: float | None = None,
    spike_uv: float = 500.0,
) -> object:
    import mne

    n_samples = int(sfreq * duration_s)
    t = np.arange(n_samples) / sfreq
    signal_v = (amplitude_uv * 1e-6) * np.sin(2 * np.pi * freq_hz * t)
    if spike_at_s is not None:
        idx = int(spike_at_s * sfreq)
        if 0 <= idx < n_samples:
            signal_v[idx] = spike_uv * 1e-6
    data = np.stack([signal_v, signal_v * 0.5])
    info = mne.create_info(["C3", "O1"], sfreq, ch_types=["eeg", "eeg"])
    raw = mne.io.RawArray(data, info, verbose=False)
    raw.set_montage("standard_1020", on_missing="ignore")
    return raw


def test_pass1_mask_rejects_spike_window() -> None:
    sfreq = 100.0
    flat = np.zeros(300)
    flat[150] = 500.0
    mask = _pass1_epoch_mask(flat, sfreq, reject_uv=200.0, epoch_seconds=1.0)
    assert mask == (True, False, True)


def test_extract_clean_samples_pass1_then_pass2() -> None:
    sfreq = 100.0
    flat = np.zeros(300)
    flat[150] = 500.0
    pass1 = _pass1_epoch_mask(flat, sfreq, reject_uv=200.0, epoch_seconds=1.0)
    clean = _extract_clean_samples(
        flat,
        sfreq,
        reject_uv=200.0,
        epoch_seconds=1.0,
        allowed_epochs=pass1,
    )
    assert clean is not None
    assert clean.size == 200


def test_welch_greater_than_mean_abs_on_synthetic_raw() -> None:
    raw = _make_raw_sine(amplitude_uv=15.0, duration_s=30.0)
    config = _synthetic_config()
    segments = {"OO": (0.0, 20.0), "OZ": (0.0, 20.0), "ZP": (0.0, 20.0)}
    norm = config.norms[0]

    mean_params = SignalAmplitudeParams(
        amplitude_method=AmplitudeMethod.MEAN_ABS,
        reject_broadband_uv=0.0,
        reject_filtered_uv=1000.0,
        min_clean_seconds=0.0,
    )
    welch_params = SignalAmplitudeParams(
        amplitude_method=AmplitudeMethod.WELCH_BAND_POWER,
        reject_broadband_uv=0.0,
        reject_filtered_uv=1000.0,
        min_clean_seconds=0.0,
    )

    mean_amp = compute_cell_amplitude(raw, norm, segments, config, mean_params)
    welch_amp = compute_cell_amplitude(raw, norm, segments, config, welch_params)
    assert welch_amp > mean_amp


def test_pass1_broadband_removes_spike_before_amplitude() -> None:
    raw = _make_raw_sine(
        amplitude_uv=10.0,
        duration_s=30.0,
        spike_at_s=5.0,
        spike_uv=800.0,
    )
    config = _synthetic_config()
    segments = {"OO": (0.0, 20.0), "OZ": (0.0, 20.0), "ZP": (0.0, 20.0)}
    norm = config.norms[0]

    no_pass1 = SignalAmplitudeParams(
        amplitude_method=AmplitudeMethod.MEAN_ABS,
        reject_broadband_uv=0.0,
        reject_filtered_uv=1000.0,
        min_clean_seconds=0.0,
    )
    with_pass1 = SignalAmplitudeParams(
        amplitude_method=AmplitudeMethod.MEAN_ABS,
        reject_broadband_uv=200.0,
        reject_filtered_uv=1000.0,
        min_clean_seconds=0.0,
    )

    amp_no_pass1 = compute_cell_amplitude(raw, norm, segments, config, no_pass1)
    amp_with_pass1 = compute_cell_amplitude(raw, norm, segments, config, with_pass1)
    assert amp_with_pass1 < amp_no_pass1


def test_min_clean_seconds_rejects_short_segment() -> None:
    raw = _make_raw_sine(duration_s=10.0)
    config = _synthetic_config()
    segments = {"OO": (0.0, 9.9), "OZ": (0.0, 9.9), "ZP": (0.0, 9.9)}
    norm = config.norms[0]
    params = SignalAmplitudeParams(
        amplitude_method=AmplitudeMethod.MEAN_ABS,
        reject_broadband_uv=0.0,
        reject_filtered_uv=1000.0,
        min_clean_seconds=30.0,
    )
    with pytest.raises(PipelineError, match="za mało czystych"):
        compute_cell_amplitude(raw, norm, segments, config, params)


def test_legacy_pipeline_params_defaults() -> None:
    assert LEGACY_PIPELINE_PARAMS.amplitude_method is AmplitudeMethod.MEAN_ABS
    assert LEGACY_PIPELINE_PARAMS.reject_broadband_uv == 0.0
    assert LEGACY_PIPELINE_PARAMS.reject_filtered_uv == 200.0
    assert LEGACY_PIPELINE_PARAMS.min_clean_seconds == 0.0
