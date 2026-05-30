# Project Foundation Implementation Plan

## Overview

F-01 tworzy szkielet aplikacji desktopowej NeuroFlag: usuwa prototyp FastAPI, definiuje typy domenowe będące kontraktem całego projektu, loader norm z walidacją schematu i obsługą PyInstaller, stub wejścia CTk z `--smoke-test`, oraz porządkuje testy. `pyproject.toml` z przypiętymi zależnościami i `norms.json` z 10 normami są już gotowe — ten plan ich nie modyfikuje.

## Current State Analysis

Prototyp FastAPI zajmuje `app/main.py` (jeden plik, ~120 linii). Brak katalogu `app/domain/`. Brak `app/ui/`. Testy w `tests/test_app_endpoints.py` i `tests/test_imports.py` są powiązane z FastAPI i starymi zależnościami (fastapi, pandas, sklearn). CI (ruff, mypy --strict, pip-audit, pytest, Windows PyInstaller build) jest w pełni skonfigurowane i musi przejść po tym planie.

`norms.json` istnieje w root projektu i zawiera kompletną bazę: 10 kombinacji norm (Średnia Z i K), zakresy pasm (Delta 0,5–4 Hz, Theta 4–8 Hz, Beta1 15–18 Hz, Beta2 18–25 Hz), `power_line_frequency: 50`, `recommendation_threshold: 3`.

`neuroflag.spec` wskazuje na `app/main.py` jako punkt wejścia — ten plik musi pozostać po zmianie nazwy i lokalizacji.

### Key Discoveries:

- `pyproject.toml:10-17` — zależności przypięte (customtkinter==5.2.2, mne==1.8.0, scipy==1.14.1, numpy==2.2.0, reportlab==4.2.5, mypy==1.13.0); FastAPI/uvicorn są tylko w `[dev]` — nie trzeba usuwać z prod deps
- `pyproject.toml:37-40` — `[tool.mypy] strict = true` — wszystkie nowe pliki muszą przejść `mypy app/ --strict`
- `neuroflag.spec:109-110` — `Analysis([str(ROOT / "app" / "main.py")])` — entry point musi pozostać na tej ścieżce
- `neuroflag.spec:65-66` — `norms.json` bundlowany do root `.exe` przez `(str(ROOT / "norms.json"), ".")`
- `.github/workflows/python-app.yml:86-88` — `--smoke-test` wywoływany na zbudowanym `.exe`; `app/main.py` musi obsługiwać ten argument
- `tests/test_app_endpoints.py:1-6` — importuje `fastapi.testclient` i `app.main.app` (FastAPI app object) — do usunięcia
- `tests/test_imports.py:1-5` — importuje pandas i sklearn, które nie są prod deps — do przepisania
- Brak `tests/unit/` katalogu — tworzyć od zera

## Desired End State

Po ukończeniu F-01:
- `app/domain/types.py` zawiera kompletne typy domenowe z adnotacjami (`ExclusionDiagnosis`, `CellColor`, `ScreeningCategory`, `PatientMetadata`, `CellResult`, `AnalysisResult`, `NormsConfig`) — każdy przyszły moduł importuje stąd, nie tworzy ad hoc
- `app/domain/norms.py` wczytuje i waliduje `norms.json`; rzuca `NormsLoadError` dla każdego naruszenia schematu; `resolve_norms_path()` działa zarówno w trybie dev jak i PyInstaller
- `app/main.py` to czysty stub desktopowy: `--smoke-test` kończy `sys.exit(0)` po poprawnym załadowaniu norm; normalny start otwiera minimalne okno CTk
- `pytest -q` przechodzi bez błędów; `mypy app/ --strict` przechodzi; `ruff check app/` przechodzi
- `tests/test_app_endpoints.py` nie istnieje; `tests/unit/test_deps.py`, `tests/unit/test_types.py`, `tests/unit/test_norms.py` istnieją i przechodzą

Weryfikacja: `pytest -q` + `mypy app/ --strict --ignore-missing-imports` + `ruff check app/` — wszystkie green na Ubuntu CI oraz lokalnie.

### Key Discoveries:

- Kontrakty typów (szczególnie `AnalysisResult` i `NormsConfig`) muszą być stabilne przed startem S-01/S-02 — zmiana sygnatur po ich implementacji generuje falę poprawek
- `mypy --strict` wymaga `from __future__ import annotations` i pełnych adnotacji na wszystkich granicach publicznych

## What We're NOT Doing

- Nie tworzymy żadnego widoku UI (`app/ui/`) — to zakres S-01
- Nie implementujemy pipeline EEG (`app/domain/pipeline.py`) ani algorytmu (`app/domain/algorithm.py`) — to S-02
- Nie generujemy raportu PDF — to S-03
- Nie modyfikujemy `norms.json`, `pyproject.toml`, `neuroflag.spec`, CI — są już poprawne
- Nie implementujemy hasła startowego (FR-009) — spoza MVP w `roadmap.md § Parked`
- Nie dodajemy logowania ani obserwability — `app/` nie ma logging library; zostaje tak do S-01+

## Implementation Approach

Nowy kod trafia do `app/domain/` (logika domenowa) zgodnie z AGENTS.md. Kolejność: najpierw typy (kontrakt), potem norms.py (korzysta z typów), potem main.py (korzysta z obu). Stary `app/main.py` jest zastępowany — nie przenoszone z niego żadne fragmenty kodu.

## Critical Implementation Details

- **PyInstaller path resolution** — `sys._MEIPASS` istnieje tylko w spakowanym bundlu; w trybie dev `sys._MEIPASS` nie istnieje. `resolve_norms_path()` musi używać `getattr(sys, '_MEIPASS', None)` i fallbackować na `Path(__file__).parent.parent.parent` (root projektu, gdzie leży `norms.json`).
- **mypy strict + dataclass** — przy `strict = true`, pola dataclass muszą mieć explicitne typy; `field(default_factory=frozenset)` wymaga `default_factory=frozenset` z importem `dataclasses.field`.
- **CTkApp w --smoke-test** — `customtkinter.CTk()` próbuje otworzyć okno, co zawiesza headless CI. Obsługa `--smoke-test` musi sprawdzić argument PRZED wywołaniem `ctk.CTk()` i zakończyć `sys.exit(0)`.

---

## Phase 1: Typy domenowe

### Overview

Tworzy `app/domain/__init__.py` i `app/domain/types.py` z pełnymi, stabilnymi typami domenowymi. To kontrakt całego projektu — każdy przyszły moduł (norms.py, pipeline.py, algorithm.py, widoki UI, PDF) importuje stąd.

### Changes Required:

#### 1. Pakiet domain

**File**: `app/domain/__init__.py`

**Intent**: Zainicjować `app/domain` jako pakiet Python; pusty plik.

**Contract**: Plik pusty (lub `# app/domain package`). Wymagany przez Python żeby `from app.domain.types import ...` działało.

#### 2. Typy domenowe

**File**: `app/domain/types.py`

**Intent**: Zdefiniować wszystkie typy domenowe jako dataclasses i Enum-y, z adnotacjami typów i `from __future__ import annotations`. To jedyne miejsce gdzie powstają te typy — żaden inny moduł nie definiuje ich ponownie.

**Contract**:

```python
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

class ExclusionDiagnosis(Enum):
    BRAIN_INJURY = "brain_injury"
    INTELLECTUAL_DISABILITY = "intellectual_disability"
    EPILEPSY = "epilepsy"

class CellColor(Enum):
    RED = "red"       # a ≤ mean_z
    YELLOW = "yellow" # mean_z < a < mean_k
    GREEN = "green"   # a ≥ mean_k

class ScreeningCategory(Enum):
    WSKAZANIE = "Wskazanie do dalszej diagnozy"
    OBSERWACJA = "Uważna obserwacja"
    BRAK = "Brak wskazań"

@dataclass(frozen=True)
class PatientMetadata:
    age: int               # 6–10
    sex: str               # "Z" | "M"
    exclusions: frozenset[ExclusionDiagnosis] = field(default_factory=frozenset)
    def is_excluded(self) -> bool: ...

@dataclass(frozen=True)
class CellResult:
    id: int                # 1–10, zgodnie z norms.json
    channel: str           # "C3" | "O1"
    task: str              # "OO" | "OZ" | "ZP"
    band: str              # "Delta" | "Theta" | "Beta1" | "Beta2"
    color: CellColor

@dataclass(frozen=True)
class AnalysisResult:
    cells: tuple[CellResult, ...]   # dokładnie 10 elementów
    category: ScreeningCategory
    description: str                # krótki opis kategorii po polsku
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
    norms: tuple[NormEntry, ...]    # dokładnie 10 elementów
```

Użycie `frozen=True` zapobiega przypadkowej mutacji tych obiektów przekazywanych przez warstwy. `tuple` zamiast `list` dla `cells` i `norms` — zgodne z `frozen=True`.

### Success Criteria:

#### Automated Verification:

- `mypy app/domain/types.py --strict --ignore-missing-imports` — czyste wyjście (0 błędów)
- `ruff check app/domain/types.py` — czyste wyjście

#### Manual Verification:

- Importy działają: `from app.domain.types import PatientMetadata, AnalysisResult, NormsConfig` bez błędu
- Instancjacja w REPL: `PatientMetadata(age=8, sex="Z")` zwraca obiekt bez błędu; `.is_excluded()` zwraca `False`

**Implementation Note**: Po ukończeniu tej fazy i przejściu automated verification, poczekaj na ręczne potwierdzenie przed przejściem do fazy 2.

---

## Phase 2: Loader norm

### Overview

Tworzy `app/domain/norms.py` z `NormsLoadError`, `resolve_norms_path()` i `load()`. Obsługuje zarówno tryb dev jak i PyInstaller (`sys._MEIPASS`). Waliduje każde wymagane pole `norms.json`.

### Changes Required:

#### 1. Loader norm

**File**: `app/domain/norms.py`

**Intent**: Wczytać `norms.json` z dysku, zwalidować schemat i zwrócić `NormsConfig`. Rzucić `NormsLoadError` dla każdego naruszenia — brakujące pola, zły typ, błędna liczba norm, nieznane pasmo.

**Contract**:

```python
from __future__ import annotations
import sys
from pathlib import Path
from app.domain.types import NormsConfig, NormEntry, BandRange

REQUIRED_NORM_COUNT = 10
VALID_BANDS = frozenset({"Delta", "Theta", "Beta1", "Beta2"})

class NormsLoadError(Exception): ...

def resolve_norms_path() -> Path:
    base = Path(getattr(sys, "_MEIPASS", None) or Path(__file__).parent.parent.parent)
    return base / "norms.json"

def load(path: Path | None = None) -> NormsConfig: ...
```

`load()` przyjmuje opcjonalny `path` (dla testów z fixture JSON); gdy `None` — używa `resolve_norms_path()`. Walidacja: sprawdza obecność kluczy `version`, `power_line_frequency`, `recommendation_threshold`, `band_ranges`, `norms`; sprawdza czy `len(norms) == 10`; sprawdza każde `NormEntry` (wymagane pola: `id`, `channel`, `task`, `band`, `mean_z`, `mean_k`); sprawdza czy `band` należy do `VALID_BANDS`.

### Success Criteria:

#### Automated Verification:

- `mypy app/domain/norms.py --strict --ignore-missing-imports` — 0 błędów
- `ruff check app/domain/norms.py` — 0 błędów
- `pytest tests/unit/test_norms.py -q` — wszystkie testy zielone

#### Manual Verification:

- `python -c "from app.domain import norms; c = norms.load(); print(c.version, len(c.norms))"` wypisuje `1 10`

**Implementation Note**: Po ukończeniu tej fazy i przejściu automated verification, poczekaj na ręczne potwierdzenie przed przejściem do fazy 3.

---

## Phase 3: Nowy app/main.py (desktop stub)

### Overview

Zastępuje prototyp FastAPI w `app/main.py` czystym stubem desktopowym. Parsuje `--smoke-test` PRZED inicjalizacją CTk. Wczytuje `NormsConfig` i łapie `NormsLoadError`. Otwiera minimalne okno CTk jako placeholder dla S-01.

### Changes Required:

#### 1. Nowy entry point

**File**: `app/main.py`

**Intent**: Zastąpić prototyp FastAPI stubem który: (1) kończy `sys.exit(0)` dla `--smoke-test` po udanym załadowaniu norm, (2) dla normalnego startu inicjalizuje CTk i otwiera okno-placeholder "NeuroFlag — uruchamianie...".

**Contract**:

```python
from __future__ import annotations
import sys
import customtkinter as ctk
from app.domain import norms
from app.domain.norms import NormsLoadError

def main() -> None:
    smoke_test = "--smoke-test" in sys.argv
    try:
        _config = norms.load()
    except NormsLoadError as exc:
        sys.exit(f"Błąd ładowania norm: {exc}")
    if smoke_test:
        sys.exit(0)
    app = ctk.CTk()
    app.title("NeuroFlag")
    app.geometry("800x600")
    app.mainloop()

if __name__ == "__main__":
    main()
```

Funkcja `main()` jest publiczna (używana przez `neuroflag.spec` jako entry point). Żadne importy FastAPI/uvicorn nie pozostają.

### Success Criteria:

#### Automated Verification:

- `mypy app/main.py --strict --ignore-missing-imports` — 0 błędów
- `ruff check app/main.py` — 0 błędów
- `pytest -q` — wszystkie testy przechodzą (w tym nowe testy domenowe)

#### Manual Verification:

- `python app/main.py --smoke-test` kończy bez błędu (exit code 0)
- `python app/main.py` otwiera okno "NeuroFlag" 800×600 i nie crashuje

**Implementation Note**: Po ukończeniu tej fazy i przejściu automated verification, poczekaj na ręczne potwierdzenie przed przejściem do fazy 4.

---

## Phase 4: Testy i porządki

### Overview

Usuwa stare testy FastAPI. Tworzy `tests/unit/` z trzema plikami: `test_deps.py` (dymny test importów prod), `test_types.py` (instancjacja typów domenowych + `is_excluded()`), `test_norms.py` (poprawne ładowanie + wszystkie ścieżki `NormsLoadError`).

### Changes Required:

#### 1. Usunięcie starych testów

**File**: `tests/test_app_endpoints.py`

**Intent**: Usunąć plik — importuje `fastapi.testclient` i `app.main.app` (FastAPI app object) które nie istnieją po zmianie `app/main.py`.

**Contract**: Plik usunięty z systemu plików.

#### 2. Pakiet tests/unit

**File**: `tests/unit/__init__.py`

**Intent**: Zainicjować `tests/unit/` jako pakiet Python. Pusty plik.

**Contract**: Plik pusty.

#### 3. Test importów prod deps

**File**: `tests/unit/test_deps.py`

**Intent**: Zastąpić `tests/test_imports.py` testem który importuje tylko prod dependencies (mne, numpy, scipy, reportlab) i sprawdza ich wersje; usuwa pandas i sklearn które nie są prod deps. Test `customtkinter` jest oddzielną funkcją guarded per-platform.

**Contract**: Dwie funkcje: `test_prod_deps_importable()` sprawdzająca `import mne`, `import numpy`, `import scipy`, `import reportlab` z asercją że `__version__` jest stringiem; `test_customtkinter_importable()` opatrzona `@pytest.mark.skipif(sys.platform != "win32", reason="customtkinter wymaga Tcl/Tk; weryfikowane przez Windows smoke-test")` — import customtkinter nie jest wymuszony na headless Ubuntu. Stary plik `tests/test_imports.py` usunięty.

#### 4. Test typów domenowych

**File**: `tests/unit/test_types.py`

**Intent**: Przetestować instancjację wszystkich dataclass-ów i metody pomocnicze; zweryfikować niezmienność (`frozen=True`); zweryfikować `is_excluded()` dla różnych kombinacji.

**Contract**: Testy pokrywają: `PatientMetadata` bez wykluczeń (`is_excluded() == False`), `PatientMetadata` z jednym wykluczeniem (`is_excluded() == True`), `PatientMetadata` z wieloma wykluczeniami, instancjację `CellResult` z każdym `CellColor`, instancjację `AnalysisResult` z 10 komórkami, próbę mutacji `frozen=True` (oczekiwany `FrozenInstanceError`).

#### 5. Test loadera norm

**File**: `tests/unit/test_norms.py`

**Intent**: Przetestować `norms.load()` dla poprawnego `norms.json` oraz wszystkich ścieżek błędów `NormsLoadError` — każde pole wymagane i każdy typ niepoprawności ma własny test.

**Contract**: Testy używają `tmp_path` (pytest fixture) do tworzenia tymczasowych plików JSON. Przypadki: (a) poprawny `norms.json` → zwraca `NormsConfig` z `version==1`, `len(norms)==10`, `band_ranges["Theta"].l_freq==4.0`; (b) brakujące pole `norms` → `NormsLoadError`; (c) brakujące pole `power_line_frequency` → `NormsLoadError`; (d) `len(norms) == 9` (za mało) → `NormsLoadError`; (e) `NormEntry` z brakującym `mean_z` → `NormsLoadError`; (f) `NormEntry` z nieznanym pasmem (`"Alpha"`) → `NormsLoadError`; (g) nieprawidłowy JSON (invalid syntax) → `NormsLoadError`.

### Success Criteria:

#### Automated Verification:

- `pytest -q` — 0 błędów, 0 skipped (dotyczy nowych testów domenowych)
- `mypy app/ --strict --ignore-missing-imports` — 0 błędów w całym katalogu `app/`
- `ruff check app/` — 0 błędów
- `tests/test_app_endpoints.py` nie istnieje
- `tests/test_imports.py` nie istnieje

#### Manual Verification:

- Przejrzyj `tests/unit/test_norms.py` — upewnij się że każda ścieżka `NormsLoadError` ma własny test case
- Uruchom `pytest tests/unit/ -v` — weryfikacja czytelnych nazw testów

**Implementation Note**: Po ukończeniu tej fazy i przejściu automated verification, poczekaj na ręczne potwierdzenie przed zamknięciem F-01.

---

## Testing Strategy

### Unit Tests:

- `tests/unit/test_types.py` — instancjacja wszystkich typów domenowych, `is_excluded()`, niezmienność `frozen=True`
- `tests/unit/test_norms.py` — `norms.load()` happy path + 7 ścieżek `NormsLoadError`
- `tests/unit/test_deps.py` — dymny import prod deps (mne, numpy, scipy, reportlab, customtkinter)

### Integration Tests:

- Brak w F-01 — integracja GUI + pipeline należy do S-01/S-02

### Manual Testing Steps:

1. `python app/main.py --smoke-test` → exit code 0, brak wyjścia na stderr
2. `python app/main.py` → okno "NeuroFlag" 800×600 otwiera się, `Ctrl+C` lub `×` zamyka bez błędu
3. `python -c "from app.domain import norms; c = norms.load(); assert len(c.norms) == 10"` → brak błędu
4. Zepsuj tymczasowo `norms.json` (usuń pole) → `python app/main.py --smoke-test` wypisuje komunikat błędu po polsku i kończy z kodem ≠ 0

## Performance Considerations

Brak — F-01 nie zawiera przetwarzania sygnału ani renderowania UI.

## Migration Notes

Brak danych do migracji — prototyp FastAPI nie miał persystentnych danych. Stare testy (`test_app_endpoints.py`, `test_imports.py`) są usuwane, nie migrowane.

## References

- Roadmap: `context/foundation/roadmap.md` (F-01, sekcja Foundations)
- PRD: `context/foundation/prd.md` (§Business Logic Changes — macierz norm i algorytm trójstanowy)
- Stack assessment: `context/foundation/stack-assessment.md` (Gap 1–3 — typing, structure, deps)
- AGENTS.md — wymagania typowania, struktura katalogów, konwencje MNE-Python
- Spec: `neuroflag.spec:109-110` — entry point `app/main.py`
- CI: `.github/workflows/python-app.yml:86-88` — `--smoke-test` na Windows build

---

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Typy domenowe

#### Automated

- [ ] 1.1 `mypy app/domain/types.py --strict --ignore-missing-imports` — 0 błędów
- [ ] 1.2 `ruff check app/domain/types.py` — 0 błędów

#### Manual

- [ ] 1.3 Importy działają: `from app.domain.types import PatientMetadata, AnalysisResult, NormsConfig` bez błędu
- [ ] 1.4 Instancjacja `PatientMetadata(age=8, sex="Z")` — `.is_excluded()` zwraca `False`

### Phase 2: Loader norm

#### Automated

- [ ] 2.1 `mypy app/domain/norms.py --strict --ignore-missing-imports` — 0 błędów
- [ ] 2.2 `ruff check app/domain/norms.py` — 0 błędów
- [ ] 2.3 `pytest tests/unit/test_norms.py -q` — wszystkie testy zielone

#### Manual

- [ ] 2.4 `python -c "from app.domain import norms; c = norms.load(); print(c.version, len(c.norms))"` wypisuje `1 10`

### Phase 3: Nowy app/main.py (desktop stub)

#### Automated

- [ ] 3.1 `mypy app/main.py --strict --ignore-missing-imports` — 0 błędów
- [ ] 3.2 `ruff check app/main.py` — 0 błędów
- [ ] 3.3 `pytest -q` — wszystkie testy przechodzą

#### Manual

- [ ] 3.4 `python app/main.py --smoke-test` kończy bez błędu (exit code 0)
- [ ] 3.5 `python app/main.py` otwiera okno "NeuroFlag" 800×600 bez crashu

### Phase 4: Testy i porządki

#### Automated

- [ ] 4.1 `pytest -q` — 0 błędów, nowe testy domenowe przechodzą
- [ ] 4.2 `mypy app/ --strict --ignore-missing-imports` — 0 błędów w całym `app/`
- [ ] 4.3 `ruff check app/` — 0 błędów
- [ ] 4.4 `tests/test_app_endpoints.py` nie istnieje; `tests/test_imports.py` nie istnieje

#### Manual

- [ ] 4.5 Przejrzyj `tests/unit/test_norms.py` — każda ścieżka `NormsLoadError` ma własny test case
- [ ] 4.6 `pytest tests/unit/ -v` — czytelne nazwy testów, wszystkie zielone
