"""Porównanie metod amplitudy na plikach referencyjnych — narzędzie dla eksperta.

Uruchom:
  python scripts/compare_amplitude_methods.py [ścieżka_norms.json]

Domyślnie ładuje norms.json obok projektu. Ustaw w pliku norm:
  "amplitude_method": "peak_to_peak_half"
aby aplikacja używała wybranej metody.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domain.algorithm import classify
from app.domain.amplitude import AmplitudeMethod, compute_band_amplitude
from app.domain.errors import PipelineError
from app.domain.norms import load, resolve_norms_path
from app.domain.pipeline import run as run_pipeline

REFERENCE_FILES: tuple[tuple[str, str], ...] = (
    (r"D:\CVGOSI\NF dane\Testowe\ok_EEG.edf", "Brak wskazań (wzorcowe)"),
    (r"D:\CVGOSI\NF dane\Testowe\ADHD_EEG.edf", "ADHD"),
    (r"D:\CVGOSI\NF dane\Testowe\depresja_EEG.edf", "Depresja"),
    (r"D:\CVGOSI\NF dane\Testowe\Kuczyński.EEG", "Brak (ekspert)"),
)

ALL_METHODS: tuple[AmplitudeMethod, ...] = tuple(AmplitudeMethod)


def _classify_with_method(
    path: Path,
    config_path: Path | None,
    method: AmplitudeMethod,
) -> tuple[str, int, int, int] | str:
    config = load(config_path or resolve_norms_path())
    # Tymczasowa konfiguracja z wybraną metodą (bez zapisywania pliku).
    from dataclasses import replace

    cfg = replace(config, amplitude_method=method)
    try:
        amps = run_pipeline(path, cfg)
    except PipelineError as exc:
        return f"BŁĄD [{exc.code}]: {exc}"
    result = classify(amps, cfg)
    red = sum(1 for c in result.cells if c.color.value == "red")
    green = sum(1 for c in result.cells if c.color.value == "green")
    yellow = sum(1 for c in result.cells if c.color.value == "yellow")
    return result.category.value, red, green, yellow


def main() -> None:
    norms_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    print("Porównanie metod amplitudy (eksperymentalne)")
    print(f"Normy: {norms_arg or resolve_norms_path()}")
    print()

    for path_str, label in REFERENCE_FILES:
        path = Path(path_str)
        print(f"{'=' * 70}")
        print(f"{path.name} — {label}")
        if not path.is_file():
            print("  (brak pliku — pominięto)")
            continue
        for method in ALL_METHODS:
            outcome = _classify_with_method(path, norms_arg, method)
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
