from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from app.domain.amplitude import AmplitudeMethod, compute_band_amplitude
from app.domain.errors import PipelineError
from app.domain.types import BandRange, NormEntry, NormsConfig

if TYPE_CHECKING:
    import mne.io
    from numpy.typing import NDArray


@dataclass(frozen=True)
class SignalAmplitudeParams:
    amplitude_method: AmplitudeMethod
    reject_broadband_uv: float
    reject_filtered_uv: float
    epoch_seconds: float = 1.0
    min_clean_seconds: float = 30.0


LEGACY_PIPELINE_PARAMS = SignalAmplitudeParams(
    amplitude_method=AmplitudeMethod.MEAN_ABS,
    reject_broadband_uv=0.0,
    reject_filtered_uv=200.0,
    min_clean_seconds=0.0,
)


def _epoch_samples(sfreq: float, epoch_seconds: float) -> int:
    return max(1, int(sfreq * epoch_seconds))


def _extract_clean_samples(
    flat_uv: NDArray[np.floating],
    sfreq: float,
    *,
    reject_uv: float,
    epoch_seconds: float,
    allowed_epochs: tuple[bool, ...] | None = None,
) -> NDArray[np.floating] | None:
    """Zwraca próbki z okien spełniających próg p-p (0 = wyłączone)."""
    window = _epoch_samples(sfreq, epoch_seconds)
    n_samples = flat_uv.size
    if n_samples < window:
        if reject_uv > 0 and float(np.ptp(flat_uv)) > reject_uv:
            return None
        if allowed_epochs is not None and (not allowed_epochs or not allowed_epochs[0]):
            return None
        return flat_uv.copy()

    good: list[NDArray[np.floating]] = []
    epoch_index = 0
    for start in range(0, n_samples - window + 1, window):
        if allowed_epochs is not None:
            if epoch_index >= len(allowed_epochs) or not allowed_epochs[epoch_index]:
                epoch_index += 1
                continue
        chunk = flat_uv[start : start + window]
        if reject_uv <= 0 or float(np.ptp(chunk)) <= reject_uv:
            good.append(chunk)
        epoch_index += 1

    if not good:
        return None
    return np.asarray(np.concatenate(good), dtype=np.float64)


def _pass1_epoch_mask(
    flat_uv: NDArray[np.floating],
    sfreq: float,
    *,
    reject_uv: float,
    epoch_seconds: float,
) -> tuple[bool, ...]:
    """Maska okien Pass 1 na sygnale broadband (po notch, przed bandpass)."""
    window = _epoch_samples(sfreq, epoch_seconds)
    n_samples = flat_uv.size
    if reject_uv <= 0:
        if n_samples < window:
            return (True,)
        epoch_count = (n_samples - window) // window + 1
        return tuple(True for _ in range(epoch_count))

    if n_samples < window:
        return (float(np.ptp(flat_uv)) <= reject_uv,)

    mask: list[bool] = []
    for start in range(0, n_samples - window + 1, window):
        chunk = flat_uv[start : start + window]
        mask.append(float(np.ptp(chunk)) <= reject_uv)
    return tuple(mask)


def _filter_method(n_times: int) -> str:
    return "iir" if n_times < 4096 else "fir"


def compute_cell_amplitude(
    raw: mne.io.BaseRaw,
    norm: NormEntry,
    segments: dict[str, tuple[float, float]],
    config: NormsConfig,
    params: SignalAmplitudeParams,
) -> float:
    """Oblicza amplitudę komórki z 2-pass odrzucaniem artefaktów."""
    t_start, t_end = segments[norm.task]
    if t_end <= t_start:
        raise PipelineError(
            "invalid_segment",
            f"Nieprawidłowy segment zadania {norm.task}.",
        )

    band: BandRange = config.band_ranges[norm.band]
    cropped = raw.copy().crop(tmin=t_start, tmax=t_end).pick([norm.channel])
    filt_method = _filter_method(cropped.n_times)

    cropped.notch_filter(
        freqs=config.power_line_frequency,
        method=filt_method,
        verbose=False,
    )

    broadband_uv = cropped.get_data()[0] * 1e6
    sfreq = float(cropped.info["sfreq"])
    pass1_mask = _pass1_epoch_mask(
        broadband_uv,
        sfreq,
        reject_uv=params.reject_broadband_uv,
        epoch_seconds=params.epoch_seconds,
    )

    cropped.filter(
        l_freq=band.l_freq,
        h_freq=band.h_freq,
        method=filt_method,
        verbose=False,
    )
    if cropped.n_times < 1:
        raise PipelineError(
            "empty_segment",
            f"Pusty segment dla zadania {norm.task} i kanału {norm.channel}.",
        )

    filtered_uv = cropped.get_data()[0] * 1e6
    clean_uv = _extract_clean_samples(
        filtered_uv,
        sfreq,
        reject_uv=params.reject_filtered_uv,
        epoch_seconds=params.epoch_seconds,
        allowed_epochs=pass1_mask,
    )
    if clean_uv is None:
        raise PipelineError(
            "artifact_rejection",
            f"Segment zadania {norm.task} ({norm.channel}, {norm.band}) "
            "został odrzucony z powodu artefaktów.",
        )

    clean_seconds = clean_uv.size / sfreq
    if clean_seconds < params.min_clean_seconds:
        raise PipelineError(
            "artifact_rejection",
            f"Segment zadania {norm.task} ({norm.channel}, {norm.band}): "
            f"za mało czystych danych ({clean_seconds:.1f} s "
            f"< {params.min_clean_seconds:.1f} s).",
        )

    amplitude = compute_band_amplitude(
        clean_uv[np.newaxis, :],
        sfreq,
        params.amplitude_method,
        band=band,
    )
    if not np.isfinite(amplitude):
        raise PipelineError(
            "invalid_amplitude",
            f"Nie udało się obliczyć amplitudy dla komórki {norm.norm_id}.",
        )
    return amplitude
