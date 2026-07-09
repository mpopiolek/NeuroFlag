from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

import numpy as np
from scipy import signal as sp_signal

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from app.domain.types import BandRange


class AmplitudeMethod(StrEnum):
    """Metoda redukcji sygnału pasmowego do jednej amplitudy [µV] per komórka.

    Domyślnie ``mean_abs`` (zgodnie z PRD). Pozostałe wartości są eksperymentalne —
    do weryfikacji z metodą eksperta (np. arkusz kalkulacyjny) przez ``amplitude_method``
    w ``norms.json``.
    """

    MEAN_ABS = "mean_abs"
    RMS = "rms"
    PEAK_TO_PEAK_HALF = "peak_to_peak_half"
    PERCENTILE_95 = "percentile_95"
    EPOCH_MEAN_ABS = "epoch_mean_abs"
    WELCH_BAND_POWER = "welch_band_power"


_VALID_METHODS = frozenset(m.value for m in AmplitudeMethod)


def parse_amplitude_method(value: object) -> AmplitudeMethod:
    if value is None:
        return AmplitudeMethod.MEAN_ABS
    if not isinstance(value, str):
        raise ValueError(f"amplitude_method must be a string, got {value!r}")
    normalized = value.strip().lower()
    if normalized not in _VALID_METHODS:
        allowed = ", ".join(sorted(_VALID_METHODS))
        raise ValueError(
            f"Unknown amplitude_method {value!r}. Allowed: {allowed}"
        )
    return AmplitudeMethod(normalized)


def compute_band_amplitude(
    data_uv: NDArray[np.floating],
    sfreq: float,
    method: AmplitudeMethod,
    *,
    band: BandRange | None = None,
) -> float:
    """Oblicza amplitudę [µV] z macierzy (n_channels, n_samples) po filtracji pasma."""
    if data_uv.size == 0:
        return float("nan")
    flat = data_uv.reshape(-1)
    if method is AmplitudeMethod.MEAN_ABS:
        return float(np.mean(np.abs(flat)))
    if method is AmplitudeMethod.RMS:
        return float(np.sqrt(np.mean(flat**2)))
    if method is AmplitudeMethod.PEAK_TO_PEAK_HALF:
        return float(np.ptp(flat) / 2.0)
    if method is AmplitudeMethod.PERCENTILE_95:
        return float(np.percentile(np.abs(flat), 95))
    if method is AmplitudeMethod.EPOCH_MEAN_ABS:
        return _epoch_mean_abs(data_uv, sfreq)
    if method is AmplitudeMethod.WELCH_BAND_POWER:
        if band is None:
            raise ValueError("band is required for welch_band_power")
        return _welch_band_power(flat, sfreq, band)
    raise ValueError(f"Unsupported amplitude method: {method}")


def _welch_band_power(
    flat_uv: NDArray[np.floating],
    sfreq: float,
    band: BandRange,
) -> float:
    """Amplituda = sqrt(2 × całka PSD w paśmie) w µV (PSD jednostronna)."""
    n_samples = flat_uv.size
    if n_samples < 2:
        return float("nan")
    nperseg = min(n_samples, max(int(sfreq), int(sfreq * 2)))
    nperseg = max(nperseg, 2)
    freqs, psd = sp_signal.welch(flat_uv, fs=sfreq, nperseg=nperseg)
    mask = (freqs >= band.l_freq) & (freqs <= band.h_freq)
    if not np.any(mask):
        return float("nan")
    band_power = float(np.trapezoid(psd[mask], freqs[mask]))
    return float(np.sqrt(2.0 * band_power))


def _epoch_mean_abs(data_uv: NDArray[np.floating], sfreq: float) -> float:
    """Średnia z okien 1 s — bliżej ręcznego liczenia w Excelu po wierszach próbek."""
    window = max(1, int(sfreq))
    n_samples = data_uv.shape[-1]
    if n_samples < window:
        return float(np.mean(np.abs(data_uv)))
    epoch_means: list[float] = []
    for start in range(0, n_samples - window + 1, window):
        chunk = data_uv[..., start : start + window]
        epoch_means.append(float(np.mean(np.abs(chunk))))
    return float(np.mean(epoch_means))
