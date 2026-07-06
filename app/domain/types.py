from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ExclusionDiagnosis(Enum):
    BRAIN_INJURY = "brain_injury"
    INTELLECTUAL_DISABILITY = "intellectual_disability"
    EPILEPSY = "epilepsy"


class ClinicalDiagnosis(Enum):
    ASD = "asd"
    ADHD = "adhd"
    DEPRESSION_ANXIETY = "depression_anxiety"
    DYSLEXIA = "dyslexia"
    OTHER = "other"


_CLINICAL_LABELS_PL: dict[ClinicalDiagnosis, str] = {
    ClinicalDiagnosis.ASD: "ASD / autyzm",
    ClinicalDiagnosis.ADHD: "ADHD",
    ClinicalDiagnosis.DEPRESSION_ANXIETY: "Depresja lub zaburzenia lękowe",
    ClinicalDiagnosis.DYSLEXIA: "Dysleksja",
    ClinicalDiagnosis.OTHER: "Inne",
}


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
    diagnoses: frozenset[ClinicalDiagnosis] = field(default_factory=frozenset)
    other_diagnosis_note: str | None = None
    initials: str | None = None
    birth_year: str | None = None
    custom_label: str | None = None

    def is_excluded(self) -> bool:
        return len(self.exclusions) > 0


def format_clinical_diagnoses(metadata: PatientMetadata) -> str:
    """Zwraca polskie etykiety diagnoz informacyjnych, rozdzielone przecinkami."""
    if not metadata.diagnoses:
        return ""
    labels: list[str] = []
    for diagnosis in sorted(metadata.diagnoses, key=lambda d: d.value):
        label = _CLINICAL_LABELS_PL[diagnosis]
        if diagnosis is ClinicalDiagnosis.OTHER and metadata.other_diagnosis_note:
            label = f"{label} ({metadata.other_diagnosis_note})"
        labels.append(label)
    return ", ".join(labels)


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
class RecommendationRules:
    indication_min_red: int
    indication_max_green: int
    no_indication_min_green: int
    no_indication_max_red: int


@dataclass(frozen=True)
class CategoryDescriptions:
    wskazanie: str
    obserwacja: str
    brak: str


@dataclass(frozen=True)
class ObservationCategory:
    title: str
    items: tuple[str, ...]


@dataclass(frozen=True)
class ObservationChecklist:
    """Stała sekcja raportu PDF — lista obserwacyjna dla pedagoga/rodzica."""

    title: str
    intro: str
    categories: tuple[ObservationCategory, ...]


@dataclass(frozen=True)
class NormsConfig:
    version: int
    power_line_frequency: float
    band_ranges: dict[str, BandRange]
    norms: tuple[NormEntry, ...]
    recommendation_rules: RecommendationRules
    category_descriptions: CategoryDescriptions
    observation_checklist: ObservationChecklist
