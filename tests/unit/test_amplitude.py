from __future__ import annotations

import pytest

from app.domain.amplitude import (
    AmplitudeMethod,
    compute_band_amplitude,
    parse_amplitude_method,
)
import numpy as np


def test_parse_amplitude_method_defaults_to_mean_abs() -> None:
    assert parse_amplitude_method(None) is AmplitudeMethod.MEAN_ABS


def test_parse_amplitude_method_accepts_known_values() -> None:
    assert parse_amplitude_method("peak_to_peak_half") is AmplitudeMethod.PEAK_TO_PEAK_HALF


def test_parse_amplitude_method_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown amplitude_method"):
        parse_amplitude_method("excel_magic")


def test_compute_band_amplitude_mean_abs_sine() -> None:
    # sinus A*sin(wt): mean|x| ≈ 2A/π
    t = np.linspace(0, 1, 1000, endpoint=False)
    amp = 10.0
    data = (amp * np.sin(2 * np.pi * 6 * t))[np.newaxis, :]
    result = compute_band_amplitude(data, 1000.0, AmplitudeMethod.MEAN_ABS)
    assert result == pytest.approx(amp * 2 / np.pi, rel=0.02)


def test_compute_band_amplitude_peak_to_peak_half() -> None:
    t = np.linspace(0, 1, 1000, endpoint=False)
    amp = 10.0
    data = (amp * np.sin(2 * np.pi * 6 * t))[np.newaxis, :]
    result = compute_band_amplitude(data, 1000.0, AmplitudeMethod.PEAK_TO_PEAK_HALF)
    assert result == pytest.approx(amp, rel=0.02)


def test_compute_band_amplitude_epoch_mean_abs() -> None:
    sfreq = 100.0
    # 2 s: pierwsza sekunda niska, druga wysoka
    low = np.zeros(int(sfreq))
    high = np.full(int(sfreq), 20.0)
    data = np.concatenate([low, high])[np.newaxis, :]
    result = compute_band_amplitude(data, sfreq, AmplitudeMethod.EPOCH_MEAN_ABS)
    assert result == pytest.approx(10.0, rel=0.01)
