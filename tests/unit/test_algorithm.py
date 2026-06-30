from __future__ import annotations

from datetime import datetime

import pytest

from app.domain.algorithm import _EPSILON, _cell_color, classify
from app.domain.norms import load, resolve_norms_path
from app.domain.types import (
    BandRange,
    CategoryDescriptions,
    CellColor,
    NormEntry,
    NormsConfig,
    ObservationCategory,
    ObservationChecklist,
    RecommendationRules,
    ScreeningCategory,
)

_RULES = RecommendationRules(
    indication_min_red=5,
    indication_max_green=3,
    no_indication_min_green=4,
    no_indication_max_red=3,
)

_DESCRIPTIONS = CategoryDescriptions(
    wskazanie="Wskazanie testowe",
    obserwacja="Obserwacja testowa",
    brak="Brak testowe",
)

_BAND_RANGES: dict[str, BandRange] = {
    "Theta": BandRange(l_freq=4.0, h_freq=8.0),
}

_NORMS_10: tuple[NormEntry, ...] = tuple(
    NormEntry(
        norm_id=i + 1,
        channel="C3",
        task="OO",
        band="Theta",
        mean_z=10.0,
        mean_k=20.0,
    )
    for i in range(10)
)


_CHECKLIST = ObservationChecklist(
    title="Test",
    intro="Test intro",
    categories=(
        ObservationCategory(title="Test kategoria", items=("Pozycja 1",)),
    ),
)


def _config(
    *,
    rules: RecommendationRules = _RULES,
    descriptions: CategoryDescriptions = _DESCRIPTIONS,
) -> NormsConfig:
    return NormsConfig(
        version=1,
        power_line_frequency=50.0,
        band_ranges=_BAND_RANGES,
        norms=_NORMS_10,
        recommendation_rules=rules,
        category_descriptions=descriptions,
        observation_checklist=_CHECKLIST,
    )


def _amplitudes(value: float) -> list[float]:
    return [value] * 10


# ---------------------------------------------------------------------------
# Testy _cell_color
# ---------------------------------------------------------------------------


def test_cell_color_below_z_is_red() -> None:
    assert _cell_color(5.0, 10.0, 20.0) is CellColor.RED


def test_cell_color_equal_z_is_red() -> None:
    assert _cell_color(10.0, 10.0, 20.0) is CellColor.RED


def test_cell_color_above_z_below_k_is_yellow() -> None:
    assert _cell_color(15.0, 10.0, 20.0) is CellColor.YELLOW


def test_cell_color_equal_k_is_green() -> None:
    assert _cell_color(20.0, 10.0, 20.0) is CellColor.GREEN


def test_cell_color_above_k_is_green() -> None:
    assert _cell_color(25.0, 10.0, 20.0) is CellColor.GREEN


def test_cell_color_epsilon_at_z_boundary() -> None:
    # Dokładnie mean_z → RED (równość z epsilonem)
    assert _cell_color(10.0, 10.0, 20.0) is CellColor.RED
    # Lekko powyżej mean_z ale poniżej epsilon → RED
    assert _cell_color(10.0 + _EPSILON * 0.5, 10.0, 20.0) is CellColor.RED
    # Powyżej mean_z + epsilon → YELLOW
    assert _cell_color(10.0 + _EPSILON * 2, 10.0, 20.0) is CellColor.YELLOW


def test_cell_color_epsilon_at_k_boundary() -> None:
    # Dokładnie mean_k → GREEN
    assert _cell_color(20.0, 10.0, 20.0) is CellColor.GREEN
    # Lekko poniżej mean_k ale w granicach epsilon → GREEN
    assert _cell_color(20.0 - _EPSILON * 0.5, 10.0, 20.0) is CellColor.GREEN
    # Poniżej mean_k - epsilon → YELLOW
    assert _cell_color(20.0 - _EPSILON * 2, 10.0, 20.0) is CellColor.YELLOW


# ---------------------------------------------------------------------------
# Testy classify — kategorie
# ---------------------------------------------------------------------------


def test_all_red_is_wskazanie() -> None:
    # 10 amplitud poniżej mean_z (5.0 < 10.0)
    result = classify(_amplitudes(5.0), _config())
    assert result.category is ScreeningCategory.WSKAZANIE
    assert all(c.color is CellColor.RED for c in result.cells)
    assert result.description == "Wskazanie testowe"


def test_all_green_is_brak() -> None:
    # 10 amplitud powyżej mean_k (25.0 > 20.0)
    result = classify(_amplitudes(25.0), _config())
    assert result.category is ScreeningCategory.BRAK
    assert all(c.color is CellColor.GREEN for c in result.cells)
    assert result.description == "Brak testowe"


def test_all_yellow_is_obserwacja() -> None:
    # 10 amplitud między mean_z a mean_k (15.0 w przedziale 10–20)
    result = classify(_amplitudes(15.0), _config())
    assert result.category is ScreeningCategory.OBSERWACJA
    assert all(c.color is CellColor.YELLOW for c in result.cells)
    assert result.description == "Obserwacja testowa"


def test_boundary_5red_3green_is_wskazanie() -> None:
    # 5 red, 3 green, 2 yellow → WSKAZANIE (5 >= 5 i 3 <= 3)
    amplitudes = [5.0] * 5 + [25.0] * 3 + [15.0] * 2
    result = classify(amplitudes, _config())
    assert result.category is ScreeningCategory.WSKAZANIE


def test_boundary_4green_3red_is_brak() -> None:
    # 3 red, 4 green, 3 yellow → BRAK (4 >= 4 i 3 <= 3)
    amplitudes = [5.0] * 3 + [25.0] * 4 + [15.0] * 3
    result = classify(amplitudes, _config())
    assert result.category is ScreeningCategory.BRAK


def test_mixed_not_meeting_thresholds_is_obserwacja() -> None:
    # 4 red, 3 green, 3 yellow → nie spełnia ani WSKAZANIE (4 < 5) ani BRAK (3 < 4)
    amplitudes = [5.0] * 4 + [25.0] * 3 + [15.0] * 3
    result = classify(amplitudes, _config())
    assert result.category is ScreeningCategory.OBSERWACJA


def test_wskazanie_wins_when_both_conditions_overlap() -> None:
    # Przy liberalnych progach (min_red=3, max_green=5 / min_green=3, max_red=5)
    # 3 red + 3 green + 4 yellow spełnia OBA warunki jednocześnie → WSKAZANIE wygrywa
    overlapping_rules = RecommendationRules(
        indication_min_red=3,
        indication_max_green=5,
        no_indication_min_green=3,
        no_indication_max_red=5,
    )
    amplitudes = [5.0] * 3 + [25.0] * 3 + [15.0] * 4
    result = classify(amplitudes, _config(rules=overlapping_rules))
    assert result.category is ScreeningCategory.WSKAZANIE


def test_5red_4green_is_obserwacja() -> None:
    # 5 red spełnia indication_min_red=5, ale 4 green > indication_max_green=3
    # → WSKAZANIE nie przechodzi; 4 green >= no_indication_min_green=4, ale 5 red > no_indication_max_red=3
    # → BRAK nie przechodzi; wynik: OBSERWACJA
    amplitudes = [5.0] * 5 + [25.0] * 4 + [15.0] * 1
    result = classify(amplitudes, _config())
    assert result.category is ScreeningCategory.OBSERWACJA


# ---------------------------------------------------------------------------
# Testy classify — inne aspekty
# ---------------------------------------------------------------------------


def test_classify_returns_10_cells() -> None:
    result = classify(_amplitudes(15.0), _config())
    assert len(result.cells) == 10


def test_classify_cell_fields_from_norm_entry() -> None:
    result = classify(_amplitudes(5.0), _config())
    cell = result.cells[0]
    assert cell.cell_id == 1
    assert cell.channel == "C3"
    assert cell.task == "OO"
    assert cell.band == "Theta"


def test_classify_analyzed_at_default_is_now() -> None:
    before = datetime.now()
    result = classify(_amplitudes(15.0), _config())
    after = datetime.now()
    assert before <= result.analyzed_at <= after


def test_classify_analyzed_at_explicit() -> None:
    ts = datetime(2026, 6, 8, 12, 0, 0)
    result = classify(_amplitudes(15.0), _config(), analyzed_at=ts)
    assert result.analyzed_at == ts


def test_classify_wrong_length_raises() -> None:
    with pytest.raises(ValueError, match="9"):
        classify([1.0] * 9, _config())


def test_classify_empty_raises() -> None:
    with pytest.raises(ValueError):
        classify([], _config())


# ---------------------------------------------------------------------------
# Testy z prawdziwym norms.json
# ---------------------------------------------------------------------------


def test_classify_with_real_norms_config() -> None:
    # Smoke test: amplitude=0.0 is a safe sentinel (always below any mean_z).
    # For precision boundary coverage (mean_z ± 2ε, mean_k ± 2ε) see
    # test_algorithm_real_norms.py which also verifies result structure per norm.
    cfg = load(resolve_norms_path())
    result = classify([0.0] * 10, cfg)
    assert result.category is ScreeningCategory.WSKAZANIE
    assert len(result.cells) == 10
    assert cfg.recommendation_rules.indication_min_red == 5
