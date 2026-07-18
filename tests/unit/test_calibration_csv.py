from __future__ import annotations

import math
from pathlib import Path

import pytest

from app.domain.calibration.csv_oracle import (
    ExpertCsvLoadError,
    classify_csv_row,
    compute_category_centroids,
    load_expert_csv,
    profile_distance,
    profile_ratios,
)
from app.domain.norms import load, resolve_norms_path
from app.domain.types import NormsConfig, ScreeningCategory

_FIXTURE_CSV = Path(__file__).resolve().parent.parent / "fixtures" / "calibration_mini.csv"


@pytest.fixture(name="norms_config")
def fixture_norms_config() -> NormsConfig:
    return load(resolve_norms_path())


def test_load_expert_csv_maps_ten_columns(norms_config: NormsConfig) -> None:
    rows = load_expert_csv(_FIXTURE_CSV)
    assert len(rows) == 4
    assert rows[0].row_id == "wsk1"
    assert rows[0].grupa == "2 (Z)"
    assert len(rows[0].amplitudes) == len(norms_config.norms)


def test_load_expert_csv_parses_decimal_comma() -> None:
    rows = load_expert_csv(_FIXTURE_CSV)
    assert rows[0].amplitudes[0] == pytest.approx(1.0)
    assert rows[1].amplitudes[0] == pytest.approx(2.0)
    assert rows[2].amplitudes[0] == pytest.approx(100.0)


def test_load_expert_csv_missing_column(tmp_path: Path) -> None:
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("id;grupa;oczy_zamkniete C3 Theta\n1;g;1,0\n", encoding="utf-8")
    with pytest.raises(ExpertCsvLoadError, match="Brak kolumny"):
        load_expert_csv(bad_csv)


def test_profile_ratios_matches_norm_order(norms_config: NormsConfig) -> None:
    amplitudes = tuple(10.0 for _ in norms_config.norms)
    ratios = profile_ratios(amplitudes, norms_config)
    assert len(ratios) == 10
    for ratio, norm in zip(ratios, norms_config.norms, strict=True):
        assert ratio == pytest.approx(10.0 / norm.mean_z)


def test_classify_csv_row_categories(norms_config: NormsConfig) -> None:
    rows = load_expert_csv(_FIXTURE_CSV)
    assert classify_csv_row(rows[0].amplitudes, norms_config) is ScreeningCategory.WSKAZANIE
    assert classify_csv_row(rows[1].amplitudes, norms_config) is ScreeningCategory.WSKAZANIE
    assert classify_csv_row(rows[2].amplitudes, norms_config) is ScreeningCategory.BRAK
    assert classify_csv_row(rows[3].amplitudes, norms_config) is ScreeningCategory.OBSERWACJA


def test_compute_category_centroids_median(norms_config: NormsConfig) -> None:
    rows = load_expert_csv(_FIXTURE_CSV)
    centroids = compute_category_centroids(rows, norms_config)

    assert ScreeningCategory.WSKAZANIE in centroids
    assert ScreeningCategory.BRAK in centroids
    assert ScreeningCategory.OBSERWACJA in centroids

    wsk_ratios_1 = profile_ratios(rows[0].amplitudes, norms_config)
    wsk_ratios_2 = profile_ratios(rows[1].amplitudes, norms_config)
    expected_wsk = tuple(
        (a + b) / 2.0 for a, b in zip(wsk_ratios_1, wsk_ratios_2, strict=True)
    )
    assert centroids[ScreeningCategory.WSKAZANIE] == pytest.approx(expected_wsk)

    brak_ratios = profile_ratios(rows[2].amplitudes, norms_config)
    assert centroids[ScreeningCategory.BRAK] == pytest.approx(brak_ratios)


def test_profile_distance_euclidean() -> None:
    a = (0.0, 0.0, 0.0)
    b = (3.0, 4.0, 0.0)
    assert profile_distance(a, b) == pytest.approx(5.0)


def test_profile_distance_requires_equal_length() -> None:
    with pytest.raises(ValueError, match="tę samą długość"):
        profile_distance((1.0, 2.0), (1.0,))


def test_profile_ratios_length_mismatch(norms_config: NormsConfig) -> None:
    with pytest.raises(ValueError, match="Oczekiwano"):
        profile_ratios((1.0, 2.0), norms_config)


def test_centroid_wskazanie_first_dimension(norms_config: NormsConfig) -> None:
    """Sanity: mediana ratio dla Theta OZ C3 przy amp 1 i 2 µV."""
    rows = load_expert_csv(_FIXTURE_CSV)
    centroids = compute_category_centroids(rows, norms_config)
    mean_z_norm1 = norms_config.norms[0].mean_z
    expected = ((1.0 / mean_z_norm1) + (2.0 / mean_z_norm1)) / 2.0
    assert centroids[ScreeningCategory.WSKAZANIE][0] == pytest.approx(expected)
    assert not math.isnan(centroids[ScreeningCategory.WSKAZANIE][0])
