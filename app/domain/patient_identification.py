from __future__ import annotations

from datetime import date


def reference_date_for_birth_year(recording_date: date | None) -> date:
    """Data odniesienia do wyliczenia roku urodzenia z wieku (data nagrania lub dziś)."""
    return recording_date or date.today()


def birth_year_from_age(age: int, reference_date: date) -> str:
    return str(reference_date.year - age)


def birth_year_conflicts_with_age(
    age: int,
    birth_year: str,
    reference_date: date,
) -> bool:
    try:
        parsed = int(birth_year.strip())
    except ValueError:
        return False
    return parsed != reference_date.year - age


def resolve_birth_year(
    age: int,
    header_birth_year: str | None,
    recording_date: date | None,
) -> tuple[str, str | None]:
    """Zwraca rok do wyświetlenia oraz opcjonalny komunikat o sprzeczności z wiekiem."""
    ref = reference_date_for_birth_year(recording_date)
    expected = birth_year_from_age(age, ref)
    if header_birth_year and header_birth_year.strip():
        year = header_birth_year.strip()
        if birth_year_conflicts_with_age(age, year, ref):
            return year, f"Niezgodne z wiekiem (oczekiwany: {expected})"
        return year, None
    return expected, None
