from __future__ import annotations

from datetime import date

from app.domain.patient_identification import (
    birth_year_conflicts_with_age,
    birth_year_from_age,
    resolve_birth_year,
)


def test_birth_year_from_age_uses_recording_date() -> None:
    assert birth_year_from_age(8, date(2024, 6, 15)) == "2016"


def test_resolve_birth_year_infers_when_header_missing() -> None:
    year, conflict = resolve_birth_year(8, None, date(2024, 1, 1))
    assert year == "2016"
    assert conflict is None


def test_resolve_birth_year_matching_header() -> None:
    year, conflict = resolve_birth_year(8, "2016", date(2024, 1, 1))
    assert year == "2016"
    assert conflict is None


def test_resolve_birth_year_reports_conflict() -> None:
    year, conflict = resolve_birth_year(8, "2010", date(2024, 1, 1))
    assert year == "2010"
    assert conflict == "Niezgodne z wiekiem (oczekiwany: 2016)"


def test_birth_year_conflicts_with_age_invalid_year() -> None:
    assert birth_year_conflicts_with_age(8, "abc", date(2024, 1, 1)) is False
