from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from app.domain.types import (
    AnalysisResult,
    CellColor,
    CellResult,
    NormsConfig,
    ScreeningCategory,
)

_EPSILON = 1e-6


def _cell_color(amplitude: float, mean_z: float, mean_k: float) -> CellColor:
    if amplitude <= mean_z + _EPSILON:
        return CellColor.RED
    if amplitude >= mean_k - _EPSILON:
        return CellColor.GREEN
    return CellColor.YELLOW


def _determine_category(
    red_count: int,
    green_count: int,
    config: NormsConfig,
) -> ScreeningCategory:
    rules = config.recommendation_rules
    if (
        red_count >= rules.indication_min_red
        and green_count <= rules.indication_max_green
    ):
        return ScreeningCategory.WSKAZANIE
    if (
        green_count >= rules.no_indication_min_green
        and red_count <= rules.no_indication_max_red
    ):
        return ScreeningCategory.BRAK
    return ScreeningCategory.OBSERWACJA


def classify(
    amplitudes: Sequence[float],
    config: NormsConfig,
    *,
    analyzed_at: datetime | None = None,
) -> AnalysisResult:
    """Klasyfikuje 10 amplitud (µV) względem norm — zwraca AnalysisResult."""
    if len(amplitudes) != len(config.norms):
        raise ValueError(
            f"Oczekiwano {len(config.norms)} amplitud, otrzymano {len(amplitudes)}."
        )

    cells: list[CellResult] = []
    red_count = 0
    green_count = 0

    for amplitude, norm in zip(amplitudes, config.norms, strict=True):
        color = _cell_color(amplitude, norm.mean_z, norm.mean_k)
        if color is CellColor.RED:
            red_count += 1
        elif color is CellColor.GREEN:
            green_count += 1
        cells.append(
            CellResult(
                cell_id=norm.norm_id,
                channel=norm.channel,
                task=norm.task,
                band=norm.band,
                color=color,
            )
        )

    category = _determine_category(red_count, green_count, config)

    descriptions = config.category_descriptions
    if category is ScreeningCategory.WSKAZANIE:
        description = descriptions.wskazanie
    elif category is ScreeningCategory.BRAK:
        description = descriptions.brak
    else:
        description = descriptions.obserwacja

    return AnalysisResult(
        cells=tuple(cells),
        category=category,
        description=description,
        analyzed_at=analyzed_at if analyzed_at is not None else datetime.now(),
    )
