"""
Skrypt diagnostyczny: analizuje pliki EEG pacjentów krok po kroku.
Uruchom: python scripts/diagnose_patient_files.py

Sprawdza:
  1. Adnotacje w pliku i rozpoznane markery (vs _TASK_KEYWORDS)
  2. Segmenty: annotation-based vs fallback 3×3 min
  3. Amplitudy pre/post filtracji per komórka vs progi mean_z/mean_k
  4. Czy brama 200 µV p-p byłaby wyzwolona
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import mne
import numpy as np

# Dodaj root projektu do path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domain.pipeline import (
    _collect_task_markers,
    _segments_from_annotations,
    _fallback_segments,
    _TASK_KEYWORDS,
    _REJECT_EEG_VOLTS,
    normalize_channel_names,
    _REQUIRED_CHANNELS,
)
from app.domain.norms import load, resolve_norms_path
from app.domain.eeg_file import read_raw_digitrack

SEP = "=" * 70

FILES = [
    r"D:\CVGOSI\NF dane\Testowe\260116_000791_EEGok.edf",
    r"D:\CVGOSI\NF dane\Testowe\kobryń.EEG",
    r"D:\CVGOSI\NF dane\Testowe\Kuczyński.EEG",
]


def load_raw(path: Path) -> mne.io.BaseRaw:
    suffix = path.suffix.upper()
    if suffix == ".EDF":
        return mne.io.read_raw_edf(str(path), preload=True, verbose=False)
    if suffix == ".VHDR":
        return mne.io.read_raw_brainvision(str(path), preload=True, verbose=False)
    if suffix in (".EEG", ".BIN"):
        raw_dt = read_raw_digitrack(path)
        # DigiTrack zwraca RawArray — konwertuj do BaseRaw przez set_annotations
        return raw_dt
    raise ValueError(f"Nieznany format: {suffix}")


def print_section(title: str) -> None:
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}")


def diagnose_file(path_str: str, config: object) -> None:  # type: ignore[type-arg]
    path = Path(path_str)
    print(f"\n{SEP}")
    print(f"PLIK: {path.name}")
    print(f"Ścieżka: {path}")
    print(SEP)

    # --- 1. Wczytaj plik ---
    print_section("1. Wczytywanie pliku")
    try:
        raw = load_raw(path)
    except Exception as e:
        print(f"  BŁĄD wczytywania: {e}")
        traceback.print_exc()
        return

    duration_s = float(raw.times[-1])
    sfreq = raw.info["sfreq"]
    print(f"  Czas trwania: {duration_s:.1f} s ({duration_s/60:.1f} min)")
    print(f"  Częstotliwość próbkowania: {sfreq} Hz")
    print(f"  Kanały ({len(raw.ch_names)}): {raw.ch_names[:20]}")
    if len(raw.ch_names) > 20:
        print(f"    ... i {len(raw.ch_names) - 20} więcej")

    # --- 2. Adnotacje ---
    print_section("2. Adnotacje w pliku")
    anns = raw.annotations
    if anns is None or len(anns) == 0:
        print("  BRAK adnotacji")
    else:
        print(f"  Liczba adnotacji: {len(anns)}")
        for i, (desc, onset, dur) in enumerate(
            zip(anns.description, anns.onset, anns.duration)
        ):
            print(f"  [{i:3d}] onset={onset:8.2f}s  dur={dur:7.2f}s  '{desc}'")

    # --- 3. Normalizacja kanałów ---
    print_section("3. Normalizacja i dostępność kanałów C3/O1")
    try:
        normalize_channel_names(raw)
        available = set(raw.ch_names)
        required = set(_REQUIRED_CHANNELS)
        missing = required - available
        if missing:
            print(f"  BRAK wymaganych kanałów: {missing}")
            print(f"  Dostępne kanały: {sorted(available)}")
        else:
            print(f"  Kanały C3/O1 dostępne ✓")
    except Exception as e:
        print(f"  BŁĄD normalizacji: {e}")

    # --- 4. Detekcja markerów ---
    print_section("4. Detekcja markerów zadań")
    known_aliases: list[str] = []
    for aliases in _TASK_KEYWORDS.values():
        known_aliases.extend(aliases)
    print(f"  Znane aliasy ({len(known_aliases)}): {known_aliases}")

    try:
        markers = _collect_task_markers(raw)
        print(f"\n  Rozpoznane markery ({len(markers)}):")
        for m in markers:
            print(f"    {m}")
    except Exception as e:
        print(f"  BŁĄD zbierania markerów: {e}")
        markers = []

    # --- 5. Segmenty ---
    print_section("5. Ścieżka segmentacji")
    try:
        ann_segments = _segments_from_annotations(raw)
        if len(ann_segments) == 3:
            print(f"  Ścieżka: ADNOTACJE ✓")
            for task, (t0, t1) in ann_segments.items():
                print(f"    {task}: {t0:.1f}s – {t1:.1f}s  (długość {t1-t0:.1f}s)")
        else:
            print(f"  Adnotacje: niepełne segmenty ({len(ann_segments)}/3)")
            if not markers:
                try:
                    fb = _fallback_segments(raw)
                    print(f"  Ścieżka: FALLBACK 3×3 MIN ⚠️")
                    for task, (t0, t1) in fb.items():
                        print(f"    {task}: {t0:.1f}s – {t1:.1f}s  (długość {t1-t0:.1f}s)")
                    segments = fb
                except Exception as e:
                    print(f"  BŁĄD fallback: {e}")
                    return
            else:
                print(f"  Ścieżka: BŁĄD missing_task_segments (częściowe markery)")
                return
    except Exception as e:
        print(f"  BŁĄD segmentacji: {e}")
        return

    segments = ann_segments if len(ann_segments) == 3 else (
        _fallback_segments(raw) if not markers else None
    )
    if segments is None:
        return

    # --- 6. Amplitudy per komórka ---
    print_section("6. Amplitudy per komórka (pre/post filtr vs normy)")

    try:
        raw.pick(list(_REQUIRED_CHANNELS))
    except Exception as e:
        print(f"  BŁĄD pick kanałów: {e}")
        return

    band_ranges = config.band_ranges  # type: ignore[attr-defined]
    power_line_freq = config.power_line_frequency  # type: ignore[attr-defined]

    print(
        f"  {'id':>3}  {'ch':>3}  {'task':>3}  {'band':>6}  "
        f"{'t_start':>8}  {'t_end':>7}  "
        f"{'pre_µV':>8}  {'post_µV':>8}  "
        f"{'200µV?':>7}  {'mean_z':>7}  {'mean_k':>7}  {'COLOR':>7}"
    )
    print("  " + "-" * 100)

    for norm in config.norms:  # type: ignore[attr-defined]
        task_segs = segments.get(norm.task)
        if task_segs is None:
            print(f"  {norm.norm_id:>3}  brak segmentu dla zadania '{norm.task}'")
            continue

        t_start, t_end = task_segs
        band = band_ranges[norm.band]

        try:
            cropped = raw.copy().crop(tmin=t_start, tmax=t_end).pick([norm.channel])

            # Amplituda RAW (broadband)
            pre_amp = float(np.mean(np.abs(cropped.get_data(units="uV"))))

            # Notch
            cropped.notch_filter(freqs=power_line_freq, verbose=False)

            # Bandpass
            cropped.filter(l_freq=band.l_freq, h_freq=band.h_freq, verbose=False)

            # Post-filter amplitude
            post_amp = float(np.mean(np.abs(cropped.get_data(units="uV"))))

            # 200 µV gate
            seg_data = cropped.get_data()[np.newaxis, ...]
            epochs = mne.EpochsArray(seg_data, cropped.info, verbose=False)
            epochs.drop_bad(reject={"eeg": _REJECT_EEG_VOLTS}, verbose=False)
            gate_fired = len(epochs) == 0
            gate_str = "ODRZUC" if gate_fired else "ok"

            # RAG color
            epsilon = 1e-6
            if gate_fired:
                color = "ERROR"
            elif post_amp <= norm.mean_z + epsilon:
                color = "RED ██"
            elif post_amp >= norm.mean_k - epsilon:
                color = "GREEN"
            else:
                color = "YELLOW"

            print(
                f"  {norm.norm_id:>3}  {norm.channel:>3}  {norm.task:>3}  "
                f"{norm.band:>6}  {t_start:>8.1f}  {t_end:>7.1f}  "
                f"{pre_amp:>8.2f}  {post_amp:>8.2f}  "
                f"{gate_str:>7}  {norm.mean_z:>7.2f}  {norm.mean_k:>7.2f}  {color:>7}"
            )

        except Exception as e:
            print(
                f"  {norm.norm_id:>3}  {norm.channel:>3}  {norm.task:>3}  "
                f"{norm.band:>6}  BŁĄD: {e}"
            )


def main() -> None:
    print(f"\n{'#' * 70}")
    print("  NEUROFLAG — DIAGNOSTYKA PIPELINE EEG")
    print(f"{'#' * 70}")

    config = load(resolve_norms_path())
    print(f"\nNormy załadowane: {len(config.norms)} komórek, f_notch={config.power_line_frequency} Hz")

    for path_str in FILES:
        diagnose_file(path_str, config)

    print(f"\n{SEP}")
    print("Koniec diagnostyki.")


if __name__ == "__main__":
    main()
