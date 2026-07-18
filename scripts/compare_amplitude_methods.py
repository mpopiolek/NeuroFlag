"""Porównanie metod amplitudy na plikach referencyjnych — harness offline.

Uruchom:
  python scripts/compare_amplitude_methods.py
  python scripts/compare_amplitude_methods.py --edf-dir path/to/Testowe
  python scripts/compare_amplitude_methods.py norms.json

Używa ``calibration.harness.compute_amplitudes`` (nie produkcyjnego ``pipeline.run``).
Metoda amplitudy wybierana per wariant ``SignalAmplitudeParams``, nie z GUI.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domain.algorithm import classify
from app.domain.amplitude import AmplitudeMethod
from app.domain.calibration.harness import compute_amplitudes
from app.domain.calibration.paths import DEFAULT_EDF_DIR
from app.domain.errors import PipelineError
from app.domain.norms import load, resolve_norms_path
from app.domain.signal_amplitude import LEGACY_PIPELINE_PARAMS, SignalAmplitudeParams

REFERENCE_FILE_SPECS: tuple[tuple[str, str, bool], ...] = (
    ("ok_EEG.edf", "Brak wskazań (wzorcowe)", False),
    ("ADHD_EEG.edf", "ADHD", True),
    ("depresja_EEG.edf", "Depresja", True),
    ("Kuczyński.EEG", "Brak (ekspert, legacy)", False),
)

ALL_METHODS: tuple[AmplitudeMethod, ...] = tuple(AmplitudeMethod)


def reference_files(edf_dir: Path) -> tuple[tuple[Path, str, bool], ...]:
    return tuple((edf_dir / name, label, scored) for name, label, scored in REFERENCE_FILE_SPECS)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Porównanie metod amplitudy na plikach referencyjnych (harness)",
    )
    parser.add_argument(
        "norms",
        nargs="?",
        type=Path,
        default=None,
        help="Ścieżka norms.json (domyślnie resolve_norms_path())",
    )
    parser.add_argument(
        "--edf-dir",
        type=Path,
        default=DEFAULT_EDF_DIR,
        help="Katalog z plikami referencyjnymi EDF/EEG",
    )
    return parser


def _classify_with_method(
    path: Path,
    config_path: Path | None,
    params: SignalAmplitudeParams,
) -> tuple[str, int, int, int] | str:
    config = load(config_path or resolve_norms_path())
    cfg = replace(config, amplitude_method=params.amplitude_method)
    try:
        amps = compute_amplitudes(path, cfg, params)
    except PipelineError as exc:
        return f"BŁĄD [{exc.code}]: {exc}"
    result = classify(amps, cfg)
    red = sum(1 for c in result.cells if c.color.value == "red")
    green = sum(1 for c in result.cells if c.color.value == "green")
    yellow = sum(1 for c in result.cells if c.color.value == "yellow")
    return result.category.value, red, green, yellow


def main() -> None:
    args = build_parser().parse_args()
    norms_path = args.norms
    edf_dir = args.edf_dir

    print("Porównanie metod amplitudy (harness offline)")
    print(f"Normy: {norms_path or resolve_norms_path()}")
    print(f"Katalog EDF: {edf_dir}")
    print(f"Parametry bazowe: reject_filtered={LEGACY_PIPELINE_PARAMS.reject_filtered_uv} µV")
    print()

    for path, label, scored in reference_files(edf_dir):
        print(f"{'=' * 70}")
        scoring_note = "scoring" if scored else "informacyjny (pominięty ze scoringu)"
        print(f"{path.name} — {label} [{scoring_note}]")
        if not path.is_file():
            print("  (brak pliku — pominięto)")
            continue
        for method in ALL_METHODS:
            params = replace(
                LEGACY_PIPELINE_PARAMS,
                amplitude_method=method,
            )
            outcome = _classify_with_method(path, norms_path, params)
            if isinstance(outcome, str):
                print(f"  {method.value:20s} {outcome}")
            else:
                category, red, green, yellow = outcome
                print(
                    f"  {method.value:20s} {category:32s} "
                    f"R={red} Y={yellow} G={green}"
                )
        print()


if __name__ == "__main__":
    main()
