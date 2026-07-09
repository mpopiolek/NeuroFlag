from __future__ import annotations

import csv
import statistics
from dataclasses import dataclass
from math import sqrt
from pathlib import Path

from app.domain.algorithm import classify
from app.domain.types import NormsConfig, ScreeningCategory

CELL_CSV_COLUMNS: tuple[tuple[int, str], ...] = (
    (1, "oczy_zamkniete C3 Theta"),
    (2, "poznawcze C3 Theta"),
    (3, "poznawcze C3 Beta1_bez_SMR"),
    (4, "oczy_otwarte C3 Beta2"),
    (5, "oczy_otwarte O1 Delta"),
    (6, "oczy_otwarte O1 Theta"),
    (7, "oczy_zamkniete O1 Theta"),
    (8, "poznawcze O1 Theta"),
    (9, "oczy_otwarte O1 Beta2"),
    (10, "poznawcze O1 Beta2"),
)


@dataclass(frozen=True)
class ExpertCsvRow:
    row_id: str
    grupa: str
    amplitudes: tuple[float, ...]


class ExpertCsvLoadError(Exception):
    """Błąd wczytywania CSV Mitsar — komunikat po polsku dla skryptów kalibracji."""


def _parse_decimal(value: str, *, label: str) -> float:
    cleaned = value.strip()
    if not cleaned:
        raise ExpertCsvLoadError(f"Brak wartości liczbowej dla '{label}'")
    normalized = cleaned.replace(" ", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError as exc:
        raise ExpertCsvLoadError(
            f"Nie można sparsować '{label}': {value!r}"
        ) from exc


def _detect_delimiter(header_line: str) -> str:
    if ";" in header_line:
        return ";"
    if "," in header_line:
        return ","
    raise ExpertCsvLoadError(
        "Nagłówek CSV nie zawiera separatora ';' ani ','"
    )


def _norm_id_to_mean_z(config: NormsConfig) -> dict[int, float]:
    return {norm.norm_id: norm.mean_z for norm in config.norms}


def load_expert_csv(path: Path) -> tuple[ExpertCsvRow, ...]:
    """Wczytuje wyniki_indywidualne.csv — 10 amplitud Mitsar per wiersz."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise ExpertCsvLoadError(f"Nie można odczytać pliku '{path}': {exc}") from exc

    lines = text.splitlines()
    if not lines:
        raise ExpertCsvLoadError(f"Plik '{path}' jest pusty")

    delimiter = _detect_delimiter(lines[0])
    reader = csv.DictReader(lines, delimiter=delimiter)
    if reader.fieldnames is None:
        raise ExpertCsvLoadError(f"Brak nagłówka w '{path}'")

    fieldnames = {name.strip(): name for name in reader.fieldnames}
    for _norm_id, column_name in CELL_CSV_COLUMNS:
        if column_name not in fieldnames:
            raise ExpertCsvLoadError(
                f"Brak kolumny '{column_name}' w '{path}'"
            )

    id_key = fieldnames.get("id")
    grupa_key = fieldnames.get("grupa")
    if id_key is None:
        raise ExpertCsvLoadError(f"Brak kolumny 'id' w '{path}'")
    if grupa_key is None:
        raise ExpertCsvLoadError(f"Brak kolumny 'grupa' w '{path}'")

    rows: list[ExpertCsvRow] = []
    for line_no, raw_row in enumerate(reader, start=2):
        row_id = (raw_row.get(id_key) or "").strip()
        if not row_id:
            continue

        grupa = (raw_row.get(grupa_key) or "").strip()
        amplitudes: list[float] = []
        for norm_id, column_name in CELL_CSV_COLUMNS:
            raw_value = raw_row.get(fieldnames[column_name], "")
            if raw_value is None:
                raw_value = ""
            amplitudes.append(
                _parse_decimal(
                    raw_value,
                    label=f"wiersz {line_no}, kolumna '{column_name}' (norm_id={norm_id})",
                )
            )

        rows.append(
            ExpertCsvRow(
                row_id=row_id,
                grupa=grupa,
                amplitudes=tuple(amplitudes),
            )
        )

    if not rows:
        raise ExpertCsvLoadError(f"Brak danych w '{path}'")

    return tuple(rows)


def profile_ratios(
    amplitudes: tuple[float, ...],
    config: NormsConfig,
) -> tuple[float, ...]:
    """Profil amp/mean_z dla 10 komórek matrycy NeuroFlag."""
    if len(amplitudes) != len(config.norms):
        raise ValueError(
            f"Oczekiwano {len(config.norms)} amplitud, otrzymano {len(amplitudes)}"
        )

    mean_z_by_id = _norm_id_to_mean_z(config)
    ratios: list[float] = []
    for amplitude, norm in zip(amplitudes, config.norms, strict=True):
        if norm.norm_id not in mean_z_by_id:
            raise ValueError(f"Brak mean_z dla norm_id={norm.norm_id}")
        mean_z = mean_z_by_id[norm.norm_id]
        if mean_z <= 0:
            raise ValueError(f"mean_z musi być dodatnie dla norm_id={norm.norm_id}")
        ratios.append(amplitude / mean_z)
    return tuple(ratios)


def classify_csv_row(
    amplitudes: tuple[float, ...],
    config: NormsConfig,
) -> ScreeningCategory:
    """Klasyfikuje wiersz CSV algorytmem NeuroFlag (10 amplitud Mitsar)."""
    return classify(amplitudes, config).category


def compute_category_centroids(
    rows: tuple[ExpertCsvRow, ...],
    config: NormsConfig,
) -> dict[ScreeningCategory, tuple[float, ...]]:
    """Mediana profili amp/mean_z per kategoria algorytmu."""
    profiles_by_category: dict[ScreeningCategory, list[tuple[float, ...]]] = {
        ScreeningCategory.WSKAZANIE: [],
        ScreeningCategory.OBSERWACJA: [],
        ScreeningCategory.BRAK: [],
    }

    for row in rows:
        category = classify_csv_row(row.amplitudes, config)
        profiles_by_category[category].append(
            profile_ratios(row.amplitudes, config)
        )

    centroids: dict[ScreeningCategory, tuple[float, ...]] = {}
    for category, profiles in profiles_by_category.items():
        if not profiles:
            continue
        dimension_count = len(profiles[0])
        centroid = tuple(
            statistics.median(profile[i] for profile in profiles)
            for i in range(dimension_count)
        )
        centroids[category] = centroid

    return centroids


def profile_distance(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Odległość euklidesowa między dwoma profilami 10-wymiarowymi."""
    if len(a) != len(b):
        raise ValueError(
            f"Profile muszą mieć tę samą długość: {len(a)} vs {len(b)}"
        )
    return sqrt(sum((left - right) ** 2 for left, right in zip(a, b, strict=True)))
