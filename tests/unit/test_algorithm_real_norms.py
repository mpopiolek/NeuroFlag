from __future__ import annotations

import pytest

from app.domain.algorithm import _EPSILON, _cell_color, classify
from app.domain.norms import load, resolve_norms_path
from app.domain.types import CellColor, NormsConfig, ScreeningCategory

_REAL_CONFIG: NormsConfig = load(resolve_norms_path())

_NORM_IDS = [
    f"norm{n.norm_id}_{n.channel}_{n.task}_{n.band}" for n in _REAL_CONFIG.norms
]


# ---------------------------------------------------------------------------
# Testy graniczne _cell_color() z realnymi normami
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("norm", _REAL_CONFIG.norms, ids=_NORM_IDS)
def test_cell_color_below_z_boundary_real_norms(norm: object) -> None:
    from app.domain.types import NormEntry

    assert isinstance(norm, NormEntry)
    amplitude = norm.mean_z - 2 * _EPSILON
    assert _cell_color(amplitude, norm.mean_z, norm.mean_k) is CellColor.RED


@pytest.mark.parametrize("norm", _REAL_CONFIG.norms, ids=_NORM_IDS)
def test_cell_color_above_z_boundary_real_norms(norm: object) -> None:
    from app.domain.types import NormEntry

    assert isinstance(norm, NormEntry)
    amplitude = norm.mean_z + 2 * _EPSILON
    assert _cell_color(amplitude, norm.mean_z, norm.mean_k) is CellColor.YELLOW


@pytest.mark.parametrize("norm", _REAL_CONFIG.norms, ids=_NORM_IDS)
def test_cell_color_below_k_boundary_real_norms(norm: object) -> None:
    from app.domain.types import NormEntry

    assert isinstance(norm, NormEntry)
    amplitude = norm.mean_k - 2 * _EPSILON
    assert _cell_color(amplitude, norm.mean_z, norm.mean_k) is CellColor.YELLOW


@pytest.mark.parametrize("norm", _REAL_CONFIG.norms, ids=_NORM_IDS)
def test_cell_color_above_k_boundary_real_norms(norm: object) -> None:
    from app.domain.types import NormEntry

    assert isinstance(norm, NormEntry)
    amplitude = norm.mean_k + 2 * _EPSILON
    assert _cell_color(amplitude, norm.mean_z, norm.mean_k) is CellColor.GREEN


# ---------------------------------------------------------------------------
# Testy zbiorcze classify() z realnymi normami
# ---------------------------------------------------------------------------


def test_classify_all_below_mean_z_is_wskazanie(real_norms_config: NormsConfig) -> None:
    amplitudes = [n.mean_z - 2 * _EPSILON for n in real_norms_config.norms]
    result = classify(amplitudes, real_norms_config)
    assert result.category is ScreeningCategory.WSKAZANIE


def test_classify_all_above_mean_k_is_brak(real_norms_config: NormsConfig) -> None:
    amplitudes = [n.mean_k + 2 * _EPSILON for n in real_norms_config.norms]
    result = classify(amplitudes, real_norms_config)
    assert result.category is ScreeningCategory.BRAK
