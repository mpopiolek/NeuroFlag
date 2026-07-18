"""Sonda pipeline na plikach EEG — tylko do QA deweloperskiego (poza GUI).

Uruchomienie:
    python tests/fixtures/probe_pipeline.py <sciezka.edf|.vhdr> [<kolejny_plik> ...]
    python tests/fixtures/probe_pipeline.py --dir "D:\\CVGOSI\\NF dane\\Testowe"

Domyślnie nie wypisuje surowych wartości µV (zgodnie z regułą produktu).
Użyj --show-uv tylko lokalnie przy debugowaniu pipeline.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from app.domain.algorithm import classify
from app.domain.channels import normalize_channel_names
from app.domain.errors import PipelineError
from app.domain.norms import NormsLoadError, load
from app.domain.pipeline import run


def _load_mne_raw(path: Path) -> "mne.io.BaseRaw":
    import mne

    suffix = path.suffix.lower()
    if suffix == ".edf":
        return mne.io.read_raw_edf(path, preload=False, verbose=False)
    if suffix == ".vhdr":
        return mne.io.read_raw_brainvision(path, preload=False, verbose=False)
    raise ValueError(f"Nieobsługiwane rozszerzenie: {suffix}")


def _print_header(path: Path) -> None:
    import mne  # noqa: F401

    raw = _load_mne_raw(path)
    print(f"  kanały ({len(raw.ch_names)}): {', '.join(raw.ch_names[:12])}", end="")
    if len(raw.ch_names) > 12:
        print(f", … (+{len(raw.ch_names) - 12})", end="")
    print()
    print(f"  czas trwania: {raw.times[-1]:.1f} s, sfreq={raw.info['sfreq']:.1f} Hz")
    if len(raw.annotations):
        descs = sorted(set(raw.annotations.description))
        preview = ", ".join(descs[:8])
        if len(descs) > 8:
            preview += f", … (+{len(descs) - 8})"
        print(f"  adnotacje ({len(descs)} unikalnych): {preview}")
    else:
        print("  adnotacje: brak (przy >=8 min -> fallback 3x180 s od poczatku)")
    normalized = raw.copy()
    normalize_channel_names(normalized)
    has_c3 = "C3" in normalized.ch_names
    has_o1 = "O1" in normalized.ch_names
    print(f"  C3/O1 po aliasach: C3={'tak' if has_c3 else 'NIE'}, O1={'tak' if has_o1 else 'NIE'}")


def _probe_file(path: Path, *, show_uv: bool) -> int:
    print(f"\n{'=' * 60}")
    print(path.name)
    if not path.is_file():
        print("  BŁĄD: plik nie istnieje")
        return 1

    try:
        _print_header(path)
    except Exception as exc:
        print(f"  BŁĄD nagłówka: {exc}")
        return 1

    try:
        config = load(Path("norms.json"))
    except NormsLoadError as exc:
        print(f"  BŁĄD norms.json: {exc}")
        return 1

    try:
        t0 = time.perf_counter()
        amplitudes, _ = run(path, config)
        elapsed = time.perf_counter() - t0
    except PipelineError as exc:
        print(f"  PIPELINE: [{exc.code}] {exc.user_message_pl}")
        return 1

    has_nan = any(not (a == a) for a in amplitudes)  # NaN check
    result = classify(amplitudes, config)
    colors = [cell.color.value for cell in result.cells]
    print(f"  OK w {elapsed:.1f} s — 10 amplitud, NaN={has_nan}")
    print(f"  kategoria: {result.category.value}")
    print(f"  kolory: {colors}")
    if show_uv:
        print(f"  µV (dev): {[round(a, 4) for a in amplitudes]}")
    if elapsed > 600:
        print("  UWAGA: analiza >10 min — poza celem PRD")
    return 0


def _collect_paths(args: argparse.Namespace) -> list[Path]:
    seen: set[Path] = set()
    ordered: list[Path] = []
    for path in args.paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            ordered.append(resolved)
    if args.dir is not None:
        directory = args.dir.resolve()
        for pattern in ("*.edf", "*.vhdr"):
            for path in sorted(directory.glob(pattern)):
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    ordered.append(resolved)
    return ordered


def main() -> None:
    parser = argparse.ArgumentParser(description="Sonda pipeline EEG (QA deweloperskie)")
    parser.add_argument("paths", nargs="*", type=Path, help="Pliki .edf / .vhdr")
    parser.add_argument(
        "--dir",
        type=Path,
        help="Katalog z plikami testowymi (skanuje *.edf, *.vhdr)",
    )
    parser.add_argument(
        "--show-uv",
        action="store_true",
        help="Pokaż surowe µV (tylko lokalnie, nie dla pedagoga)",
    )
    args = parser.parse_args()
    paths = _collect_paths(args)
    if not paths:
        parser.print_help()
        print(
            "\nPrzykład:\n"
            '  python tests/fixtures/probe_pipeline.py --dir "D:\\CVGOSI\\NF dane\\Testowe"',
            file=sys.stderr,
        )
        sys.exit(2)

    failures = 0
    for path in paths:
        failures += _probe_file(path.resolve(), show_uv=args.show_uv)
    print()
    print(f"Podsumowanie: {len(paths) - failures}/{len(paths)} OK")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
