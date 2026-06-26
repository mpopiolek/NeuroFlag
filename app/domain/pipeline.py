from __future__ import annotations

import re
import time
import unicodedata
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import numpy as np

from app.domain.channels import (
    apply_channel_overrides,
    normalize_channel_names,
    require_channels,
)
from app.domain.eeg_file import validate_extension
from app.domain.errors import AnalysisCancelledError, PipelineError
from app.domain.types import NormEntry, NormsConfig

if TYPE_CHECKING:
    import mne.io

_REQUIRED_CHANNELS = ("C3", "O1")
_TASK_ORDER = ("OO", "OZ", "ZP")
_MIN_RECORDING_SECONDS = 480.0  # 8 min — minimum do analizy przesiewowej
_MIN_RECORDING_TOLERANCE_S = 1.0  # tolerancja próbkowania (np. 479.996 s ≈ 8 min)
_DEFAULT_SEGMENT_SECONDS = 180.0  # domyślna długość segmentu bez kolejnego znacznika
_REJECT_EEG_VOLTS = 200e-6  # 200 µV peak-to-peak (dane MNE w V)

_TASK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "OO": (
        "OCZY OTWARTE",
        "OCZY OTW",
        "EYES OPEN",
        "EYESOPEN",
        "OPEN EYES",
        "OO",
    ),
    "OZ": (
        "OCZY ZAMKNIETE",
        "OCZY ZAMK",
        "EYES CLOSED",
        "EYESCLOSED",
        "CLOSED EYES",
        "OZ",
    ),
    "ZP": (
        "MATEMATYKA POZNAWCZA",
        "ZADANIE POZNAWCZE",
        "ZADANIE PAMIECIOWE",
        "ZADANIE PAMIĘCIOWE",
        "OBLICZENIA",
        "MEMORY TASK",
        "MATEMATYKA",
        "MAT.",
        "MEMORY",
        "ZP",
    ),
}
_MIN_ANNOTATION_DURATION_S = 1.0


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


def _wait_or_cancel(
    seconds: float,
    cancel_check: Callable[[], bool],
) -> None:
    if seconds <= 0:
        return
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        _check_cancel(cancel_check)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(0.1, remaining))


def _fold_annotation_text(desc: str) -> str:
    text = unicodedata.normalize("NFKD", desc.strip())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.upper()
    text = re.sub(r"^\d{1,2}:\d{2}:\d{2}\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _match_task(description: str) -> str | None:
    norm = _fold_annotation_text(description)
    if not norm:
        return None
    best_len = -1
    best_task: str | None = None
    for task, keywords in _TASK_KEYWORDS.items():
        for keyword in keywords:
            folded_kw = _fold_annotation_text(keyword)
            if len(folded_kw) <= 3:
                matched = re.search(rf"\b{re.escape(folded_kw)}\b", norm) is not None
            else:
                matched = folded_kw in norm
            if matched and len(folded_kw) > best_len:
                best_len = len(folded_kw)
                best_task = task
    return best_task


def _annotation_segment_end(
    onset: float,
    duration: float,
    next_onset: float | None,
    recording_end: float,
) -> float:
    if duration >= _MIN_ANNOTATION_DURATION_S:
        return min(onset + duration, recording_end)
    if next_onset is not None and next_onset > onset + _MIN_ANNOTATION_DURATION_S:
        return next_onset
    return min(onset + _DEFAULT_SEGMENT_SECONDS, recording_end)


def _collect_task_markers(
    raw: mne.io.BaseRaw,
) -> list[tuple[str, float, float]]:
    annotations = raw.annotations
    if annotations is None or len(annotations) == 0:
        return []
    markers: list[tuple[str, float, float]] = []
    for desc, onset, duration in zip(
        annotations.description,
        annotations.onset,
        annotations.duration,
        strict=True,
    ):
        task = _match_task(str(desc))
        if task is None:
            continue
        markers.append((task, float(onset), float(duration)))
    markers.sort(key=lambda item: item[1])
    return markers


def _next_annotation_onset_after(raw: mne.io.BaseRaw, after: float) -> float | None:
    annotations = raw.annotations
    if annotations is None or len(annotations) == 0:
        return None
    candidates = [
        float(onset)
        for onset in annotations.onset
        if float(onset) > after + _MIN_ANNOTATION_DURATION_S
    ]
    if not candidates:
        return None
    return min(candidates)


def _segments_from_annotations(raw: mne.io.BaseRaw) -> dict[str, tuple[float, float]]:
    markers = _collect_task_markers(raw)
    if not markers:
        return {}

    selected: list[tuple[str, float, float]] = []
    for task, onset, duration in markers:
        if len(selected) >= len(_TASK_ORDER):
            break
        expected = _TASK_ORDER[len(selected)]
        if task != expected:
            continue
        selected.append((task, onset, duration))

    if len(selected) < len(_TASK_ORDER):
        return {}

    recording_end = float(raw.times[-1])
    segments: dict[str, tuple[float, float]] = {}
    for index, (task, onset, duration) in enumerate(selected):
        if index + 1 < len(selected):
            next_onset: float | None = selected[index + 1][1]
        else:
            next_onset = _next_annotation_onset_after(raw, onset)
        end = _annotation_segment_end(onset, duration, next_onset, recording_end)
        if end <= onset:
            return {}
        segments[task] = (onset, end)
    return segments


def _require_recording_duration(raw: mne.io.BaseRaw) -> None:
    total = float(raw.times[-1])
    if total < _MIN_RECORDING_SECONDS - _MIN_RECORDING_TOLERANCE_S:
        minutes = total / 60.0
        raise PipelineError(
            "insufficient_duration",
            f"Nagranie jest za krótkie ({minutes:.0f} min). "
            "Wymagane co najmniej 8 minut nagrania.",
        )


def _fallback_segments(raw: mne.io.BaseRaw) -> dict[str, tuple[float, float]]:
    """Trzy kolejne okna 3 min od początku nagrania — gdy brak znaczników zadań."""
    total = float(raw.times[-1])
    if total <= 360.0:
        raise PipelineError(
            "insufficient_duration",
            f"Nagranie jest za krótkie ({total / 60.0:.0f} min). "
            "Wymagane co najmniej 8 minut nagrania.",
        )
    return {
        "OO": (0.0, min(_DEFAULT_SEGMENT_SECONDS, total)),
        "OZ": (
            _DEFAULT_SEGMENT_SECONDS,
            min(2 * _DEFAULT_SEGMENT_SECONDS, total),
        ),
        "ZP": (
            2 * _DEFAULT_SEGMENT_SECONDS,
            min(3 * _DEFAULT_SEGMENT_SECONDS, total),
        ),
    }


def detect_task_segments(raw: mne.io.BaseRaw) -> dict[str, tuple[float, float]]:
    """Wykrywa segmenty OO, OZ, ZP z adnotacji lub fallbacku 3×3 min."""
    _require_recording_duration(raw)
    segments = _segments_from_annotations(raw)
    if len(segments) == len(_TASK_ORDER):
        return {k: segments[k] for k in _TASK_ORDER}
    if not _collect_task_markers(raw):
        return _fallback_segments(raw)
    raise PipelineError(
        "missing_task_segments",
        "Nie wykryto trzech znaczników zadań (OO, OZ, ZP) w poprawnej kolejności. "
        "Bez nich nie można wykonać analizy przesiewowej.",
    )


def _load_raw(path: Path) -> mne.io.BaseRaw:
    from app.domain.eeg_file import EEGFileError

    try:
        validate_extension(path)
    except EEGFileError as exc:
        raise PipelineError("unsupported_format", str(exc)) from exc
    mne = _load_mne()
    suffix = path.suffix.lower()
    try:
        if suffix == ".edf":
            return mne.io.read_raw_edf(path, preload=True, verbose=False)
        if suffix == ".vhdr":
            return mne.io.read_raw_brainvision(path, preload=True, verbose=False)
    except (OSError, Exception) as exc:
        raise PipelineError(
            "file_unreadable",
            "Nie mo\u017cna odczyta\u0107 pliku EEG \u2014 "
            "sprawd\u017a czy plik istnieje i nie jest uszkodzony.",
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
    channel_overrides: dict[str, str] | None = None,
    step_delay_s: float = 0.0,
    anonymize_header: bool = False,
) -> tuple[float, ...]:
    """Ładuje plik EEG i zwraca 10 amplitud (µV) w kolejności config.norms."""
    _check_cancel(cancel_check)
    _wait_or_cancel(step_delay_s, cancel_check)
    raw = _load_raw(path)
    if anonymize_header:
        try:
            raw.anonymize(daysback=None, keep_his=False)
        except Exception as exc:
            raise PipelineError(
                "anonymize_failed",
                "Nie udało się wyczyścić nagłówka pliku EEG.",
            ) from exc
    _check_cancel(cancel_check)
    _wait_or_cancel(step_delay_s, cancel_check)
    normalize_channel_names(raw)
    if channel_overrides:
        apply_channel_overrides(raw, channel_overrides)
    require_channels(raw, _REQUIRED_CHANNELS)
    raw.pick(list(_REQUIRED_CHANNELS))
    _check_cancel(cancel_check)
    _wait_or_cancel(step_delay_s, cancel_check)
    segments = detect_task_segments(raw)
    amplitudes: list[float] = []
    for norm in config.norms:
        _check_cancel(cancel_check)
        _wait_or_cancel(step_delay_s, cancel_check)
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
