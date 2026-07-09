from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from app.domain.types import (
    AnalysisResult,
    CellColor,
    CellResult,
    ClinicalDiagnosis,
    PatientMetadata,
    ScreeningCategory,
    Sex,
)
from app.storage.history import HistoryStore, StudyRecord, _CREATE_STUDIES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(analyzed_at: datetime | None = None) -> AnalysisResult:
    cells = tuple(
        CellResult(cell_id=i, channel="C3", task="OO", band="Theta", color=CellColor.YELLOW)
        for i in range(1, 11)
    )
    return AnalysisResult(
        cells=cells,
        category=ScreeningCategory.OBSERWACJA,
        description="Uważna obserwacja",
        analyzed_at=analyzed_at or datetime(2026, 6, 1, 10, 0, 0),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(tmp_path / "test.db")


@pytest.fixture
def sample_metadata() -> PatientMetadata:
    return PatientMetadata(age=8, sex=Sex.Z, initials="AN", birth_year="2018")


@pytest.fixture
def sample_result() -> AnalysisResult:
    from app.domain.algorithm import classify
    from app.domain.norms import load, resolve_norms_path
    cfg = load(resolve_norms_path())
    return classify([15.0] * 10, cfg)


# ---------------------------------------------------------------------------
# CRUD tests
# ---------------------------------------------------------------------------

def test_add_returns_id(
    store: HistoryStore,
    sample_metadata: PatientMetadata,
    sample_result: AnalysisResult,
) -> None:
    record_id = store.add(sample_metadata, sample_result)
    assert isinstance(record_id, int)
    assert record_id > 0


def test_has_any_false_when_empty(store: HistoryStore) -> None:
    assert store.has_any() is False


def test_has_any_true_after_add(
    store: HistoryStore,
    sample_metadata: PatientMetadata,
    sample_result: AnalysisResult,
) -> None:
    store.add(sample_metadata, sample_result)
    assert store.has_any() is True


def test_list_recent_empty(store: HistoryStore) -> None:
    assert store.list_recent() == []


def test_list_recent_returns_added_record(
    store: HistoryStore,
    sample_metadata: PatientMetadata,
    sample_result: AnalysisResult,
) -> None:
    store.add(sample_metadata, sample_result)
    records = store.list_recent()
    assert len(records) == 1
    rec = records[0]
    assert rec.age == sample_metadata.age
    assert rec.sex == sample_metadata.sex.value
    assert rec.initials == sample_metadata.initials
    assert rec.birth_year == sample_metadata.birth_year
    assert rec.category == sample_result.category.value


def test_list_recent_sorted_descending(
    store: HistoryStore,
    sample_metadata: PatientMetadata,
) -> None:
    older = _make_result(datetime(2026, 1, 1, 8, 0, 0))
    newer = _make_result(datetime(2026, 6, 1, 10, 0, 0))
    store.add(sample_metadata, older)
    store.add(sample_metadata, newer)
    records = store.list_recent()
    assert len(records) == 2
    assert records[0].analyzed_at > records[1].analyzed_at


def test_delete_removes_record(
    store: HistoryStore,
    sample_metadata: PatientMetadata,
    sample_result: AnalysisResult,
) -> None:
    record_id = store.add(sample_metadata, sample_result)
    store.delete(record_id)
    assert store.list_recent() == []


def test_delete_nonexistent_no_error(store: HistoryStore) -> None:
    store.delete(9999)  # should not raise


def test_update_identification_changes_fields(
    store: HistoryStore,
    sample_metadata: PatientMetadata,
    sample_result: AnalysisResult,
) -> None:
    record_id = store.add(sample_metadata, sample_result)
    updated = store.update_identification(
        record_id,
        initials="BK",
        birth_year="2017",
        custom_label="Klasa3B",
    )
    assert updated is True
    record = store.list_recent()[0]
    assert record.initials == "BK"
    assert record.birth_year == "2017"
    assert record.custom_label == "Klasa3B"


def test_update_identification_clears_optional_fields(
    store: HistoryStore,
    sample_metadata: PatientMetadata,
    sample_result: AnalysisResult,
) -> None:
    record_id = store.add(sample_metadata, sample_result)
    assert store.update_identification(
        record_id,
        initials=None,
        birth_year=None,
        custom_label=None,
    )
    record = store.list_recent()[0]
    assert record.initials is None
    assert record.birth_year is None
    assert record.custom_label is None


def test_update_identification_nonexistent_returns_false(store: HistoryStore) -> None:
    assert store.update_identification(
        9999,
        initials="AN",
        birth_year="2018",
        custom_label=None,
    ) is False


# ---------------------------------------------------------------------------
# Notice flag tests
# ---------------------------------------------------------------------------

def test_notice_flag_initially_false(store: HistoryStore) -> None:
    assert store.is_notice_shown() is False


def test_mark_notice_shown(store: HistoryStore) -> None:
    store.mark_notice_shown()
    assert store.is_notice_shown() is True


# ---------------------------------------------------------------------------
# Schema / init tests
# ---------------------------------------------------------------------------

def test_schema_created_on_init(tmp_path: Path) -> None:
    db_path = tmp_path / "fresh.db"
    assert not db_path.exists()
    s = HistoryStore(db_path)
    assert db_path.exists()
    # Tables accessible without error
    assert s.list_recent() == []
    assert s.is_notice_shown() is False


# ---------------------------------------------------------------------------
# StudyRecord.display_name tests
# ---------------------------------------------------------------------------

def _make_record(**kwargs: object) -> StudyRecord:
    defaults: dict[str, object] = {
        "id": 1,
        "analyzed_at": datetime(2026, 6, 1, 10, 30, 0),
        "initials": None,
        "birth_year": None,
        "custom_label": None,
        "age": 8,
        "sex": "Z",
        "category": ScreeningCategory.OBSERWACJA.value,
        "description": "test",
        "cells_json": "[]",
        "eeg_filename": None,
    }
    defaults.update(kwargs)
    return StudyRecord(**defaults)  # type: ignore[arg-type]


def test_display_name_with_initials() -> None:
    rec = _make_record(initials="AN", birth_year="2018")
    assert rec.display_name == "AN / 2018 / Dziewczynka"


def test_display_name_with_custom_label() -> None:
    rec = _make_record(custom_label="Klasa2A")
    assert rec.display_name == "Klasa2A / Dziewczynka"


def test_display_name_without_identification_includes_age_and_sex() -> None:
    rec = _make_record()
    assert rec.display_name == "8 lat, Dziewczynka"


def test_display_name_with_boy() -> None:
    rec = _make_record(sex="M", age=9)
    assert rec.display_name == "9 lat, Chłopiec"


# ---------------------------------------------------------------------------
# eeg_path / eeg_filename tests
# ---------------------------------------------------------------------------

def test_add_with_eeg_path(
    store: HistoryStore,
    sample_metadata: PatientMetadata,
    sample_result: AnalysisResult,
    tmp_path: Path,
) -> None:
    eeg_file = tmp_path / "patient_session.edf"
    store.add(sample_metadata, sample_result, eeg_path=eeg_file)
    records = store.list_recent()
    assert len(records) == 1
    assert records[0].eeg_filename == "patient_session.edf"


def test_add_without_eeg_path_eeg_filename_none(
    store: HistoryStore,
    sample_metadata: PatientMetadata,
    sample_result: AnalysisResult,
) -> None:
    store.add(sample_metadata, sample_result)
    assert store.list_recent()[0].eeg_filename is None


# ---------------------------------------------------------------------------
# resolve_history_db_path — dev path
# ---------------------------------------------------------------------------

def test_resolve_history_db_path_dev() -> None:
    from app.storage.history import resolve_history_db_path
    path = resolve_history_db_path()
    assert path.name == "history.db"
    # In dev (not frozen) the path should be in the project root,
    # not inside the app package directory.
    assert "app" not in path.parts[:-1] or path.parent.name != "app"


# ---------------------------------------------------------------------------
# list_for_patient tests
# ---------------------------------------------------------------------------

def test_list_for_patient_by_initials_and_birth_year(
    store: HistoryStore,
    sample_result: AnalysisResult,
) -> None:
    meta_a = PatientMetadata(age=8, sex=Sex.Z, initials="AN", birth_year="2018")
    meta_b = PatientMetadata(age=9, sex=Sex.M, initials="BK", birth_year="2017")
    store.add(meta_a, sample_result)
    store.add(meta_b, sample_result)
    records = store.list_for_patient("AN", "2018", None)
    assert len(records) == 1
    assert records[0].initials == "AN"


def test_list_for_patient_no_criteria_returns_all(
    store: HistoryStore,
    sample_metadata: PatientMetadata,
    sample_result: AnalysisResult,
) -> None:
    store.add(sample_metadata, sample_result)
    store.add(sample_metadata, sample_result)
    records = store.list_for_patient(None, None, None)
    assert len(records) == 2


def test_list_for_patient_by_custom_label(
    store: HistoryStore,
    sample_result: AnalysisResult,
) -> None:
    meta = PatientMetadata(age=7, sex=Sex.Z, custom_label="Klasa2A")
    store.add(meta, sample_result)
    store.add(PatientMetadata(age=8, sex=Sex.M), sample_result)
    records = store.list_for_patient(None, None, "Klasa2A")
    assert len(records) == 1
    assert records[0].custom_label == "Klasa2A"


def test_add_persists_diagnoses_json(
    store: HistoryStore,
    sample_result: AnalysisResult,
) -> None:
    meta = PatientMetadata(
        age=8,
        sex=Sex.Z,
        diagnoses=frozenset({ClinicalDiagnosis.ADHD, ClinicalDiagnosis.DYSLEXIA}),
    )
    store.add(meta, sample_result)
    row = store._conn.execute(
        "SELECT diagnoses_json FROM studies ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert row is not None
    payload = json.loads(row["diagnoses_json"])
    assert payload["diagnoses"] == ["adhd", "dyslexia"]
    assert payload["other_note"] is None


def test_schema_migration_adds_diagnoses_column(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(_CREATE_STUDIES)
    conn.commit()
    conn.close()

    store = HistoryStore(db_path)
    columns = {
        row["name"]
        for row in store._conn.execute("PRAGMA table_info(studies)").fetchall()
    }
    assert "diagnoses_json" in columns
