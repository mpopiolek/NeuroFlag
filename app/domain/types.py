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


class Sex(Enum):
    Z = "Z"
    M = "M"


@dataclass(frozen=True)
class PatientMetadata:
    age: int
    sex: Sex
    exclusions: frozenset[ExclusionDiagnosis] = field(default_factory=frozenset)

    def is_excluded(self) -> bool:
        return len(self.exclusions) > 0


@dataclass(frozen=True)
class CellResult:
    cell_id: int
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

    def __post_init__(self) -> None:
        if len(self.cells) != 10:
            raise ValueError(
                f"AnalysisResult.cells must contain exactly 10 elements, got {len(self.cells)}"
            )


@dataclass(frozen=True)
class BandRange:
    l_freq: float
    h_freq: float


@dataclass(frozen=True)
class NormEntry:
    norm_id: int
    channel: str
    task: str
    band: str
    mean_z: float
    mean_k: float


@dataclass(frozen=True)
class NormsConfig:
    version: int
    power_line_frequency: float
    recommendation_threshold: int
    band_ranges: dict[str, BandRange]
    norms: tuple[NormEntry, ...]
