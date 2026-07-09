from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from app.domain.amplitude import AmplitudeMethod
from app.domain.calibration.csv_oracle import load_expert_csv
from app.domain.calibration.sweep import (
    iter_param_grid,
    run_sweep,
    score_variant,
)
from app.domain.norms import load, resolve_norms_path
from app.domain.signal_amplitude import SignalAmplitudeParams
from app.domain.types import NormsConfig, ScreeningCategory

_FIXTURE_CSV = Path(__file__).resolve().parent.parent / "fixtures" / "calibration_mini.csv"
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


@pytest.fixture(name="norms_config")
def fixture_norms_config() -> NormsConfig:
    return load(resolve_norms_path())


def test_iter_param_grid_respects_max_combinations() -> None:
    grid = iter_param_grid(
        methods=(AmplitudeMethod.MEAN_ABS, AmplitudeMethod.RMS),
        reject_broadband_uv=(0.0, 100.0),
        reject_filtered_uv=(200.0,),
        min_clean_seconds=(30.0,),
        max_combinations=2,
    )
    assert len(grid) == 2
    assert grid[0].amplitude_method is AmplitudeMethod.MEAN_ABS
    assert grid[0].reject_broadband_uv == 0.0
    assert grid[1].amplitude_method is AmplitudeMethod.MEAN_ABS
    assert grid[1].reject_broadband_uv == 100.0


def test_score_variant_with_mocked_harness(norms_config: NormsConfig, tmp_path: Path) -> None:
    adhd = tmp_path / "ADHD_EEG.edf"
    dep = tmp_path / "depresja_EEG.edf"
    adhd.write_bytes(b"stub")
    dep.write_bytes(b"stub")

    rows = load_expert_csv(_FIXTURE_CSV)
    from app.domain.calibration.csv_oracle import compute_category_centroids

    centroid = compute_category_centroids(rows, norms_config)[ScreeningCategory.WSKAZANIE]

    wsk_amps = rows[0].amplitudes

    def fake_compute(
        path: Path,
        config: NormsConfig,
        params: SignalAmplitudeParams,
    ) -> tuple[float, ...]:
        del config, params
        if path.name == "ADHD_EEG.edf":
            return wsk_amps
        return tuple(value * 1.1 for value in wsk_amps)

    params = SignalAmplitudeParams(
        amplitude_method=AmplitudeMethod.MEAN_ABS,
        reject_broadband_uv=0.0,
        reject_filtered_uv=200.0,
        min_clean_seconds=30.0,
    )
    score = score_variant(
        params,
        edf_dir=tmp_path,
        config=norms_config,
        wskazanie_centroid=centroid,
        compute_amplitudes=fake_compute,
    )
    assert score.avg_distance < float("inf")
    assert len(score.anchors) == 2
    assert all(anchor.ratios is not None for anchor in score.anchors)


def test_run_sweep_produces_ranking(norms_config: NormsConfig, tmp_path: Path) -> None:
    (tmp_path / "ADHD_EEG.edf").write_bytes(b"stub")
    (tmp_path / "depresja_EEG.edf").write_bytes(b"stub")
    rows = load_expert_csv(_FIXTURE_CSV)

    from app.domain.calibration.sweep import _METHOD_COMPLEXITY

    def fake_compute(
        path: Path,
        config: NormsConfig,
        params: SignalAmplitudeParams,
    ) -> tuple[float, ...]:
        del path, config
        scale = 1.0 + _METHOD_COMPLEXITY[params.amplitude_method] * 0.01
        return tuple(1.5 * scale for _ in range(10))

    report = run_sweep(
        csv_rows=rows,
        config=norms_config,
        edf_dir=tmp_path,
        compute_amplitudes=fake_compute,
        methods=(AmplitudeMethod.MEAN_ABS, AmplitudeMethod.RMS),
        max_combinations=2,
    )
    assert report.evaluated_combinations == 2
    assert len(report.ranked) == 2
    assert report.ranked[0].avg_distance <= report.ranked[1].avg_distance


def test_calibrate_script_smoke_with_mocked_sweep(
    norms_config: NormsConfig,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    csv_path = _FIXTURE_CSV
    edf_dir = tmp_path
    (edf_dir / "ADHD_EEG.edf").write_bytes(b"stub")
    (edf_dir / "depresja_EEG.edf").write_bytes(b"stub")

    if str(_SCRIPTS_DIR.parent) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR.parent))
    import scripts.calibrate_against_expert_csv as calibrate_module
    from scripts.calibrate_against_expert_csv import main

    rows = load_expert_csv(csv_path)

    def fake_run_sweep(**kwargs: object) -> object:
        from app.domain.calibration.sweep import SweepReport

        del kwargs
        return SweepReport(
            timestamp=__import__("datetime").datetime.now(
                tz=__import__("datetime").timezone.utc
            ),
            csv_row_count=len(rows),
            category_counts={
                ScreeningCategory.WSKAZANIE: 2,
                ScreeningCategory.BRAK: 1,
                ScreeningCategory.OBSERWACJA: 1,
            },
            wskazanie_centroid=(0.5,) * 10,
            ranked=(),
            total_combinations=300,
            evaluated_combinations=2,
        )

    with patch.object(calibrate_module, "run_sweep", side_effect=fake_run_sweep):
        exit_code = main(
            [
                "--csv-path",
                str(csv_path),
                "--edf-dir",
                str(edf_dir),
                "--stdout-only",
                "--max-combinations",
                "2",
            ]
        )
    assert exit_code == 0


def test_calibrate_script_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sys.path.insert(0, str(_SCRIPTS_DIR.parent))
    from scripts.calibrate_against_expert_csv import _report_to_json
    from app.domain.calibration.sweep import AnchorProfile, SweepReport, VariantScore
    from datetime import datetime, timezone

    params = SignalAmplitudeParams(
        amplitude_method=AmplitudeMethod.MEAN_ABS,
        reject_broadband_uv=0.0,
        reject_filtered_uv=200.0,
        min_clean_seconds=30.0,
    )
    anchor = AnchorProfile(
        label="ADHD",
        path=tmp_path / "ADHD_EEG.edf",
        ratios=(0.5,) * 10,
        distance=0.1,
        error=None,
    )
    score = VariantScore(
        params=params,
        anchors=(anchor,),
        avg_distance=0.1,
        profile_variance=0.0,
        aggressiveness=100.0,
        method_complexity=0,
    )
    report = SweepReport(
        timestamp=datetime(2026, 7, 9, tzinfo=timezone.utc),
        csv_row_count=4,
        category_counts={ScreeningCategory.WSKAZANIE: 2},
        wskazanie_centroid=(0.5,) * 10,
        ranked=(score,),
        total_combinations=300,
        evaluated_combinations=1,
    )
    payload = _report_to_json(report)
    text = json.dumps(payload)
    assert "mean_abs" in text
