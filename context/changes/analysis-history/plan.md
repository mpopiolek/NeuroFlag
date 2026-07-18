# Historia badań — lokalna baza SQLite

## Overview

Dodanie lokalnej historii badań przesiewowych do NeuroFlag. Każde zakończone badanie
zapisywane automatycznie do bazy SQLite (`history.db` obok `neuroflag.exe`).
Pedagog widzi listę poprzednich badań (data, identyfikator dziecka, kategoria wynikowa)
i może usuwać rekordy. Funkcja spełnia kryterium CRUD dla certyfikacji MVP
i otwiera drogę do trendów terapeutycznych w v2.0.

**Rozszerzenie (Phase 6):** zbieranie zdiagnozowanych wcześniej schorzeń
psychologiczno-pedagogicznych/medycznych (ASD, ADHD, depresja/lęki, dysleksja, inne)
obok istniejących diagnoz wykluczających. Dane zapisywane lokalnie w `history.db`
i trafiają do raportu PDF — bez wpływu na algorytm przesiewowy w v1.0; fundament
pod rozszerzanie norm i uczenie w v2.0 (FR-010).

## Current State Analysis

- `PatientMetadata` (`app/domain/types.py:31`) — pola identyfikujące dziecko
  (`initials`, `birth_year`, `custom_label`) już zaimplementowane (Phase 2, ekran importu).
  Brak pól na diagnozy informacyjne (ASD, ADHD itd.) — tylko `ExclusionDiagnosis`
  (uraz mózgu, niepełnosprawność intelektualna, padaczka) z blokadą analizy.
  Pipeline i algorytm ignorują metrykę poza wiekiem/płcią — nowe diagnozy można
  dodać bez zmiany wyniku przesiewowego.
- `AppState` (`app/ui/app_window.py:12`) — sesja w RAM, reset przy „Nowe badanie".
  `AppState.metadata` i `AppState.analysis_result` są dostępne w momencie zapisu.
- `AnalysisView._on_done()` (`app/ui/views/analysis.py:143`) — naturalne miejsce
  auto-zapisu: wynik gotowy, `show_view(ResultsGridView)` jeszcze niezwołane.
- `ResultsGridView._on_new_study()` (`app/ui/views/results_grid.py:169`) — reset stanu i
  powrót do `MetadataFormView`. Przycisk „Historia badań" zaimplementowany (Phase 4).
- `HistoryStore` + `history.db` — **zaimplementowane** (fazy 1–5): auto-zapis po analizie,
  `HistoryView`, komunikat RODO, pola identyfikacyjne (`initials`, `birth_year`,
  `custom_label`) na ekranie importu pliku. `AGENTS.md` zaktualizowany.
- `resolve_history_db_path()` (`app/storage/history.py`) — wzorzec lokalizacji pliku obok `.exe`.

## Desired End State

Użytkownik może:
1. Wypełnić opcjonalne pola identyfikujące dziecko w formularzu metryki.
2. Po zakończeniu analizy zobaczyć na ekranie wyników przycisk „Historia badań"
   (widoczny tylko gdy historia zawiera co najmniej jeden rekord).
3. Otworzyć widok historii i zobaczyć listę badań: data, identyfikator dziecka,
   kategoria wynikowa (kolor RAG).
4. Usunąć wybrany rekord po potwierdzeniu.
5. Wrócić do ekranu wyników.
6. *(Phase 6)* Opcjonalnie zaznaczyć wcześniejsze diagnozy (ASD, ADHD, depresja/lęki,
   dysleksja, inne) w formularzu metryki — bez wpływu na wynik przesiewowy.
7. *(Phase 6)* Zdiagnozowane schorzenia zapisywane lokalnie w historii i widoczne w raporcie PDF.

Weryfikacja: po przeprowadzeniu 2 badań lista pokazuje 2 rekordy; po usunięciu jednego —
1 rekord; `history.db` istnieje w folderze aplikacji.
Po Phase 6: rekord z zaznaczonym ADHD ma `diagnoses_json` w bazie; PDF zawiera sekcję diagnoz.

## What We're NOT Doing

- Ładowanie danych dziecka z historii do formularza (prefill) — v2.0.
- Wykresy trendów / porównanie wyników w czasie — v2.0.
- Paginacja listy historii — lista wyświetla max 200 ostatnich rekordów; dla MVP wystarczy.
- Szyfrowanie bazy danych — dane pozostają lokalne, szyfrowanie v2.0.
- Eksport historii (CSV/Excel) — v2.0.
- Wyszukiwanie / filtrowanie historii — v2.0.
- Użycie diagnoz informacyjnych w algorytmie przesiewowym lub segmentacji norm — v2.0.
- Filtrowanie historii po diagnozie — v2.0.

## Implementation Approach

Pięć faz (1–5) **ukończonych**; Phase 6 (diagnozy informacyjne) — pending.
Sekwencja Phase 6: typy domenowe → UI metryki + RODO → storage (`diagnoses_json`) → PDF → testy.

SQLite obsługiwany przez wbudowany moduł `sqlite3` — zero nowych zależności.
Schemat tworzy się przy pierwszym uruchomieniu (`CREATE TABLE IF NOT EXISTS`).

## Critical Implementation Details

- **Lokalizacja DB**: wzorzec identyczny jak `resolve_norms_path()` —
  `Path(sys.executable).parent / "history.db"` dla PyInstaller, projekt root / `history.db`
  dla dev. Nowy `resolve_history_db_path()` w `app/storage/history.py`.
- **Wielowątkowość**: `AnalysisView._analysis_worker` działa w wątku tła; `_on_done`
  jest wywołane przez `self.after(0, ...)` — już w wątku GUI. Zapis SQLite ma być
  wyłącznie w `_on_done` (wątek GUI), nie w workerze. `sqlite3` w trybie
  `check_same_thread=True` (domyślnym) jest tu bezpieczny.
- **Jednorazowy komunikat RODO**: flaga `history_notice_shown` przechowywana w tabeli
  `settings` (klucz/wartość, ta sama baza). Komunikat pokazywany przed pierwszym zapisem
  (przed `store.add()`), blokuje zapis do potwierdzenia przez użytkownika.
- **`cells_json`**: serializacja listy `CellResult` jako JSON-array obiektów
  `{cell_id, channel, task, band, color}`. Deserialization tylko dla v2.0 (trendy);
  w tej wersji lista służy wyłącznie do odtworzenia kategorii/opisu przy podglądzie
  (nierealizowanym w MVP) — można przechowywać jako surowy JSON string.

---

## Phase 1: Warstwa storage — `app/storage/`

### Overview

Nowy moduł `app/storage/` z `HistoryStore` (SQLite CRUD) i `StudyRecord` (dataclass rekordu).
Brak efektów ubocznych — czyste I/O na pliku DB.

### Changes Required:

#### 1. Utwórz `app/storage/__init__.py`

**File**: `app/storage/__init__.py`

**Intent**: Pakiet storage — pusty plik inicjalizujący.

**Contract**: Pusty lub z eksportem `HistoryStore`.

#### 2. Dodaj `app/storage/history.py`

**File**: `app/storage/history.py`

**Intent**: Zdefiniować `StudyRecord` (dataclass rekordu historii) i `HistoryStore`
(klasa zarządzająca połączeniem SQLite i operacjami CRUD).

**Contract**:

```python
@dataclass
class StudyRecord:
    id: int
    analyzed_at: datetime
    initials: str | None
    birth_date: str | None   # format "YYYY-MM-DD" lub wolny tekst
    custom_label: str | None
    age: int
    sex: str             # "Z" | "M"
    category: str        # wartość ScreeningCategory.value
    description: str
    cells_json: str      # surowy JSON string
    eeg_filename: str | None

    @property
    def display_name(self) -> str:
        """Zwraca czytelny identyfikator dziecka dla listy historii."""
        ...
```

`HistoryStore`:
```python
class HistoryStore:
    def __init__(self, db_path: Path) -> None: ...

    def _ensure_schema(self) -> None:
        """CREATE TABLE IF NOT EXISTS studies (...); CREATE TABLE IF NOT EXISTS settings (...);"""

    def add(
        self,
        metadata: PatientMetadata,
        result: AnalysisResult,
        *,
        eeg_path: Path | None = None,
    ) -> int:
        """Wstawia rekord i zwraca nowe id. eeg_path.name zapisywany jako eeg_filename."""

    def list_recent(self, limit: int = 200) -> list[StudyRecord]:
        """Zwraca rekordy posortowane malejąco po analyzed_at."""

    def delete(self, study_id: int) -> None: ...

    def has_any(self) -> bool: ...

    def is_notice_shown(self) -> bool:
        """Sprawdza flagę 'history_notice_shown' w tabeli settings."""

    def mark_notice_shown(self) -> None: ...
```

Schemat SQLite (w `_ensure_schema`):
```sql
CREATE TABLE IF NOT EXISTS studies (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    analyzed_at      TEXT    NOT NULL,
    initials         TEXT,
    birth_date       TEXT,
    custom_label     TEXT,
    age              INTEGER NOT NULL,
    sex              TEXT    NOT NULL,
    exclusions_json  TEXT    NOT NULL,
    category         TEXT    NOT NULL,
    description      TEXT    NOT NULL,
    cells_json       TEXT    NOT NULL,
    eeg_filename     TEXT
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

#### 3. Dodaj `resolve_history_db_path()` w `app/storage/history.py`

**File**: `app/storage/history.py`

**Intent**: Zwrócić ścieżkę do `history.db` spójną z `resolve_norms_path()` —
obok `.exe` w dystrybucji, w root projektu w dev.

**Contract**: Sygnatura `def resolve_history_db_path() -> Path:` — wzorzec
identyczny z `app/domain/norms.py:127`.

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/test_history.py -q` — testy z Phase 5 przechodzą
- `mypy app/storage/history.py --strict` bez błędów
- `ruff check app/storage/history.py` bez błędów

#### Manual Verification:

- `python -c "from app.storage.history import HistoryStore, resolve_history_db_path; s = HistoryStore(resolve_history_db_path()); print(s.has_any())"` drukuje `False`

**Implementation Note**: Po zakończeniu tej fazy i przejściu automatycznych weryfikacji,
zatrzymaj się na ręczne potwierdzenie przed przejściem do Phase 2.

---

## Phase 2: Typy domenowe + formularz metryki

### Overview

Rozszerzenie `PatientMetadata` o trzy opcjonalne pola identyfikujące dziecko
oraz dodanie odpowiadających im pól do formularza UI.

### Changes Required:

#### 1. Dodaj opcjonalne pola do `PatientMetadata`

**File**: `app/domain/types.py:31`

**Intent**: Umożliwić przechowywanie inicjałów, daty urodzenia i własnej etykiety
w ramach istniejącego obiektu metryki bez wpływu na logikę pipeline/algorytmu.

**Contract**: Rozszerz dataclass o:
```python
initials: str | None = None
birth_date: str | None = None   # wolny tekst, np. "2018" lub "2018-05"
custom_label: str | None = None
```
Pola opcjonalne z defaultem `None` — istniejące testy i konstruktory `PatientMetadata(age, sex)`
nadal działają bez zmian.

#### 2. Dodaj pola UI do `MetadataFormView`

**File**: `app/ui/views/metadata_form.py`

**Intent**: Wyświetlić sekcję „Identyfikacja dziecka (opcjonalnie)" z trzema
polami tekstowymi: Inicjały, Data urodzenia, Własna etykieta. Sekcja oznaczona
jako opcjonalna — formularz przechodzi do następnego ekranu niezależnie od tego,
czy pola są wypełnione.

**Contract**: Trzy `CTkEntry` poniżej istniejących pól diagnozy wykluczającej.
`_on_next()` odczytuje ich wartości (`entry.get().strip() or None`) i przekazuje
do `PatientMetadata(age, sex, exclusions, initials=..., birth_date=..., custom_label=...)`.
`_restore_from_state()` przywraca wartości przy powrocie do formularza.

### Success Criteria:

#### Automated Verification:

- `mypy app/domain/types.py --strict` bez błędów
- `mypy app/ui/views/metadata_form.py --strict` bez błędów
- `python -m pytest tests/unit/test_types.py -q` bez regresji

#### Manual Verification:

- Formularz pokazuje sekcję „Identyfikacja dziecka (opcjonalnie)" z 3 polami
- Formularz przechodzi dalej gdy pola są puste (opcjonalne)
- Formularz przechodzi dalej gdy pola są wypełnione

**Implementation Note**: Po zakończeniu tej fazy zatrzymaj się na potwierdzenie.

---

## Phase 3: Auto-zapis po analizie

### Overview

Hook w `AnalysisView._on_done()`: przy pomyślnym wyniku zapisuje rekord do `HistoryStore`.
Przed pierwszym zapisem pokazuje jednorazowy komunikat RODO.

### Changes Required:

#### 1. Wstrzyknij `HistoryStore` do `AppWindow` / `AppState`

**File**: `app/ui/app_window.py`

**Intent**: Udostępnić pojedynczą instancję `HistoryStore` wszystkim widokom
bez tworzenia wielokrotnych połączeń z DB.

**Contract**: Dodaj pole do `AppState`:
```python
history_store: HistoryStore | None = None
```
Inicjuj w `AppWindow.__init__()` po skonstruowaniu `self._state`:
```python
from app.storage.history import HistoryStore, resolve_history_db_path
self._state.history_store = HistoryStore(resolve_history_db_path())
```
W widokach korzystaj z `assert app_state.history_store is not None` przed użyciem
(store jest zawsze ustawiony przez AppWindow zanim jakikolwiek widok zostanie wyświetlony).

#### 2. Auto-zapis w `AnalysisView._on_done()`

**File**: `app/ui/views/analysis.py:143`

**Intent**: Po pomyślnej analizie (gdy `result is not None` i `error is None`):
sprawdzić flagę RODO, opcjonalnie pokazać komunikat, zapisać rekord do historii.

**Contract**: Przed `self._app_state.analysis_result = result` wywołaj:
```python
store = self._app_state.history_store
if result is not None and not store.is_notice_shown():
    _show_rodo_notice()        # CTkMessagebox lub tkinter.messagebox
    store.mark_notice_shown()
if result is not None:
    store.add(self._app_state.metadata, result, eeg_path=self._app_state.eeg_path)
```
Komunikat RODO: jednoprzyciskowe `tkinter.messagebox.showinfo` (tylko OK, brak
opcji odrzucenia) z treścią: „Badanie zostało zapisane w lokalnej historii na tym
urządzeniu. Historia zawiera inicjały i datę urodzenia dziecka.
Dane nie opuszczają urządzenia." Po kliknięciu OK — wywołaj `store.mark_notice_shown()`
i kontynuuj normalny flow (store.add, show_view). Nie używaj `askyesno` ani
`askokcancel` — komunikat jest informacyjny, nie wymaga decyzji użytkownika.
Błąd zapisu do SQLite (`Exception`) — zaloguj do `sys.stderr`, nie przerywaj flow
(wynik wyświetlany niezależnie od powodzenia zapisu).

### Success Criteria:

#### Automated Verification:

- `mypy app/ui/app_window.py --strict` bez błędów
- `mypy app/ui/views/analysis.py --strict` bez błędów

#### Manual Verification:

- Po pierwszej analizie pojawia się komunikat RODO (tylko raz)
- `history.db` powstaje w folderze projektu / obok `.exe`
- `HistoryStore(resolve_history_db_path()).list_recent()` zwraca 1 rekord po analizie

**Implementation Note**: Po zakończeniu tej fazy zatrzymaj się na potwierdzenie.

---

## Phase 4: `HistoryView` + przycisk w wynikach

### Overview

Nowy widok listy historii i przycisk „Historia badań" w `ResultsGridView`
(widoczny tylko gdy `store.has_any()`).

### Changes Required:

#### 1. Utwórz `app/ui/views/history.py`

**File**: `app/ui/views/history.py`

**Intent**: Widok listy historii badań z nagłówkiem, scrollowalną listą rekordów
i przyciskiem powrotu. Każdy wiersz: data + display_name + kategoria (kolor RAG)
+ przycisk „Usuń" z potwierdzeniem (`CTkMessagebox` lub `tkinter.messagebox.askyesno`).

**Contract**: Klasa `HistoryView(ctk.CTkFrame)`. Konstruktor:
`__init__(master, app_window, app_state, **kwargs)` — zgodne z wzorcem widoków.
Wiersz kategorii: kolor tła identyczny z `RAG_COLORS` z `app/ui/components/rag_colors.py`.
Powrót: `show_view(ResultsGridView)` — widok wyników jest poprzednim ekranem.
Usunięcie: `store.delete(record.id)` → odśwież listę w miejscu (bez `show_view`).

#### 2. Dodaj przycisk „Historia badań" do `ResultsGridView`

**File**: `app/ui/views/results_grid.py`

**Intent**: Pokazać przycisk „Historia badań" gdy historia zawiera minimum 1 rekord,
dający dostęp do `HistoryView`.

**Contract**: W `__init__()`, po zbudowaniu przycisków „Nowe badanie" / „Zapisz PDF":
```python
if self._app_state.history_store.has_any():
    CTkButton(..., text="Historia badań", command=self._on_history)
```
`_on_history()` → `self._app_window.show_view(HistoryView)`.

### Success Criteria:

#### Automated Verification:

- `mypy app/ui/views/history.py --strict` bez błędów
- `mypy app/ui/views/results_grid.py --strict` bez błędów
- `ruff check app/ui/views/history.py` bez błędów

#### Manual Verification:

- Przycisk „Historia badań" widoczny na ekranie wyników po przeprowadzeniu badania
- Kliknięcie otwiera widok z listą badań
- Wiersz pokazuje: datę, identyfikator dziecka (`display_name`), kategorię z kolorem RAG
- Usunięcie rekordu po potwierdzeniu usuwa go z listy i bazy
- Przycisk powrotu wraca do ekranu wyników

**Implementation Note**: Po zakończeniu tej fazy zatrzymaj się na potwierdzenie.

---

## Phase 5: Testy jednostkowe

### Overview

Testy dla `HistoryStore` pokrywające wszystkie operacje CRUD i serializację `StudyRecord`.

### Changes Required:

#### 1. Zaktualizuj `AGENTS.md`

**File**: `AGENTS.md`

**Intent**: Usunąć nieaktualny wpis „nie ma bazy danych" i dodać krótką notatkę
o `history.db` i module `app/storage/`.

**Contract**: W sekcji opisującej architekturę zastąp wzmiankę „nie ma bazy danych"
zdaniem „Lokalna baza SQLite (`history.db`) obok `neuroflag.exe` — przechowuje
historię badań; obsługiwana przez `app/storage/history.py`."

#### 2. Utwórz `tests/unit/test_history.py`

**File**: `tests/unit/test_history.py`

**Intent**: Pokryć ścieżki happy path i graniczne `HistoryStore`.

**Contract**: Używaj `tmp_path` z pytest jako DB path — izolacja między testami.
Testy do zaimplementowania:

- `test_add_returns_id` — `store.add(metadata, result)` zwraca int > 0
- `test_has_any_false_when_empty` — pusta baza → `False`
- `test_has_any_true_after_add` — po add → `True`
- `test_list_recent_empty` — pusta baza → `[]`
- `test_list_recent_returns_added_record` — po add → lista z 1 elementem; pola zgodne z wejściem
- `test_list_recent_sorted_descending` — dwa rekordy z różnym `analyzed_at` → nowszy pierwszy
- `test_delete_removes_record` — add → delete(id) → `list_recent()` puste
- `test_delete_nonexistent_no_error` — `delete(9999)` nie rzuca
- `test_notice_flag_initially_false` — `is_notice_shown()` → False
- `test_mark_notice_shown` — `mark_notice_shown()` → `is_notice_shown()` → True
- `test_schema_created_on_init` — init tworzy plik DB i tabele bez błędu
- `test_display_name_with_initials` — `StudyRecord` z inicjałami → `display_name` zawiera inicjały
- `test_display_name_fallback` — brak inicjałów/daty → `display_name` nie pusty (fallback do daty badania)

Fixture pomocnicze:
```python
@pytest.fixture
def store(tmp_path):
    return HistoryStore(tmp_path / "test.db")

@pytest.fixture
def sample_metadata():
    return PatientMetadata(age=8, sex=Sex.Z, initials="AN", birth_date="2018")

@pytest.fixture
def sample_result():
    # Użyj realnego norms.json — wzorzec z test_algorithm.py:test_classify_with_real_norms_config
    from app.domain.algorithm import classify
    from app.domain.norms import load, resolve_norms_path
    cfg = load(resolve_norms_path())
    return classify([15.0] * 10, cfg)  # wszystkie YELLOW → OBSERWACJA
```

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/test_history.py -v` — 13 testów przechodzi
- `python -m pytest tests/unit/ -q` — brak regresji w istniejących testach
- `mypy tests/unit/test_history.py --strict` bez błędów

#### Manual Verification:

- Wszystkie 13 testów zielone lokalnie

**Implementation Note**: Po zakończeniu tej fazy zatrzymaj się na potwierdzenie.

---

## Phase 6: Diagnozy informacyjne w metryce (FR-010)

### Overview

Rozszerzenie metryki dziecka o opcjonalne, wcześniej postawione diagnozy
psychologiczno-pedagogiczne/medyczne. Oddzielone od istniejących diagnoz wykluczających
(uraz mózgu, niepełnosprawność intelektualna, padaczka), które nadal blokują analizę.
Zbierane dane służą wyłącznie do zapisu lokalnego i raportu PDF w v1.0; w v2.0 umożliwią
rozszerzanie norm i analizę trendów per grupa kliniczna.

### Changes Required:

#### 1. Dodaj enum `ClinicalDiagnosis` i pola w `PatientMetadata`

**File**: `app/domain/types.py`

**Intent**: Typować diagnozy informacyjne oddzielnie od `ExclusionDiagnosis`;
zachować kompatybilność wsteczną istniejących konstruktorów.

**Contract**:
```python
class ClinicalDiagnosis(Enum):
    ASD = "asd"                          # ASD / autyzm
    ADHD = "adhd"
    DEPRESSION_ANXIETY = "depression_anxiety"  # depresja / zaburzenia lękowe
    DYSLEXIA = "dyslexia"
    OTHER = "other"
```

Rozszerz `PatientMetadata`:
```python
diagnoses: frozenset[ClinicalDiagnosis] = field(default_factory=frozenset)
other_diagnosis_note: str | None = None  # wymagane gdy OTHER ∈ diagnoses
```

Eksportuj `ClinicalDiagnosis` z `app/domain/__init__.py`.

Dodaj helper w `app/domain/types.py` (lub `app/domain/clinical_labels.py` jeśli
plik rośnie):
```python
_CLINICAL_LABELS_PL: dict[ClinicalDiagnosis, str] = {
    ClinicalDiagnosis.ASD: "ASD / autyzm",
    ClinicalDiagnosis.ADHD: "ADHD",
    ClinicalDiagnosis.DEPRESSION_ANXIETY: "Depresja lub zaburzenia lękowe",
    ClinicalDiagnosis.DYSLEXIA: "Dysleksja",
    ClinicalDiagnosis.OTHER: "Inne",
}

def format_clinical_diagnoses(metadata: PatientMetadata) -> str:
    """Zwraca polskie etykiety diagnoz informacyjnych, rozdzielone przecinkami."""
    ...
```
PDF (`pdf_generator.py`) i testy importują `format_clinical_diagnoses` — jedno
źródło prawdy dla etykiet PL.

#### 2. Sekcja UI w `MetadataFormView`

**File**: `app/ui/views/metadata_form.py`

**Intent**: Umożliwić pedagogowi zaznaczenie wcześniejszych diagnoz bez blokady analizy.

**Contract**:
- Nowa sekcja **„Zdiagnozowane wcześniej (opcjonalnie)"** między płcią a diagnozami
  wykluczającymi.
- Checkboxy (wielokrotny wybór): ASD / autyzm, ADHD, Depresja lub zaburzenia lękowe,
  Dysleksja, Inne.
- Gdy zaznaczono „Inne" — pojawia się `CTkEntry` na krótki opis (max ~100 znaków,
  `strip() or None`).
- Sekcja opcjonalna — puste checkboxy nie blokują „Dalej →".
- Istniejąca sekcja „Diagnozy wykluczające" bez zmian (blokada analizy).
- `_on_next()` przekazuje `diagnoses` i `other_diagnosis_note` do `PatientMetadata`.
- `_restore_from_state()` przywraca checkboxy i pole „Inne".
- Infobox RODO: doprecyzować, że diagnozy zapisywane są lokalnie (jak inicjały)
  i nie wpływają na wynik przesiewowy.

#### 2b. Aktualizacja komunikatu RODO przy pierwszym zapisie

**File**: `app/ui/views/analysis.py`

**Intent**: Jednorazowy dialog przy pierwszym zapisie do historii musi wymieniać
pełny zakres zapisywanych danych osobowych — w tym opcjonalne diagnozy (art. 9).

**Contract**: Rozszerz `_RODO_NOTICE` o wzmiankę o diagnozach, np.:
„Historia zawiera inicjały, rok urodzenia oraz — jeśli podane — wcześniejsze
diagnozy dziecka. Dane nie opuszczają urządzenia."
Bez zmiany mechanizmu `is_notice_shown()` / `mark_notice_shown()`.

#### 3. Kolumna `diagnoses_json` w `HistoryStore`

**File**: `app/storage/history.py`

**Intent**: Persystować diagnozy informacyjne obok istniejącego `exclusions_json`.

**Contract**:
- Migracja schematu w `_ensure_schema()`:
  ```sql
  ALTER TABLE studies ADD COLUMN diagnoses_json TEXT NOT NULL
      DEFAULT '{"diagnoses":[],"other_note":null}'
  ```
  (obsłużyć `sqlite3.OperationalError` gdy kolumna już istnieje — idempotentna migracja).
- `add()` serializuje ten sam kształt:
  ```python
  diagnoses_json = json.dumps({
      "diagnoses": [d.value for d in metadata.diagnoses],
      "other_note": metadata.other_diagnosis_note,
  })
  ```
  Pusty zestaw → `{"diagnoses":[],"other_note":null}` (nigdy goły `[]`).
- `exclusions_json` bez zmian — nadal zapisuje wykluczenia (puste `[]` gdy brak).
- `StudyRecord` — opcjonalnie pole `diagnoses_json: str` (odczyt przez helper
  `format_clinical_diagnoses` po deserializacji, gdy potrzebny w v2.0).

#### 4. Raport PDF — sekcja diagnoz

**File**: `app/reports/pdf_generator.py`

**Intent**: Spełnić FR-010 — metryka dziecka w raporcie zawiera zdiagnozowane schorzenia.

**Contract**:
- Pod linią wiek/płeć dodaj wiersz „Diagnozy:" gdy `metadata.diagnoses` niepuste.
- Użyj `format_clinical_diagnoses(metadata)` z domain — nie duplikuj mapowania w PDF.
- Dla `OTHER` helper dołącza `other_diagnosis_note` w nawiasie.
- Gdy brak diagnoz — wiersz pominięty (nie drukuj „Brak").
- **Nie** wyświetlaj diagnoz wykluczających w PDF (analiza dla nich nie dochodzi do skutku).

#### 5. Testy jednostkowe

**Files**: `tests/unit/test_types.py`, `tests/unit/test_history.py`,
`tests/unit/test_pdf_generator.py`

**Intent**: Pokryć serializację, domyślne wartości i render PDF.

**Contract** — nowe testy:
- `test_patient_metadata_empty_diagnoses` — domyślnie `frozenset()`
- `test_patient_metadata_with_diagnoses` — konstruktor z `ClinicalDiagnosis.ADHD`
- `test_add_persists_diagnoses_json` — `store.add()` zapisuje JSON z diagnozami
- `test_schema_migration_adds_diagnoses_column` — init na istniejącej DB dodaje kolumnę
- `test_pdf_includes_diagnoses_when_present` — PDF zawiera etykietę ADHD
- `test_pdf_omits_diagnoses_when_empty` — PDF bez wiersza „Diagnozy"

### Success Criteria:

#### Automated Verification:

- `mypy app/domain/types.py app/storage/history.py app/ui/views/metadata_form.py app/ui/views/analysis.py app/reports/pdf_generator.py --strict` bez błędów
- `python -m pytest tests/unit/test_types.py tests/unit/test_history.py tests/unit/test_pdf_generator.py -q` bez regresji
- `ruff check app/domain/types.py app/storage/history.py app/ui/views/metadata_form.py` bez błędów

#### Manual Verification:

- Formularz metryki pokazuje sekcję „Zdiagnozowane wcześniej (opcjonalnie)" z 5 checkboxami
- Zaznaczenie ADHD + przejście dalej nie blokuje analizy
- Po analizie `diagnoses_json` w `history.db` zawiera `"adhd"`
- Raport PDF zawiera wiersz „Diagnozy: ADHD"
- Zaznaczenie urazu mózgu nadal blokuje „Dalej →" (regresja wykluczeń)

**Implementation Note**: Po zakończeniu tej fazy zatrzymaj się na potwierdzenie.

---

## Testing Strategy

### Unit Tests:

- `test_add_returns_id`, `test_has_any_*`, `test_list_recent_*`, `test_delete_*`
- `test_notice_flag_*`
- `test_display_name_*`

### Manual Testing Steps:

1. Uruchom aplikację, wypełnij metrykę z inicjałami i datą urodzenia
2. Wczytaj plik EEG i przeprowadź analizę
3. Sprawdź czy pojawia się jednorazowy komunikat RODO
4. Sprawdź czy na ekranie wyników widoczny jest przycisk „Historia badań"
5. Kliknij „Historia badań" — sprawdź listę z datą, inicjałami, kategorią kolorową
6. Przeprowadź drugie badanie — sprawdź dwa rekordy w historii
7. Usuń jeden rekord — potwierdź że lista skraca się do jednego
8. Wyjdź z aplikacji, uruchom ponownie — sprawdź że komunikat RODO nie pojawia się ponownie
9. Sprawdź `history.db` w folderze projektu przez DB Browser lub CLI SQLite

### Phase 6 Manual Testing Steps:

1. Wypełnij metrykę z zaznaczonym ADHD i dysleksją — przejdź dalej bez blokady
2. Przeprowadź analizę — sprawdź `diagnoses_json` w `history.db`
3. Wygeneruj PDF — sprawdź wiersz „Diagnozy: ADHD, Dysleksja"
4. Zaznacz „Inne" z opisem „Zaburzenia ze spektrum tików" — sprawdź PDF i JSON
5. Zaznacz uraz mózgu — potwierdź że „Dalej →" jest zablokowane (regresja)

## Migration Notes

`neuroflag.spec` — nie wymaga zmian. `app/storage/` jest statycznie importowane
z `app/ui/app_window.py`, więc PyInstaller auto-wykryje pakiet bez ręcznego wpisu
w `hiddenimports`. Weryfikacja: `pyinstaller neuroflag.spec --clean` + smoke-test
po wdrożeniu tej zmiany.

## References

- `app/domain/norms.py:127` — wzorzec `resolve_norms_path()` do naśladowania
- `app/ui/views/analysis.py:143` — `_on_done()` — hook auto-zapisu
- `app/ui/views/results_grid.py:169` — `_on_new_study()` — punkt wejścia przycisku
- `app/ui/components/rag_colors.py` — kolory RAG do użycia w `HistoryView`
- `app/domain/types.py:31` — `PatientMetadata` — rozszerzany dataclass
- `context/changes/eegdigitrack-native-reader/plan.md` — wzorzec struktury planu

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Warstwa storage — `app/storage/`

#### Automated

- [x] 1.1 `pytest tests/unit/test_history.py -q` przechodzi — 0f9ae74
- [x] 1.2 `mypy app/storage/history.py --strict` bez błędów — 79a9c2c
- [x] 1.3 `ruff check app/storage/history.py` bez błędów — 79a9c2c

#### Manual

- [x] 1.4 `HistoryStore(resolve_history_db_path()).has_any()` zwraca `False` — 79a9c2c

> Odchylenie od planu: `birth_date` → `birth_year` (spójność z `PatientMetadata`); `list_for_patient()` dodana w ramach Phase 1 na potrzeby filtrowania w Phase 4.

### Phase 2: Typy domenowe + formularz metryki

#### Automated

- [x] 2.1 `mypy app/domain/types.py --strict` bez błędów — 086edad
- [x] 2.2 `mypy app/ui/views/metadata_form.py --strict` bez błędów — 086edad
- [x] 2.3 `pytest tests/unit/test_types.py -q` bez regresji — 086edad

> Odchylenie od planu: pola identyfikacyjne przeniesione z MetadataFormView → FileImportView (po walidacji pliku); birth_date zmienione na birth_year; pre-fill z nagłówka EDF; wszystkie 3 pola opcjonalne.

#### Manual

- [x] 2.4 Formularz pokazuje sekcję „Identyfikacja dziecka (opcjonalnie)" z 3 polami — 086edad
- [x] 2.5 Formularz przechodzi dalej gdy pola są puste — 086edad

### Phase 3: Auto-zapis po analizie

#### Automated

- [x] 3.1 `mypy app/ui/app_window.py --strict` bez błędów — bf2bdca
- [x] 3.2 `mypy app/ui/views/analysis.py --strict` bez błędów — bf2bdca

#### Manual

- [x] 3.3 Po pierwszej analizie pojawia się komunikat RODO (tylko raz) — bf2bdca
- [x] 3.4 `HistoryStore(resolve_history_db_path()).list_recent()` zwraca 1 rekord po analizie — bf2bdca

### Phase 4: `HistoryView` + przycisk w wynikach

#### Automated

- [x] 4.1 `mypy app/ui/views/history.py --strict` bez błędów — fbab1ae
- [x] 4.2 `mypy app/ui/views/results_grid.py --strict` bez błędów — fbab1ae
- [x] 4.3 `ruff check app/ui/views/history.py` bez błędów — fbab1ae

> Odchylenie od planu: HistoryView domyślnie filtruje rekordy po danych bieżącego pacjenta (initials+birth_year lub custom_label); przycisk „Pokaż wszystkie" przełącza na pełną listę.

#### Manual

- [x] 4.4 Przycisk „Historia badań" widoczny po przeprowadzeniu badania — fbab1ae
- [x] 4.5 Usunięcie rekordu działa poprawnie — fbab1ae

### Phase 5: Testy jednostkowe

#### Automated

- [x] 5.1 `pytest tests/unit/test_history.py -v` — 13 testów przechodzi — 0f9ae74
- [x] 5.2 `pytest tests/unit/ -q` — brak regresji — 0f9ae74
- [x] 5.3 `mypy tests/unit/test_history.py --strict` bez błędów — 0f9ae74

#### Manual

- [x] 5.4 Wszystkie 13 testów zielone lokalnie — 0f9ae74
- [x] 5.5 AGENTS.md zaktualizowany (usunięte „nie ma bazy danych") — 0f9ae74

### Phase 6: Diagnozy informacyjne w metryce (FR-010)

#### Automated

- [x] 6.1 `mypy app/domain/types.py app/storage/history.py app/ui/views/metadata_form.py app/ui/views/analysis.py app/reports/pdf_generator.py --strict` bez błędów — 1522cf5
- [x] 6.2 `pytest tests/unit/test_types.py tests/unit/test_history.py tests/unit/test_pdf_generator.py -q` bez regresji — 1522cf5
- [x] 6.3 `ruff check` na zmienionych plikach bez błędów — 1522cf5

#### Manual

- [x] 6.4 Formularz pokazuje sekcję diagnoz informacyjnych (5 checkboxów + pole „Inne") — 1522cf5
- [x] 6.5 Diagnozy informacyjne nie blokują analizy; wykluczenia nadal blokują; komunikat RODO wymienia diagnozy — 1522cf5
- [x] 6.6 `diagnoses_json` zapisany w `history.db` po analizie — 1522cf5
- [x] 6.7 Raport PDF zawiera wiersz diagnoz gdy zaznaczone — 1522cf5
