from __future__ import annotations

import itertools
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Callable

from app.domain.amplitude import AmplitudeMethod
from app.domain.calibration.csv_oracle import (
    ExpertCsvRow,
    classify_csv_row,
    compute_category_centroids,
    profile_distance,
    profile_ratios,
)
from app.domain.errors import PipelineError
from app.domain.signal_amplitude import SignalAmplitudeParams
from app.domain.types import NormsConfig, ScreeningCategory

if TYPE_CHECKING:
    pass

DEFAULT_REJECT_BROADBAND_UV: tuple[float, ...] = (0.0, 100.0, 150.0, 200.0, 300.0)
DEFAULT_REJECT_FILTERED_UV: tuple[float, ...] = (100.0, 150.0, 200.0, 300.0)
DEFAULT_MIN_CLEAN_SECONDS: tuple[float, ...] = (30.0, 60.0, 90.0)

_METHOD_COMPLEXITY: dict[AmplitudeMethod, int] = {
    AmplitudeMethod.MEAN_ABS: 0,
    AmplitudeMethod.RMS: 1,
    AmplitudeMethod.PEAK_TO_PEAK_HALF: 2,
    AmplitudeMethod.PERCENTILE_95: 3,
    AmplitudeMethod.EPOCH_MEAN_ABS: 4,
    AmplitudeMethod.WELCH_BAND_POWER: 5,
}

ANCHOR_EDF_NAMES: tuple[tuple[str, str], ...] = (
    ("ADHD_EEG.edf", "ADHD"),
    ("depresja_EEG.edf", "depresja"),
)


@dataclass(frozen=True)
class AnchorProfile:
    label: str
    path: Path
    ratios: tuple[float, ...] | None
    distance: float | None
    error: str | None


@dataclass(frozen=True)
class VariantScore:
    params: SignalAmplitudeParams
    anchors: tuple[AnchorProfile, ...]
    avg_distance: float
    profile_variance: float
    aggressiveness: float
    method_complexity: int

    @property
    def sort_key(self) -> tuple[float, float, float, int]:
        return (
            self.avg_distance,
            self.profile_variance,
            self.aggressiveness,
            self.method_complexity,
        )


@dataclass(frozen=True)
class SweepReport:
    timestamp: datetime
    csv_row_count: int
    category_counts: dict[ScreeningCategory, int]
    wskazanie_centroid: tuple[float, ...]
    ranked: tuple[VariantScore, ...]
    total_combinations: int
    evaluated_combinations: int


def iter_param_grid(
    *,
    methods: tuple[AmplitudeMethod, ...] | None = None,
    reject_broadband_uv: tuple[float, ...] = DEFAULT_REJECT_BROADBAND_UV,
    reject_filtered_uv: tuple[float, ...] = DEFAULT_REJECT_FILTERED_UV,
    min_clean_seconds: tuple[float, ...] = DEFAULT_MIN_CLEAN_SECONDS,
    max_combinations: int | None = None,
) -> tuple[SignalAmplitudeParams, ...]:
    """Buduje siatkę wariantów harness (domyślnie pełny grid planu fazy 3)."""
    method_values = methods if methods is not None else tuple(AmplitudeMethod)
    combos = itertools.product(
        method_values,
        reject_broadband_uv,
        reject_filtered_uv,
        min_clean_seconds,
    )
    params_list: list[SignalAmplitudeParams] = []
    for method, bb, rf, mc in combos:
        params_list.append(
            SignalAmplitudeParams(
                amplitude_method=method,
                reject_broadband_uv=bb,
                reject_filtered_uv=rf,
                min_clean_seconds=mc,
            )
        )
        if max_combinations is not None and len(params_list) >= max_combinations:
            break
    return tuple(params_list)


def category_distribution(
    rows: tuple[ExpertCsvRow, ...],
    config: NormsConfig,
) -> dict[ScreeningCategory, int]:
    counts = {category: 0 for category in ScreeningCategory}
    for row in rows:
        counts[classify_csv_row(row.amplitudes, config)] += 1
    return counts


def _aggressiveness(params: SignalAmplitudeParams) -> float:
    broadband_score = (
        300.0 - params.reject_broadband_uv if params.reject_broadband_uv > 0 else 0.0
    )
    filtered_score = 300.0 - params.reject_filtered_uv
    return broadband_score + filtered_score + params.min_clean_seconds


def _profile_variance(profiles: tuple[tuple[float, ...], ...]) -> float:
    flat = [value for profile in profiles for value in profile]
    if len(flat) < 2:
        return 0.0
    return statistics.pvariance(flat)


def _evaluate_anchor(
    path: Path,
    label: str,
    config: NormsConfig,
    params: SignalAmplitudeParams,
    wskazanie_centroid: tuple[float, ...],
    compute_amplitudes: Callable[[Path, NormsConfig, SignalAmplitudeParams], tuple[float, ...]],
) -> AnchorProfile:
    try:
        amplitudes = compute_amplitudes(path, config, params)
        ratios = profile_ratios(amplitudes, config)
        distance = profile_distance(ratios, wskazanie_centroid)
        return AnchorProfile(
            label=label,
            path=path,
            ratios=ratios,
            distance=distance,
            error=None,
        )
    except PipelineError as exc:
        return AnchorProfile(
            label=label,
            path=path,
            ratios=None,
            distance=None,
            error=f"{exc.code}: {exc.user_message_pl}",
        )


def score_variant(
    params: SignalAmplitudeParams,
    *,
    edf_dir: Path,
    config: NormsConfig,
    wskazanie_centroid: tuple[float, ...],
    compute_amplitudes: Callable[[Path, NormsConfig, SignalAmplitudeParams], tuple[float, ...]],
) -> VariantScore:
    anchors: list[AnchorProfile] = []
    for filename, label in ANCHOR_EDF_NAMES:
        anchors.append(
            _evaluate_anchor(
                edf_dir / filename,
                label,
                config,
                params,
                wskazanie_centroid,
                compute_amplitudes,
            )
        )

    distances = [
        anchor.distance
        for anchor in anchors
        if anchor.distance is not None
    ]
    avg_distance = (
        sum(distances) / len(distances)
        if len(distances) == len(anchors)
        else float("inf")
    )

    successful_ratios = tuple(
        anchor.ratios for anchor in anchors if anchor.ratios is not None
    )
    variance = _profile_variance(successful_ratios) if successful_ratios else float("inf")

    return VariantScore(
        params=params,
        anchors=tuple(anchors),
        avg_distance=avg_distance,
        profile_variance=variance,
        aggressiveness=_aggressiveness(params),
        method_complexity=_METHOD_COMPLEXITY[params.amplitude_method],
    )


def run_sweep(
    *,
    csv_rows: tuple[ExpertCsvRow, ...],
    config: NormsConfig,
    edf_dir: Path,
    compute_amplitudes: Callable[[Path, NormsConfig, SignalAmplitudeParams], tuple[float, ...]],
    methods: tuple[AmplitudeMethod, ...] | None = None,
    max_combinations: int | None = None,
) -> SweepReport:
    """Uruchamia sweep wariantów i zwraca ranking wg odległości od centroidu Wskazanie."""
    centroids = compute_category_centroids(csv_rows, config)
    if ScreeningCategory.WSKAZANIE not in centroids:
        raise ValueError("Brak centroidu kategorii Wskazanie w CSV eksperta")

    wskazanie_centroid = centroids[ScreeningCategory.WSKAZANIE]
    grid = iter_param_grid(methods=methods, max_combinations=max_combinations)
    full_grid_size = len(
        iter_param_grid(methods=methods, max_combinations=None)
    )

    scores = [
        score_variant(
            params,
            edf_dir=edf_dir,
            config=config,
            wskazanie_centroid=wskazanie_centroid,
            compute_amplitudes=compute_amplitudes,
        )
        for params in grid
    ]
    ranked = tuple(sorted(scores, key=lambda item: item.sort_key))

    return SweepReport(
        timestamp=datetime.now(tz=timezone.utc),
        csv_row_count=len(csv_rows),
        category_counts=category_distribution(csv_rows, config),
        wskazanie_centroid=wskazanie_centroid,
        ranked=ranked,
        total_combinations=full_grid_size,
        evaluated_combinations=len(grid),
    )


def format_params(params: SignalAmplitudeParams) -> str:
    return (
        f"method={params.amplitude_method.value}, "
        f"bb={params.reject_broadband_uv:g}, "
        f"rf={params.reject_filtered_uv:g}, "
        f"min_clean={params.min_clean_seconds:g}s"
    )


def format_report(report: SweepReport, *, top_n: int = 10) -> str:
    lines: list[str] = []
    ts = report.timestamp.strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"# Raport kalibracji NeuroFlag vs Mitsar ({ts})")
    lines.append("")
    lines.append("## Podsumowanie CSV")
    lines.append("")
    lines.append(f"- Wiersze CSV: {report.csv_row_count}")
    lines.append("- Rozkład kategorii (sanity check):")
    for category in ScreeningCategory:
        count = report.category_counts.get(category, 0)
        lines.append(f"  - {category.value}: {count}")
    lines.append("")
    lines.append("## Centroid Wskazanie (mediana profili CSV)")
    lines.append("")
    centroid_str = ", ".join(f"{value:.3f}" for value in report.wskazanie_centroid)
    lines.append(f"`[{centroid_str}]`")
    lines.append("")
    lines.append(
        f"## Ranking wariantów (top {top_n} z "
        f"{report.evaluated_combinations}/{report.total_combinations} kombinacji)"
    )
    lines.append("")
    lines.append(
        "| # | avg_dist | method | bb | rf | min_clean | ADHD | depresja |"
    )
    lines.append("|---|----------|--------|----|----|-----------|------|----------|")

    for index, score in enumerate(report.ranked[:top_n], start=1):
        adhd = next(a for a in score.anchors if a.label == "ADHD")
        dep = next(a for a in score.anchors if a.label == "depresja")
        adhd_cell = f"{adhd.distance:.3f}" if adhd.distance is not None else "ERR"
        dep_cell = f"{dep.distance:.3f}" if dep.distance is not None else "ERR"
        params = score.params
        lines.append(
            f"| {index} | {score.avg_distance:.3f} | {params.amplitude_method.value} "
            f"| {params.reject_broadband_uv:g} | {params.reject_filtered_uv:g} "
            f"| {params.min_clean_seconds:g} | {adhd_cell} | {dep_cell} |"
        )

    if report.ranked:
        winner = report.ranked[0]
        lines.append("")
        lines.append("## Zwycięzca")
        lines.append("")
        lines.append(f"- Parametry: `{format_params(winner.params)}`")
        lines.append(f"- Średnia odległość od centroidu Wskazanie: {winner.avg_distance:.4f}")
        for anchor in winner.anchors:
            if anchor.ratios is not None:
                ratio_str = ", ".join(f"{value:.3f}" for value in anchor.ratios)
                lines.append(f"- Profil {anchor.label} (amp/mean_z): `[{ratio_str}]`")
            elif anchor.error is not None:
                lines.append(f"- {anchor.label}: błąd — {anchor.error}")

    lines.append("")
    lines.append("## Wykluczone z scoringu")
    lines.append("")
    lines.append("- `ok_EEG.edf` (flat-line C3/O1)")
    lines.append("- `Kuczyński.EEG` (legacy DigiTrack)")
    return "\n".join(lines)
