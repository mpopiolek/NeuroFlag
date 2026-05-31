from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ExclusionDiagnosis(Enum):
    BRAIN_INJURY = "brain_injury"
    INTELLECTUAL_DISABILITY = "intellectual_disability"
    EPILEPSY = "epilepsy"


class CellColor(Enum):
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"


class ScreeningCategory(Enum):
    WSKAZANIE = "Wskazanie do dalszej diagnozy"
    OBSERWACJA = "Uważna obserwacja"
    BRAK = "Brak wskazań"


@dataclass(frozen=True)
class PatientMetadata:
    age: int
    sex: str
    exclusions: frozenset[ExclusionDiagnosis] = field(default_factory=frozenset)

    def is_excluded(self) -> bool:
        return len(self.exclusions) > 0


@dataclass(frozen=True)
class CellResult:
    id: int
    channel: str
    task: str
    band: str
    color: CellColor


@dataclass(frozen=True)
class AnalysisResult:
    cells: tuple[CellResult, ...]
    category: ScreeningCategory
    description: str
    analyzed_at: datetime


@dataclass(frozen=True)
class BandRange:
    l_freq: float
    h_freq: float


@dataclass(frozen=True)
class NormEntry:
    id: int
    channel: str
    task: str
    band: str
    mean_z: float
    mean_k: float


@dataclass
class NormsConfig:
    version: int
    power_line_frequency: float
    recommendation_threshold: int
    band_ranges: dict[str, BandRange]
    norms: tuple[NormEntry, ...]
