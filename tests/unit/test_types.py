from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError
from datetime import datetime

from app.domain.types import (
    AnalysisResult,
    CellColor,
    CellResult,
    ClinicalDiagnosis,
    ExclusionDiagnosis,
    PatientMetadata,
    ScreeningCategory,
    Sex,
    format_clinical_diagnoses,
)


def test_patient_metadata_no_exclusions() -> None:
    p = PatientMetadata(age=8, sex=Sex.Z)
    assert p.is_excluded() is False


def test_patient_metadata_single_exclusion() -> None:
    p = PatientMetadata(age=7, sex=Sex.M, exclusions=frozenset({ExclusionDiagnosis.EPILEPSY}))
    assert p.is_excluded() is True


def test_patient_metadata_brain_injury_excluded() -> None:
    p = PatientMetadata(
        age=8,
        sex=Sex.Z,
        exclusions=frozenset({ExclusionDiagnosis.BRAIN_INJURY}),
    )
    assert p.is_excluded() is True


def test_patient_metadata_intellectual_disability_excluded() -> None:
    p = PatientMetadata(
        age=9,
        sex=Sex.M,
        exclusions=frozenset({ExclusionDiagnosis.INTELLECTUAL_DISABILITY}),
    )
    assert p.is_excluded() is True


def test_patient_metadata_multiple_exclusions() -> None:
    p = PatientMetadata(
        age=10,
        sex=Sex.Z,
        exclusions=frozenset({ExclusionDiagnosis.EPILEPSY, ExclusionDiagnosis.BRAIN_INJURY}),
    )
    assert p.is_excluded() is True


def test_patient_metadata_frozen() -> None:
    p = PatientMetadata(age=8, sex=Sex.Z)
    with pytest.raises(FrozenInstanceError):
        p.age = 9  # type: ignore[misc]


def test_patient_metadata_empty_diagnoses() -> None:
    p = PatientMetadata(age=8, sex=Sex.Z)
    assert p.diagnoses == frozenset()
    assert p.other_diagnosis_note is None


def test_patient_metadata_with_diagnoses() -> None:
    p = PatientMetadata(
        age=8,
        sex=Sex.Z,
        diagnoses=frozenset({ClinicalDiagnosis.ADHD}),
    )
    assert ClinicalDiagnosis.ADHD in p.diagnoses
    assert format_clinical_diagnoses(p) == "ADHD"


def test_format_clinical_diagnoses_other_with_note() -> None:
    p = PatientMetadata(
        age=7,
        sex=Sex.M,
        diagnoses=frozenset({ClinicalDiagnosis.OTHER}),
        other_diagnosis_note="Zaburzenia ze spektrum tików",
    )
    assert format_clinical_diagnoses(p) == "Inne (Zaburzenia ze spektrum tików)"


def test_cell_result_each_color() -> None:
    for color in CellColor:
        cell = CellResult(cell_id=1, channel="C3", task="OO", band="Theta", color=color)
        assert cell.color is color


def test_cell_result_frozen() -> None:
    cell = CellResult(cell_id=1, channel="C3", task="OO", band="Theta", color=CellColor.GREEN)
    with pytest.raises(FrozenInstanceError):
        cell.channel = "O1"  # type: ignore[misc]


def test_analysis_result_ten_cells() -> None:
    cells = tuple(
        CellResult(cell_id=i, channel="C3", task="OO", band="Theta", color=CellColor.GREEN)
        for i in range(1, 11)
    )
    result = AnalysisResult(
        cells=cells,
        category=ScreeningCategory.BRAK,
        description="Brak wskazań",
        analyzed_at=datetime(2026, 5, 31, 12, 0, 0),
    )
    assert len(result.cells) == 10
    assert result.category is ScreeningCategory.BRAK
