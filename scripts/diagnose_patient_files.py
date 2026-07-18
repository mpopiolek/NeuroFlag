"""
Skrypt diagnostyczny (tylko inżynierski): analizuje pliki EEG krok po kroku.

Uruchom: python scripts/diagnose_patient_files.py

UWAGA: Wypisuje surowe amplitudy µV na stdout — nie jest częścią aplikacji GUI.

Sprawdza:
  1. Adnotacje w pliku
  2. Segmenty przez publiczne detect_task_segments (adnotacje lub fallback 3×3 min)
  3. Amplitudy per komórka przez produkcyjną ścieżkę signal_amplitude (2-pass + metoda z NormsConfig)
  4. Klasyfikacja RAG względem progów mean_z/mean_k
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

# Dodaj root projektu do path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domain.channels import normalize_channel_names, require_channels
from app.domain.errors import PipelineError
from app.domain.norms import load, resolve_norms_path
from app.domain.pipeline import detect_task_segments, load_raw
from app.domain.signal_amplitude import compute_cell_amplitude, signal_params_from_config
from app.domain.types import NormsConfig

SEP = "=" * 70
_REQUIRED_CHANNELS = ("C3", "O1")

FILES = [
    r"D:\CVGOSI\NF dane\Testowe\260116_000791_EEGok.edf",
    r"D:\CVGOSI\NF dane\Testowe\kobryń.EEG",
    r"D:\CVGOSI\NF dane\Testowe\Kuczyński.EEG",
]


def print_section(title: str) -> None:
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}")


def _rag_label(amplitude: float, mean_z: float, mean_k: float) -> str:
    epsilon = 1e-6
    if amplitude <= mean_z + epsilon:
        return "RED ██"
    if amplitude >= mean_k - epsilon:
        return "GREEN"
    return "YELLOW"


def diagnose_file(path_str: str, config: NormsConfig) -> None:
    path = Path(path_str)
    params = signal_params_from_config(config)
    print(f"\n{SEP}")
    print(f"PLIK: {path.name}")
    print(f"Ścieżka: {path}")
    print(SEP)

    print_section("1. Wczytywanie pliku")
    try:
        raw = load_raw(path)
    except PipelineError as exc:
        print(f"  BŁĄD wczytywania [{exc.code}]: {exc.user_message_pl}")
        return
    except Exception as exc:
        print(f"  BŁĄD wczytywania: {exc}")
        traceback.print_exc()
        return

    duration_s = float(raw.times[-1])
    sfreq = raw.info["sfreq"]
    print(f"  Czas trwania: {duration_s:.1f} s ({duration_s / 60:.1f} min)")
    print(f"  Częstotliwość próbkowania: {sfreq} Hz")
    print(f"  Kanały ({len(raw.ch_names)}): {raw.ch_names[:20]}")
    if len(raw.ch_names) > 20:
        print(f"    ... i {len(raw.ch_names) - 20} więcej")

    print_section("2. Adnotacje w pliku")
    anns = raw.annotations
    if anns is None or len(anns) == 0:
        print("  BRAK adnotacji")
    else:
        print(f"  Liczba adnotacji: {len(anns)}")
        for i, (desc, onset, dur) in enumerate(
            zip(anns.description, anns.onset, anns.duration, strict=True)
        ):
            print(f"  [{i:3d}] onset={onset:8.2f}s  dur={dur:7.2f}s  '{desc}'")

    print_section("3. Normalizacja i dostępność kanałów C3/O1")
    try:
        normalize_channel_names(raw)
        require_channels(raw, _REQUIRED_CHANNELS)
        print("  Kanały C3/O1 dostępne ✓")
    except PipelineError as exc:
        print(f"  BŁĄD [{exc.code}]: {exc.user_message_pl}")
        return
    except Exception as exc:
        print(f"  BŁĄD normalizacji: {exc}")
        return

    print_section("4. Segmenty zadań (detect_task_segments)")
    try:
        segments = detect_task_segments(raw)
        for task, (t0, t1) in segments.items():
            print(f"    {task}: {t0:.1f}s – {t1:.1f}s  (długość {t1 - t0:.1f}s)")
    except PipelineError as exc:
        print(f"  BŁĄD segmentacji [{exc.code}]: {exc.user_message_pl}")
        return

    print_section("5. Amplitudy per komórka (produkcyjna ścieżka signal_amplitude)")
    print(
        f"  Metoda: {params.amplitude_method.value}, "
        f"bb={params.reject_broadband_uv} µV, "
        f"rf={params.reject_filtered_uv} µV, "
        f"min_clean={params.min_clean_seconds} s"
    )
    print(
        f"  {'id':>3}  {'ch':>3}  {'task':>3}  {'band':>6}  "
        f"{'t_start':>8}  {'t_end':>7}  "
        f"{'amp_µV':>8}  {'status':>12}  "
        f"{'mean_z':>7}  {'mean_k':>7}  {'COLOR':>7}"
    )
    print("  " + "-" * 100)

    raw.pick(list(_REQUIRED_CHANNELS))

    for norm in config.norms:
        task_segs = segments.get(norm.task)
        if task_segs is None:
            print(f"  {norm.norm_id:>3}  brak segmentu dla zadania '{norm.task}'")
            continue

        t_start, t_end = task_segs
        try:
            amplitude = compute_cell_amplitude(
                raw,
                norm,
                segments,
                config,
                params,
            )
            color = _rag_label(amplitude, norm.mean_z, norm.mean_k)
            print(
                f"  {norm.norm_id:>3}  {norm.channel:>3}  {norm.task:>3}  "
                f"{norm.band:>6}  {t_start:>8.1f}  {t_end:>7.1f}  "
                f"{amplitude:>8.2f}  {'ok':>12}  "
                f"{norm.mean_z:>7.2f}  {norm.mean_k:>7.2f}  {color:>7}"
            )
        except PipelineError as exc:
            print(
                f"  {norm.norm_id:>3}  {norm.channel:>3}  {norm.task:>3}  "
                f"{norm.band:>6}  {t_start:>8.1f}  {t_end:>7.1f}  "
                f"{'—':>8}  {exc.code:>12}  "
                f"{norm.mean_z:>7.2f}  {norm.mean_k:>7.2f}  {'ERROR':>7}"
            )
        except Exception as exc:
            print(
                f"  {norm.norm_id:>3}  {norm.channel:>3}  {norm.task:>3}  "
                f"{norm.band:>6}  BŁĄD: {exc}"
            )


def main() -> None:
    print(f"\n{'#' * 70}")
    print("  NEUROFLAG — DIAGNOSTYKA PIPELINE EEG (inżynierska, stdout µV)")
    print(f"{'#' * 70}")

    config = load(resolve_norms_path())
    print(
        f"\nNormy załadowane: {len(config.norms)} komórek, "
        f"f_notch={config.power_line_frequency} Hz, "
        f"metoda={config.amplitude_method.value}"
    )

    for path_str in FILES:
        diagnose_file(path_str, config)

    print(f"\n{SEP}")
    print("Koniec diagnostyki.")


if __name__ == "__main__":
    main()
