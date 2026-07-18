"""Kalibracja offline: sweep wariantów harness vs centroid Mitsar (Wskazanie).

Uruchom:
  python scripts/calibrate_against_expert_csv.py
  python scripts/calibrate_against_expert_csv.py --max-combinations 4
  python scripts/calibrate_against_expert_csv.py --csv-path path/to.csv --edf-dir path/

Wynik: ``reports/calibration_<timestamp>.md`` (+ opcjonalnie JSON w ``scripts/output/``).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.domain.amplitude import AmplitudeMethod, parse_amplitude_method
from app.domain.calibration.csv_oracle import ExpertCsvLoadError, load_expert_csv
from app.domain.calibration.harness import compute_amplitudes
from app.domain.calibration.paths import DEFAULT_EDF_DIR, DEFAULT_EXPERT_CSV
from app.domain.calibration.sweep import format_report, run_sweep
from app.domain.norms import load, resolve_norms_path
from app.domain.types import ScreeningCategory


@dataclass(frozen=True)
class CalibrationCliResult:
    report_path: Path | None
    json_path: Path | None
    exit_code: int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sweep wariantów amplitudy vs centroid Wskazanie (Mitsar CSV)",
    )
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=DEFAULT_EXPERT_CSV,
        help="Ścieżka do wyniki_indywidualne.csv",
    )
    parser.add_argument(
        "--edf-dir",
        type=Path,
        default=DEFAULT_EDF_DIR,
        help="Katalog z kotwicami ADHD_EEG.edf i depresja_EEG.edf",
    )
    parser.add_argument(
        "--norms",
        type=Path,
        default=None,
        help="Ścieżka norms.json (domyślnie resolve_norms_path())",
    )
    parser.add_argument(
        "--max-combinations",
        type=int,
        default=None,
        metavar="N",
        help="Ogranicz liczbę kombinacji grid (smoke / CI)",
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        default=None,
        metavar="METHOD",
        help="Podzbiór metod amplitudy (np. mean_abs welch_band_power)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Ile wariantów pokazać w raporcie (domyślnie 10)",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=Path("reports"),
        help="Katalog na raport Markdown",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Zapisz wynik rankingu jako JSON w scripts/output/",
    )
    parser.add_argument(
        "--stdout-only",
        action="store_true",
        help="Tylko stdout — bez zapisu pliku raportu",
    )
    return parser


def _parse_methods(raw: list[str] | None) -> tuple[AmplitudeMethod, ...] | None:
    if raw is None:
        return None
    return tuple(parse_amplitude_method(value) for value in raw)


def run_calibration(
    *,
    csv_path: Path,
    edf_dir: Path,
    norms_path: Path | None,
    max_combinations: int | None,
    methods: tuple[AmplitudeMethod, ...] | None,
    top: int,
    report_dir: Path,
    write_json: bool,
    stdout_only: bool,
) -> CalibrationCliResult:
    config = load(norms_path or resolve_norms_path())

    try:
        csv_rows = load_expert_csv(csv_path)
    except ExpertCsvLoadError as exc:
        print(f"BŁĄD CSV: {exc}", file=sys.stderr)
        return CalibrationCliResult(None, None, 1)

    report = run_sweep(
        csv_rows=csv_rows,
        config=config,
        edf_dir=edf_dir,
        compute_amplitudes=compute_amplitudes,
        methods=methods,
        max_combinations=max_combinations,
    )

    markdown = format_report(report, top_n=top)
    print(markdown)

    report_path: Path | None = None
    if not stdout_only:
        report_dir.mkdir(parents=True, exist_ok=True)
        stamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
        report_path = report_dir / f"calibration_{stamp}.md"
        report_path.write_text(markdown, encoding="utf-8")
        print(f"\nZapisano raport: {report_path}")

    json_path: Path | None = None
    if write_json:
        output_dir = Path("scripts") / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = report.timestamp.strftime("%Y%m%d_%H%M%S")
        json_path = output_dir / f"calibration_{stamp}.json"
        payload = _report_to_json(report)
        json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Zapisano JSON: {json_path}")

    return CalibrationCliResult(report_path, json_path, 0)


def _report_to_json(report: object) -> dict[str, object]:
    from app.domain.calibration.sweep import SweepReport, format_params

    assert isinstance(report, SweepReport)
    return {
        "timestamp": report.timestamp.isoformat(),
        "csv_row_count": report.csv_row_count,
        "category_counts": {
            category.value: report.category_counts.get(category, 0)
            for category in ScreeningCategory
        },
        "wskazanie_centroid": list(report.wskazanie_centroid),
        "total_combinations": report.total_combinations,
        "evaluated_combinations": report.evaluated_combinations,
        "ranked": [
            {
                "params": {
                    "amplitude_method": score.params.amplitude_method.value,
                    "reject_broadband_uv": score.params.reject_broadband_uv,
                    "reject_filtered_uv": score.params.reject_filtered_uv,
                    "epoch_seconds": score.params.epoch_seconds,
                    "min_clean_seconds": score.params.min_clean_seconds,
                },
                "params_label": format_params(score.params),
                "avg_distance": score.avg_distance,
                "profile_variance": score.profile_variance,
                "anchors": [
                    {
                        "label": anchor.label,
                        "path": str(anchor.path),
                        "distance": anchor.distance,
                        "ratios": list(anchor.ratios) if anchor.ratios else None,
                        "error": anchor.error,
                    }
                    for anchor in score.anchors
                ],
            }
            for score in report.ranked
        ],
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_combinations is not None and args.max_combinations < 1:
        print("--max-combinations musi być >= 1", file=sys.stderr)
        return 2

    result = run_calibration(
        csv_path=args.csv_path,
        edf_dir=args.edf_dir,
        norms_path=args.norms,
        max_combinations=args.max_combinations,
        methods=_parse_methods(args.methods),
        top=args.top,
        report_dir=args.report_dir,
        write_json=args.json,
        stdout_only=args.stdout_only,
    )
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
