from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from app.domain.types import (
    AnalysisResult,
    CellColor,
    CellResult,
    PatientMetadata,
    ScreeningCategory,
    Sex,
)
from app.storage.history import HistoryStore, StudyRecord


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
    assert "AN" in rec.display_name
    assert "2018" in rec.display_name


def test_display_name_fallback() -> None:
    rec = _make_record()
    assert rec.display_name  # not empty
    assert "2026" in rec.display_name  # fallback contains analysis year
