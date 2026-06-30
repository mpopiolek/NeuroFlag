from __future__ import annotations

import json
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.domain.types import AnalysisResult, CellResult, PatientMetadata


@dataclass
class StudyRecord:
    id: int
    analyzed_at: datetime
    initials: str | None
    birth_year: str | None
    custom_label: str | None
    age: int
    sex: str
    category: str
    description: str
    cells_json: str
    eeg_filename: str | None

    @property
    def display_name(self) -> str:
        """Zwraca czytelny identyfikator dziecka dla listy historii."""
        parts: list[str] = []
        if self.initials:
            parts.append(self.initials)
        if self.birth_year:
            parts.append(self.birth_year)
        if parts:
            return " / ".join(parts)
        return self.analyzed_at.strftime("%Y-%m-%d %H:%M")


def resolve_history_db_path() -> Path:
    """Zwraca ścieżkę do history.db — obok .exe w dystrybucji, w root projektu w dev."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "history.db"
    return Path(__file__).parent.parent.parent / "history.db"


def _serialize_cells(cells: tuple[CellResult, ...]) -> str:
    return json.dumps(
        [
            {
                "cell_id": c.cell_id,
                "channel": c.channel,
                "task": c.task,
                "band": c.band,
                "color": c.color.value,
            }
            for c in cells
        ]
    )


_CREATE_STUDIES = """
CREATE TABLE IF NOT EXISTS studies (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    analyzed_at      TEXT    NOT NULL,
    initials         TEXT,
    birth_year       TEXT,
    custom_label     TEXT,
    age              INTEGER NOT NULL,
    sex              TEXT    NOT NULL,
    exclusions_json  TEXT    NOT NULL,
    category         TEXT    NOT NULL,
    description      TEXT    NOT NULL,
    cells_json       TEXT    NOT NULL,
    eeg_filename     TEXT
);
"""

_CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class HistoryStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute(_CREATE_STUDIES)
        cur.execute(_CREATE_SETTINGS)
        self._conn.commit()

    def add(
        self,
        metadata: PatientMetadata,
        result: AnalysisResult,
        *,
        eeg_path: Path | None = None,
    ) -> int:
        """Wstawia rekord i zwraca nowe id. eeg_path.name zapisywany jako eeg_filename."""
        exclusions_json = json.dumps([e.value for e in metadata.exclusions])
        cells_json = _serialize_cells(result.cells)
        eeg_filename = eeg_path.name if eeg_path is not None else None
        cur = self._conn.execute(
            """
            INSERT INTO studies
                (analyzed_at, initials, birth_year, custom_label, age, sex,
                 exclusions_json, category, description, cells_json, eeg_filename)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.analyzed_at.isoformat(),
                metadata.initials,
                metadata.birth_year,
                metadata.custom_label,
                metadata.age,
                metadata.sex.value,
                exclusions_json,
                result.category.value,
                result.description,
                cells_json,
                eeg_filename,
            ),
        )
        self._conn.commit()
        row_id: int = cur.lastrowid  # type: ignore[assignment]
        return row_id

    def list_recent(self, limit: int = 200) -> list[StudyRecord]:
        """Zwraca rekordy posortowane malejąco po analyzed_at."""
        rows = self._conn.execute(
            """
            SELECT id, analyzed_at, initials, birth_year, custom_label,
                   age, sex, category, description, cells_json, eeg_filename
            FROM studies
            ORDER BY analyzed_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        records: list[StudyRecord] = []
        for row in rows:
            records.append(
                StudyRecord(
                    id=row["id"],
                    analyzed_at=datetime.fromisoformat(row["analyzed_at"]),
                    initials=row["initials"],
                    birth_year=row["birth_year"],
                    custom_label=row["custom_label"],
                    age=row["age"],
                    sex=row["sex"],
                    category=row["category"],
                    description=row["description"],
                    cells_json=row["cells_json"],
                    eeg_filename=row["eeg_filename"],
                )
            )
        return records

    def delete(self, study_id: int) -> None:
        self._conn.execute("DELETE FROM studies WHERE id = ?", (study_id,))
        self._conn.commit()

    def has_any(self) -> bool:
        row = self._conn.execute("SELECT COUNT(*) FROM studies").fetchone()
        return bool(row[0] > 0)

    def is_notice_shown(self) -> bool:
        """Sprawdza flagę 'history_notice_shown' w tabeli settings."""
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = 'history_notice_shown'"
        ).fetchone()
        return row is not None and row["value"] == "1"

    def mark_notice_shown(self) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('history_notice_shown', '1')"
        )
        self._conn.commit()
