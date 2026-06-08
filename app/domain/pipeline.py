from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import numpy as np

from app.domain.channels import normalize_channel_names, require_channels
from app.domain.eeg_file import validate_extension
from app.domain.errors import AnalysisCancelledError, PipelineError
from app.domain.types import NormEntry, NormsConfig

if TYPE_CHECKING:
    import mne.io

_REQUIRED_CHANNELS = ("C3", "O1")
_FALLBACK_SEGMENT_SECONDS = 180.0
_REJECT_EEG_VOLTS = 200e-6  # 200 µV peak-to-peak (dane MNE w V)

_TASK_ALIASES: dict[str, frozenset[str]] = {
    "OO": frozenset(
        {
            "OO",
            "EYES OPEN",
            "EYESOPEN",
            "OPEN EYES",
            "OCZY OTWARTE",
            "OCZY OTW.",
        }
    ),
    "OZ": frozenset(
        {
            "OZ",
            "EYES CLOSED",
            "EYESCLOSED",
            "CLOSED EYES",
            "OCZY ZAMKNIETE",
            "OCZY ZAMK.",
        }
    ),
    "ZP": frozenset(
        {
            "ZP",
            "MEMORY",
            "MEMORY TASK",
            "ZADANIE PAMIECIOWE",
            "ZADANIE PAMIĘCIOWE",
        }
    ),
}


def _load_mne() -> ModuleType:
    try:
        import mne
    except ImportError as exc:
        raise PipelineError(
            "mne_missing",
            "Brak biblioteki MNE-Python. Zainstaluj zależności projektu.",
        ) from exc
    return mne  # type: ignore[no-any-return]


def _check_cancel(cancel_check: Callable[[], bool]) -> None:
    if cancel_check():
        raise AnalysisCancelledError()


def _normalize_annotation(desc: str) -> str:
    text = desc.strip().upper()
    text = re.sub(r"\s+", " ", text)
    return text


def _match_task(description: str) -> str | None:
    norm = _normalize_annotation(description)
    for task, aliases in _TASK_ALIASES.items():
        if norm in aliases:
            return task
    return None


def _segments_from_annotations(raw: mne.io.BaseRaw) -> dict[str, tuple[float, float]]:
    segments: dict[str, tuple[float, float]] = {}
    annotations = raw.annotations
    if annotations is None or len(annotations) == 0:
        return segments
    for desc, onset, duration in zip(
        annotations.description,
        annotations.onset,
        annotations.duration,
        strict=True,
    ):
        task = _match_task(str(desc))
        if task is None or task in segments:
            continue
        end = float(onset) + float(duration)
        segments[task] = (float(onset), end)
    return segments


def _fallback_segments(raw: mne.io.BaseRaw) -> dict[str, tuple[float, float]]:
    total = float(raw.times[-1])
    needed = 3 * _FALLBACK_SEGMENT_SECONDS
    if total < needed:
        raise PipelineError(
            "insufficient_duration",
            f"Nagranie jest za krótkie ({total:.0f} s). "
            f"Wymagane co najmniej {needed:.0f} s lub znaczniki OO/OZ/ZP.",
        )
    return {
        "OO": (0.0, _FALLBACK_SEGMENT_SECONDS),
        "OZ": (_FALLBACK_SEGMENT_SECONDS, 2 * _FALLBACK_SEGMENT_SECONDS),
        "ZP": (2 * _FALLBACK_SEGMENT_SECONDS, 3 * _FALLBACK_SEGMENT_SECONDS),
    }


def detect_task_segments(raw: mne.io.BaseRaw) -> dict[str, tuple[float, float]]:
    """Wykrywa segmenty OO, OZ, ZP z adnotacji lub trzech okien 180 s."""
    segments = _segments_from_annotations(raw)
    if len(segments) < 3:
        segments = _fallback_segments(raw)
    missing = [t for t in ("OO", "OZ", "ZP") if t not in segments]
    if missing:
        raise PipelineError(
            "missing_task_segments",
            f"Nie wykryto segmentów zadań: {', '.join(missing)}. "
            "Sprawdź znaczniki OO, OZ, ZP w pliku.",
        )
    return {k: segments[k] for k in ("OO", "OZ", "ZP")}


def _load_raw(path: Path) -> mne.io.BaseRaw:
    validate_extension(path)
    mne = _load_mne()
    suffix = path.suffix.lower()
    try:
        if suffix == ".edf":
            return mne.io.read_raw_edf(path, preload=True, verbose=False)
        if suffix == ".vhdr":
            return mne.io.read_raw_brainvision(path, preload=True, verbose=False)
    except OSError as exc:
        raise PipelineError(
            "file_unreadable",
            f"Nie można odczytać pliku EEG: {exc}",
        ) from exc
    except Exception as exc:
        raise PipelineError(
            "file_unreadable",
            f"Nie można odczytać pliku EEG: {exc}",
        ) from exc
    raise PipelineError(
        "unsupported_format",
        f"Nieobsługiwany format pliku: {suffix}",
    )


def _amplitude_for_norm(
    raw: mne.io.BaseRaw,
    norm: NormEntry,
    segments: dict[str, tuple[float, float]],
    config: NormsConfig,
) -> float:
    mne = _load_mne()
    t_start, t_end = segments[norm.task]
    if t_end <= t_start:
        raise PipelineError(
            "invalid_segment",
            f"Nieprawidłowy segment zadania {norm.task}.",
        )
    band = config.band_ranges[norm.band]
    cropped = raw.copy().crop(tmin=t_start, tmax=t_end).pick([norm.channel])
    cropped.notch_filter(
        freqs=config.power_line_frequency,
        verbose=False,
    )
    cropped.filter(
        l_freq=band.l_freq,
        h_freq=band.h_freq,
        verbose=False,
    )
    if cropped.n_times < 1:
        raise PipelineError(
            "empty_segment",
            f"Pusty segment dla zadania {norm.task} i kanału {norm.channel}.",
        )
    segment_data = cropped.get_data()[np.newaxis, ...]
    epochs = mne.EpochsArray(segment_data, cropped.info, verbose=False)
    epochs.drop_bad(reject={"eeg": _REJECT_EEG_VOLTS}, verbose=False)
    if len(epochs) == 0:
        raise PipelineError(
            "artifact_rejection",
            f"Segment zadania {norm.task} ({norm.channel}, {norm.band}) "
            "został odrzucony z powodu artefaktów.",
        )
    data_uv = epochs.get_data(units="uV")
    return float(np.mean(np.abs(data_uv)))


def run(
    path: Path,
    config: NormsConfig,
    *,
    cancel_check: Callable[[], bool] = lambda: False,
) -> tuple[float, ...]:
    """Ładuje plik EEG i zwraca 10 amplitud (µV) w kolejności config.norms."""
    _check_cancel(cancel_check)
    raw = _load_raw(path)
    _check_cancel(cancel_check)
    normalize_channel_names(raw)
    require_channels(raw, _REQUIRED_CHANNELS)
    raw.pick(list(_REQUIRED_CHANNELS))
    _check_cancel(cancel_check)
    segments = detect_task_segments(raw)
    amplitudes: list[float] = []
    for norm in config.norms:
        _check_cancel(cancel_check)
        value = _amplitude_for_norm(raw, norm, segments, config)
        if not np.isfinite(value):
            raise PipelineError(
                "invalid_amplitude",
                f"Nie udało się obliczyć amplitudy dla komórki {norm.norm_id}.",
            )
        amplitudes.append(value)
    if len(amplitudes) != len(config.norms):
        raise PipelineError(
            "amplitude_count",
            f"Oczekiwano {len(config.norms)} amplitud, otrzymano {len(amplitudes)}.",
        )
    return tuple(amplitudes)
