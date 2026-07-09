"""Porównanie metod amplitudy na plikach referencyjnych — harness offline.

Uruchom:
  python scripts/compare_amplitude_methods.py [ścieżka_norms.json]

Używa ``calibration.harness.compute_amplitudes`` (nie produkcyjnego ``pipeline.run``).
Metoda amplitudy wybierana per wariant ``SignalAmplitudeParams``, nie z GUI.
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domain.algorithm import classify
from app.domain.amplitude import AmplitudeMethod
from app.domain.calibration.harness import compute_amplitudes
from app.domain.errors import PipelineError
from app.domain.norms import load, resolve_norms_path
from app.domain.signal_amplitude import LEGACY_PIPELINE_PARAMS, SignalAmplitudeParams

REFERENCE_FILES: tuple[tuple[str, str, bool], ...] = (
    (r"D:\CVGOSI\NF dane\Testowe\ok_EEG.edf", "Brak wskazań (wzorcowe)", False),
    (r"D:\CVGOSI\NF dane\Testowe\ADHD_EEG.edf", "ADHD", True),
    (r"D:\CVGOSI\NF dane\Testowe\depresja_EEG.edf", "Depresja", True),
    (r"D:\CVGOSI\NF dane\Testowe\Kuczyński.EEG", "Brak (ekspert, legacy)", False),
)

ALL_METHODS: tuple[AmplitudeMethod, ...] = tuple(AmplitudeMethod)


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
    norms_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    print("Porównanie metod amplitudy (harness offline)")
    print(f"Normy: {norms_arg or resolve_norms_path()}")
    print(f"Parametry bazowe: reject_filtered={LEGACY_PIPELINE_PARAMS.reject_filtered_uv} µV")
    print()

    for path_str, label, scored in REFERENCE_FILES:
        path = Path(path_str)
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
            outcome = _classify_with_method(path, norms_arg, params)
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
