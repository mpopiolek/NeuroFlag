# Historia badań — lokalna baza SQLite

## Overview

Dodanie lokalnej historii badań przesiewowych do NeuroFlag. Każde zakończone badanie
zapisywane automatycznie do bazy SQLite (`history.db` obok `neuroflag.exe`).
Pedagog widzi listę poprzednich badań (data, identyfikator dziecka, kategoria wynikowa)
i może usuwać rekordy. Funkcja spełnia kryterium CRUD dla certyfikacji MVP
i otwiera drogę do trendów terapeutycznych w v2.0.

## Current State Analysis

- `PatientMetadata` (`app/domain/types.py:31`) — brak pól identyfikujących dziecko
  (inicjały, data urodzenia, etykieta). Można bezpiecznie dodać opcjonalne pola —
  `frozen=True` dataclass, pipeline i algorytm je ignorują.
- `AppState` (`app/ui/app_window.py:12`) — sesja w RAM, reset przy „Nowe badanie".
  `AppState.metadata` i `AppState.analysis_result` są dostępne w momencie zapisu.
- `AnalysisView._on_done()` (`app/ui/views/analysis.py:143`) — naturalne miejsce
  auto-zapisu: wynik gotowy, `show_view(ResultsGridView)` jeszcze niezwołane.
- `ResultsGridView._on_new_study()` (`app/ui/views/results_grid.py:169`) — reset stanu i
  powrót do `MetadataFormView`. Tu można dołączyć przycisk „Historia badań".
- Brak jakiejkolwiek warstwy persystencji; `resolve_norms_path()` (`app/domain/norms.py:127`)
  to wzorzec lokalizacji pliku obok `.exe`.
- `AGENTS.md` zawiera wpis „nie ma bazy danych" — wymaga aktualizacji po tej zmianie.

## Desired End State

Użytkownik może:
1. Wypełnić opcjonalne pola identyfikujące dziecko w formularzu metryki.
2. Po zakończeniu analizy zobaczyć na ekranie wyników przycisk „Historia badań"
   (widoczny tylko gdy historia zawiera co najmniej jeden rekord).
3. Otworzyć widok historii i zobaczyć listę badań: data, identyfikator dziecka,
   kategoria wynikowa (kolor RAG).
4. Usunąć wybrany rekord po potwierdzeniu.
5. Wrócić do ekranu wyników.

Weryfikacja: po przeprowadzeniu 2 badań lista pokazuje 2 rekordy; po usunięciu jednego —
1 rekord; `history.db` istnieje w folderze aplikacji.

## What We're NOT Doing

- Ładowanie danych dziecka z historii do formularza (prefill) — v2.0.
- Wykresy trendów / porównanie wyników w czasie — v2.0.
- Paginacja listy historii — lista wyświetla max 200 ostatnich rekordów; dla MVP wystarczy.
- Szyfrowanie bazy danych — dane pozostają lokalne, szyfrowanie v2.0.
- Eksport historii (CSV/Excel) — v2.0.
- Wyszukiwanie / filtrowanie historii — v2.0.

## Implementation Approach

Pięć faz zależnych sekwencyjnie: warstwa storage (nowy moduł) → rozszerzenie typów domenowych
i formularza → auto-zapis po analizie z jednorazowym komunikatem RODO → widok historii
i przycisk w wynikach → testy jednostkowe.

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

- [ ] 1.1 `pytest tests/unit/test_history.py -q` przechodzi
- [x] 1.2 `mypy app/storage/history.py --strict` bez błędów
- [x] 1.3 `ruff check app/storage/history.py` bez błędów

#### Manual

- [x] 1.4 `HistoryStore(resolve_history_db_path()).has_any()` zwraca `False`

### Phase 2: Typy domenowe + formularz metryki

#### Automated

- [ ] 2.1 `mypy app/domain/types.py --strict` bez błędów
- [ ] 2.2 `mypy app/ui/views/metadata_form.py --strict` bez błędów
- [ ] 2.3 `pytest tests/unit/test_types.py -q` bez regresji

#### Manual

- [ ] 2.4 Formularz pokazuje sekcję „Identyfikacja dziecka (opcjonalnie)" z 3 polami
- [ ] 2.5 Formularz przechodzi dalej gdy pola są puste

### Phase 3: Auto-zapis po analizie

#### Automated

- [ ] 3.1 `mypy app/ui/app_window.py --strict` bez błędów
- [ ] 3.2 `mypy app/ui/views/analysis.py --strict` bez błędów

#### Manual

- [ ] 3.3 Po pierwszej analizie pojawia się komunikat RODO (tylko raz)
- [ ] 3.4 `HistoryStore(resolve_history_db_path()).list_recent()` zwraca 1 rekord po analizie

### Phase 4: `HistoryView` + przycisk w wynikach

#### Automated

- [ ] 4.1 `mypy app/ui/views/history.py --strict` bez błędów
- [ ] 4.2 `mypy app/ui/views/results_grid.py --strict` bez błędów
- [ ] 4.3 `ruff check app/ui/views/history.py` bez błędów

#### Manual

- [ ] 4.4 Przycisk „Historia badań" widoczny po przeprowadzeniu badania
- [ ] 4.5 Usunięcie rekordu działa poprawnie

### Phase 5: Testy jednostkowe

#### Automated

- [ ] 5.1 `pytest tests/unit/test_history.py -v` — 13 testów przechodzi
- [ ] 5.2 `pytest tests/unit/ -q` — brak regresji
- [ ] 5.3 `mypy tests/unit/test_history.py --strict` bez błędów

#### Manual

- [ ] 5.4 Wszystkie 13 testów zielone lokalnie
- [ ] 5.5 AGENTS.md zaktualizowany (usunięte „nie ma bazy danych")
