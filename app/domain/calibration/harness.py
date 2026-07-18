from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from app.domain.channels import normalize_channel_names, require_channels
from app.domain.errors import PipelineError
from app.domain.pipeline import detect_task_segments, load_raw
from app.domain.signal_amplitude import (
    SignalAmplitudeParams,
    compute_cell_amplitude,
)
from app.domain.types import NormsConfig

if TYPE_CHECKING:
    pass

_REQUIRED_CHANNELS = ("C3", "O1")


def compute_amplitudes(
    path: Path,
    config: NormsConfig,
    params: SignalAmplitudeParams,
) -> tuple[float, ...]:
    """Harness offline: segmentacja + 2-pass amplitudy per norma."""
    raw = load_raw(path)
    normalize_channel_names(raw)
    require_channels(raw, _REQUIRED_CHANNELS)
    raw.pick(list(_REQUIRED_CHANNELS))
    segments = detect_task_segments(raw)

    amplitudes: list[float] = []
    for norm in config.norms:
        value = compute_cell_amplitude(raw, norm, segments, config, params)
        amplitudes.append(value)

    if len(amplitudes) != len(config.norms):
        raise PipelineError(
            "amplitude_count",
            f"Oczekiwano {len(config.norms)} amplitud, otrzymano {len(amplitudes)}.",
        )
    return tuple(amplitudes)
