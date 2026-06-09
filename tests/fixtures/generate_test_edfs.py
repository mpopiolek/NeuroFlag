"""Generuje syntetyczne pliki .edf do testowania manualnego.

Uruchomienie:
    python tests/fixtures/generate_test_edfs.py

Wygenerowane pliki (w katalogu tests/fixtures/):
    test_standard.edf       -- C3, O1, EOG; adnotacje OO/OZ/ZP (9 min)
    test_bad_channels.edf   -- EEG 4, EEG 7; adnotacje OO/OZ/ZP (9 min)
    test_no_annotations.edf -- C3, O1; brak adnotacji (10 min, fallback 3x180s)

Pliki są gitignore'owane (.edf w .gitignore); regeneruj gdy potrzebne.
"""

from __future__ import annotations

import sys
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent

_SFREQ = 256.0
_DURATION_S = 600.0  # 10 min — wystarczy na 3×180 s fallback + margines
_AMP_UV = 20.0  # amplituda sygnału alfa (µV)


def _make_raw(
    ch_names: list[str],
    sfreq: float = _SFREQ,
    duration: float = _DURATION_S,
) -> "mne.io.RawArray":
    import mne
    import numpy as np

    n_samples = int(sfreq * duration)
    n_ch = len(ch_names)

    t = np.linspace(0, duration, n_samples, endpoint=False)
    # Sygnał alfa 10 Hz w µV, konwersja do V (MNE przechowuje dane w V)
    data = (_AMP_UV * np.sin(2 * np.pi * 10 * t)) * 1e-6
    raw_data = np.tile(data, (n_ch, 1))

    ch_types = ["eeg"] * n_ch
    info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)
    return mne.io.RawArray(raw_data, info, verbose=False)


def _add_task_annotations(raw: "mne.io.RawArray") -> None:
    import mne

    # OO: 60–240 s, OZ: 260–440 s, ZP: 460–540 s
    onsets = [60.0, 260.0, 460.0]
    durations = [180.0, 180.0, 80.0]
    descriptions = ["OO", "OZ", "ZP"]
    annotations = mne.Annotations(
        onset=onsets,
        duration=durations,
        description=descriptions,
    )
    raw.set_annotations(annotations)


def _write_edf(raw: "mne.io.RawArray", out_path: Path) -> None:
    raw.export(str(out_path), fmt="edf", overwrite=True, verbose=False)


def generate_standard(out_dir: Path) -> Path:
    """C3, O1, EOG + adnotacje OO/OZ/ZP — podstawowy test flow."""
    import mne

    raw = _make_raw(["C3", "O1", "EOG"])
    # EOG jako osobny typ żeby MNE nie mieszało przy pick()
    raw.set_channel_types({"EOG": "eog"})
    _add_task_annotations(raw)
    out = out_dir / "test_standard.edf"
    _write_edf(raw, out)
    print(f"  OK  {out.name}")
    return out


def generate_bad_channels(out_dir: Path) -> Path:
    """EEG 4 (zamiast C3), EEG 7 (zamiast O1) — test pickera mapowania."""
    raw = _make_raw(["EEG 4", "EEG 7"])
    _add_task_annotations(raw)
    out = out_dir / "test_bad_channels.edf"
    _write_edf(raw, out)
    print(f"  OK  {out.name}")
    return out


def generate_no_annotations(out_dir: Path) -> Path:
    """C3, O1 — brak adnotacji, pipeline musi użyć fallbacku 3×180 s."""
    raw = _make_raw(["C3", "O1"])
    out = out_dir / "test_no_annotations.edf"
    _write_edf(raw, out)
    print(f"  OK  {out.name}")
    return out


def main() -> None:
    try:
        import mne  # noqa: F401
    except ImportError:
        print("BŁĄD: MNE-Python niedostępny. Uruchom: pip install mne", file=sys.stderr)
        sys.exit(1)

    try:
        import mne.export  # noqa: F401
    except Exception:
        pass

    out_dir = FIXTURES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Generowanie syntetycznych plików EEG...")
    generate_standard(out_dir)
    generate_bad_channels(out_dir)
    generate_no_annotations(out_dir)
    print()
    print("Gotowe. Pliki w:", out_dir)
    print()
    print("Scenariusze testowe:")
    print("  test_standard.edf       -- pelny flow: metryka -> import -> analiza -> wyniki")
    print("  test_bad_channels.edf   -- picker mapowania kanalow (C3=EEG 4, O1=EEG 7)")
    print("  test_no_annotations.edf -- fallback segmentacji 3x180 s")


if __name__ == "__main__":
    main()
