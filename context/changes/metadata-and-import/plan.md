# S-01: Formularz metryki dziecka + import pliku EEG — Implementation Plan

## Overview

Implementacja S-01 buduje pierwszą warstwę UI aplikacji NeuroFlag: formularz metryki dziecka
(wiek 6–10, płeć, diagnozy kliniczne) oraz widok importu pliku EEG (.edf / .vhdr).
Po ukończeniu aplikacja posiada kompletny front-end wejścia — pedagog może wypełnić dane
i wczytać plik, a aplikacja dostarcza typowany `PatientMetadata` + `Path` gotowe do S-02.

## Current State Analysis

Po F-01 codebase zawiera:
- `app/domain/types.py` — `PatientMetadata`, `ExclusionDiagnosis`, `Sex`, `CellColor`,
  `ScreeningCategory`, `AnalysisResult`, `NormsConfig` (kontrakt domenowy gotowy)
- `app/domain/norms.py` — loader `NormsConfig` z `norms.json`
- `app/main.py` — stub CTk (800×600, brak widoków, obsługa `--smoke-test`)
- `tests/unit/` — testy typów, norm; brak testów UI lub walidacji pliku

Brakuje:
- `app/ui/` — katalog i jakiekolwiek widoki
- `app/domain/eeg_file.py` — walidacja pliku EEG (logika domenowa)
- Mechanizmu nawigacji między widokami
- Typowanego kontenera stanu aplikacji

### Key Discoveries

- `PatientMetadata(age, sex, exclusions)` jest `frozen=True`; musi być skonstruowany jednorazowo
  po wypełnieniu formularza i przechowany w `AppState` — nie da się go modyfikować in-place
  (`app/domain/types.py:32–38`)
- `ExclusionDiagnosis` to enum z trzema wartościami; `is_excluded()` jest już zaimplementowane
  i sprawdzone testami (`app/domain/types.py:8–11`, `38`)
- `Sex` enum ma wartości `Z` / `M` (`app/domain/types.py:26–28`)
- `app/main.py` tworzy `ctk.CTk()` bezpośrednio — do refaktoru w Phase 1 (AppWindow zastępuje
  anonimowe okno)
- MNE `read_raw_brainvision` przyjmuje tylko ścieżkę `.vhdr`; pliki `.vmrk` i `.eeg` są
  odkrywane automatycznie przez MNE z tego samego katalogu — wystarczy sprawdzić ich obecność
  przed wywołaniem (`mne.io` docs + AGENTS.md)
- CTk 5.2.2 nie posiada natywnego Spinbox; wiek (5 wartości: 6–10) modelujemy przez `CTkOptionMenu`

## Desired End State

Po ukończeniu S-01:

1. Pedagog uruchamia aplikację i widzi MetadataFormView: pola wiek, płeć, checkboxy wykluczeń
2. Zaznaczenie wykluczenia klinicznego → pojawia się etykieta ostrzegawcza i przycisk 'Dalej'
   staje się nieaktywny; odznaczenie → blokada znika
3. Po kliknięciu 'Dalej' z poprawnymi danymi → przejście do FileImportView
4. W FileImportView przycisk 'Wczytaj plik' otwiera dialog (filtry .edf, .vhdr);
   po wyborze plik jest walidowany w wątku tła przez MNE header read;
   wynik (sukces / błąd) jest wyświetlany obok nazwy pliku
5. Przycisk 'Analizuj' jest aktywny tylko gdy walidacja przebiegła pomyślnie;
   kliknięcie go wywołuje `AppState.ready_for_analysis() == True` (metadane + ścieżka pliku
   są ustawione) — stub przekazujący kontrolę do S-02
6. `pytest -q` przechodzi; `mypy app/ --strict` nie zgłasza błędów

### Key Discoveries

- `app/ui/app_window.py` staje się nowym centrum aplikacji; `app/main.py` tworzy
  instancję `AppWindow` zamiast anonimowego `ctk.CTk()`
- `AppState` musi być mutowalny (widoki zapisują wyniki postupno) — **nie** jest frozen dataclass
- Walidacja pliku (MNE header load) musi działać w wątku (`threading.Thread`) i zwracać
  wynik do UI przez `CTk.after()` — bezpośrednie wywołanie MNE w event loop zamraża okno

## What We're NOT Doing

- **Drag & drop** — odkładamy na backlog; tylko przycisk 'Wczytaj plik' w S-01
- **Analiza sygnału** — S-01 dostarcza tylko ścieżkę pliku; pipeline EEG to S-02
- **Siatka wyników** — to S-02
- **Raport PDF** — to S-03
- **Podmiana norms.json przez UI** — to S-04
- **Opcjonalne hasło startowe (FR-009)** — odłożone (nice-to-have, poza MVP scope)
- **Persystencja stanu między sesjami** — AppState żyje tylko w pamięci przez czas sesji
- **Walidacja zawartości EEG** (czy plik zawiera kanały C3/O1, znaczniki OO/OZ/ZP) —
  to zadanie pipeline'u w S-02, nie importu

## Implementation Approach

Podejście warstwowe: najpierw powłoka nawigacyjna (AppWindow + AppState), potem widoki
od lewej strony flow (MetadataFormView), potem prawa strona (FileImportView + walidator pliku),
na końcu testy. Każda faza kończy się weryfikowalnym checkpointem.

`app/domain/eeg_file.py` trzyma logikę domenową walidacji pliku (co to znaczy "poprawny plik EEG"
w kontekście NeuroFlag) z dala od CTk — dzięki temu jest testowalny bez display i importowalny
przez S-02 pipeline.

## Critical Implementation Details

**Threading i CTk**: MNE header load (`preload=False`) wywołujemy w `threading.Thread`;
wynik (sukces lub wyjątek) przekazujemy do UI przez `self.after(0, callback)` — jedyna
bezpieczna metoda aktualizacji CTk widgetów z wątku innego niż główny. Nigdy nie aktualizuj
widgetów bezpośrednio z wątku tła.

**AppState mutability**: `AppState` jest zwykłą dataclassą (`@dataclass`, **bez** `frozen=True`).
Widoki modyfikują jej pola bezpośrednio — `app_state.metadata = PatientMetadata(...)`.
Kontrast z `PatientMetadata` (frozen) i innymi value objects z `types.py`.

**Destroy + create navigation**: `AppWindow.show_view(ViewClass, **kwargs)` niszczy bieżący
widget `self._current_view` (jeśli istnieje) i tworzy nową instancję `ViewClass`, pakując ją
przez `pack(fill="both", expand=True)`. Widoki nie przechowują referencji do siebie nawzajem —
tylko `AppWindow` zna oba widoki.

---

## Phase 1: AppWindow — powłoka nawigacyjna i AppState

### Overview

Tworzy typowany kontener stanu (`AppState`) oraz `AppWindow` z mechanizmem destroy+create
do przełączania widoków. Refaktoruje `app/main.py` tak, żeby używał `AppWindow`. Po tej fazie
aplikacja uruchamia się i wyświetla puste okno z tytułem "NeuroFlag — Badanie przesiewowe EEG"
(zamiast obecnego `ctk.CTk()` stub).

### Changes Required

#### 1. Nowe pliki inicjalizacyjne UI

**File**: `app/ui/__init__.py`

**Intent**: Oznaczyć `app/ui/` jako pakiet Pythona.

**Contract**: Pusty plik.

---

**File**: `app/ui/views/__init__.py`

**Intent**: Oznaczyć `app/ui/views/` jako pakiet Pythona.

**Contract**: Pusty plik.

---

#### 2. AppState i AppWindow

**File**: `app/ui/app_window.py`

**Intent**: Zdefiniować `AppState` jako mutowalną dataclassę trzymającą stan pomiędzy widokami
oraz `AppWindow` jako główne okno CTk z metodą `show_view` realizującą nawigację destroy+create.

**Contract**:

```python
@dataclass
class AppState:
    metadata: PatientMetadata | None = None
    eeg_path: Path | None = None

    def ready_for_analysis(self) -> bool:
        return self.metadata is not None and self.eeg_path is not None

class AppWindow(ctk.CTk):
    def __init__(self) -> None: ...
    def show_view(self, view_class: type[ctk.CTkFrame], **kwargs: object) -> None: ...
```

`show_view` przechowuje bieżący widok w `self._current_view: ctk.CTkFrame | None`;
przy każdym wywołaniu niszczy poprzedni (`destroy()`) i tworzy nowy.
Widoki otrzymują `app_window=self` i `app_state=self._state` jako kwargs.

Rozmiar okna: `900x650`. Tytuł: `"NeuroFlag — Badanie przesiewowe EEG"`.
CTk appearance mode i color theme: `"light"` / `"blue"` (ustawiane przed `__init__`).

---

#### 3. Aktualizacja app/main.py

**File**: `app/main.py`

**Intent**: Zastąpić anonimowe `ctk.CTk()` instancją `AppWindow` i uruchomić
`show_view(MetadataFormView)` jako pierwszy widok po załadowaniu norm.

**Contract**: Import `AppWindow` z `app.ui.app_window`; import `MetadataFormView`
z `app.ui.views.metadata_form`. Sygnatura `main()` bez zmian.

---

#### 4. mypy override dla CustomTkinter *(addendum — impl-review Phase 1)*

**File**: `pyproject.toml`

**Intent**: Zezwolić na dziedziczenie po `ctk.CTk` / `ctk.CTkFrame` przy `mypy --strict`.
CustomTkinter nie dostarcza stubów typów; bez override mypy zgłasza `[misc] Class cannot subclass "CTk" (has type "Any")`.

**Contract**: Dodać w `[tool.mypy]`:

```toml
[[tool.mypy.overrides]]
module = ["customtkinter", "customtkinter.*"]
disallow_subclassing_any = false

[[tool.mypy.overrides]]
module = ["app.ui", "app.ui.*"]
disallow_subclassing_any = false
```

### Success Criteria

#### Automated Verification

- `python -m app.main --smoke-test` kończy się kodem 0
- `mypy app/ --strict` bez błędów dla nowych plików
- `pytest -q` zielony (istniejące testy nie regresują)

#### Manual Verification

- Aplikacja uruchamia się, wyświetla okno 900×650 z tytułem "NeuroFlag — Badanie przesiewowe EEG"
- Okno zamyka się przez przycisk X bez błędów w konsoli

**Implementation Note**: Zatrzymaj się po Phase 1 i potwierdź ręcznie, że okno otwiera się
poprawnie przed przejściem do Phase 2.

---

## Phase 2: MetadataFormView — formularz metryki dziecka

### Overview

Implementuje widok formularza metryki dziecka: wybór wieku (CTkOptionMenu 6–10),
płci (dwa CTkRadioButton), diagnoz wykluczających (trzy CTkCheckBox). Kliknięcie 'Dalej'
konstruuje `PatientMetadata`, zapisuje w `AppState.metadata` i przechodzi do FileImportView.
Zaznaczenie jakiegokolwiek wykluczenia dezaktywuje przycisk 'Dalej' i wyświetla etykietę
ostrzegawczą.

### Changes Required

#### 1. MetadataFormView

**File**: `app/ui/views/metadata_form.py`

**Intent**: Zbudować formularz CTk z polami metryki dziecka, logiką blokady wykluczeń
i nawigacją do FileImportView po poprawnym wypełnieniu.

**Contract**:

```python
class MetadataFormView(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTk,
        app_window: "AppWindow",
        app_state: AppState,
        **kwargs: object,
    ) -> None: ...
```

Struktura widgety (z góry na dół):
1. `CTkLabel` — nagłówek "Dane dziecka"
2. Rząd: `CTkLabel("Wiek:")` + `CTkOptionMenu(values=["6","7","8","9","10"])`
3. Rząd: `CTkLabel("Płeć:")` + `CTkRadioButton("Dziewczynka", variable=sex_var, value="Z")` +
   `CTkRadioButton("Chłopiec", variable=sex_var, value="M")`; zmienna
   `sex_var = StringVar(value="Z")` — **"Dziewczynka" wstępnie zaznaczona domyślnie**,
   co eliminuje ryzyko `Sex("")` → ValueError przy kliknięciu 'Dalej →'
4. `CTkLabel("Diagnozy wykluczające:")` + trzy `CTkCheckBox`:
   - "Uraz lub uszkodzenie mózgu" → `ExclusionDiagnosis.BRAIN_INJURY`
   - "Niepełnosprawność intelektualna" → `ExclusionDiagnosis.INTELLECTUAL_DISABILITY`
   - "Padaczka" → `ExclusionDiagnosis.EPILEPSY`
5. `CTkLabel` (ostrzeżenie, początkowo ukryty przez `grid_remove()`):
   tekst "Zaznaczone diagnozy wykluczają udział w badaniu przesiewowym."
   kolor tekstu: `"#CC0000"` (ciemnoczerwony, zgodny z "light" theme)
6. `CTkButton("Dalej →")` — disabled gdy jakiekolwiek wykluczenie zaznaczone

Każdy `CTkCheckBox` jest podpięty do `BooleanVar`; metoda `_on_exclusion_change()` wywoływana
przez `trace_add("write", ...)` na każdej zmiennej — aktualizuje widoczność ostrzeżenia
i stan przycisku.

Kliknięcie 'Dalej →' (gdy aktywny):
- odczytuje wiek (`int(age_var.get())`), płeć (`Sex(sex_var.get())`),
  wykluczenia (`frozenset` z zaznaczonych `ExclusionDiagnosis`)
- tworzy `PatientMetadata(age=..., sex=..., exclusions=...)`
- zapisuje do `app_state.metadata`
- wywołuje `app_window.show_view(FileImportView)` — **import FileImportView
  musi być lazy (wewnątrz ciała metody _on_next, nie na poziomie modułu)**
  żeby uniknąć circular import z file_import.py, który importuje MetadataFormView:
  ```python
  def _on_next(self) -> None:
      from app.ui.views.file_import import FileImportView  # lazy — nie na poziomie modułu
      self._app_window.show_view(FileImportView)
  ```

### Success Criteria

#### Automated Verification

- `mypy app/ --strict` bez błędów dla `metadata_form.py`
- `pytest -q` zielony

#### Manual Verification

- Widok MetadataFormView wyświetla się jako pierwszy ekran po uruchomieniu
- CTkOptionMenu pokazuje wartości 6, 7, 8, 9, 10
- Zaznaczenie dowolnego checkboxa → pojawia się komunikat ostrzegawczy, przycisk 'Dalej →' jest wyszarzony
- Odznaczenie wszystkich checkboxów → komunikat znika, przycisk 'Dalej →' jest aktywny
- Kliknięcie 'Dalej →' z wiekiem=8, płcią=Z, brak wykluczeń → otwiera się FileImportView
- Kliknięcie 'Dalej →' z zaznaczonym wykluczeniem jest niemożliwe (przycisk disabled)

**Implementation Note**: Zatrzymaj się po Phase 2 i przetestuj ręcznie formularz zanim
przejdziesz do Phase 3.

---

## Phase 3: EEG file validator + FileImportView

### Overview

Tworzy moduł domenowy `app/domain/eeg_file.py` (testowalny, bez CTk) z logiką walidacji
pliku EEG oraz widok `FileImportView` z dialogiem wyboru pliku, asynchroniczną walidacją
w wątku tła i przyciskiem 'Analizuj'.

### Changes Required

#### 1. Moduł domenowy walidacji pliku EEG

**File**: `app/domain/eeg_file.py`

**Intent**: Zdefiniować `EEGFileError` i publiczne funkcje walidacji pliku EEG, izolując
logikę domenową ("co to znaczy poprawny plik EEG") od warstwy UI.

**Contract**:

```python
class EEGFileError(Exception):
    pass

SUPPORTED_EXTENSIONS: frozenset[str]  # {".edf", ".vhdr"}

def validate_extension(path: Path) -> None:
    """Raises EEGFileError if extension not in SUPPORTED_EXTENSIONS."""

def resolve_brainvision_companions(vhdr_path: Path) -> tuple[Path, Path]:
    """Returns (vmrk_path, eeg_path) next to vhdr_path.
    Raises EEGFileError if either companion file is missing."""

def validate_eeg_header(path: Path) -> None:
    """Single entry point for full EEG file validation.
    Step 1: calls validate_extension(path) — raises EEGFileError for unsupported extensions.
    Step 2 (.edf): calls mne.io.read_raw_edf(path, preload=False).
    Step 2 (.vhdr): calls resolve_brainvision_companions(path), then read_raw_brainvision.
    Wraps any MNE exception or OSError as EEGFileError."""
```

`validate_eeg_header` jest przeznaczona do wywołania z wątku tła — nie wywołuj jej
bezpośrednio z event loop CTk.

Mapowanie wyjątków MNE → `EEGFileError`:
- `Exception` z `read_raw_*` → `EEGFileError(f"Nie można odczytać pliku: {exc}")`
- `OSError` → `EEGFileError(f"Plik niedostępny: {exc}")`

---

#### 2. FileImportView

**File**: `app/ui/views/file_import.py`

**Intent**: Zbudować widok importu pliku EEG z przyciskiem 'Wczytaj plik', etykietą statusu
walidacji i przyciskiem 'Analizuj' aktywnym tylko po pomyślnej walidacji.

**Contract**:

```python
class FileImportView(ctk.CTkFrame):
    def __init__(
        self,
        master: ctk.CTk,
        app_window: "AppWindow",
        app_state: AppState,
        **kwargs: object,
    ) -> None: ...
```

**Ważne**: `__init__` ustawia `app_state.eeg_path = None` jako pierwszy krok —
każda nowa instancja FileImportView zaczyna bez wybranego pliku, niezależnie od
tego co poprzednia sesja zostawiła w AppState. Zapobiega sytuacji, gdzie
`AppState.ready_for_analysis()` zwraca True mimo że UI pokazuje "Nie wybrano pliku".

Struktura widgetów (z góry na dół):
1. `CTkLabel` — nagłówek "Wczytaj plik EEG"
2. `CTkButton("Wczytaj plik")` — otwiera `filedialog.askopenfilename`
   z `filetypes=[("Pliki EEG", "*.edf *.vhdr"), ("Wszystkie pliki", "*.*")]`
3. `CTkLabel` — ścieżka wybranego pliku (początkowo: "Nie wybrano pliku")
4. `CTkLabel` — status walidacji (początkowo: ukryty); pokazuje:
   - "✓ Plik wczytany poprawnie" (kolor zielony) — po sukcesie
   - "✗ {komunikat błędu}" (kolor `"#CC0000"`) — po błędzie
5. `CTkProgressBar` — nieokreślony (`mode="indeterminate"`), widoczny podczas walidacji w tle
6. `CTkButton("Analizuj")` — disabled domyślnie; aktywny po pomyślnej walidacji
7. `CTkButton("← Wróć")` — wraca do MetadataFormView; **import MetadataFormView
   musi być lazy (wewnątrz ciała metody _on_back)** żeby uniknąć circular import:
   ```python
   def _on_back(self) -> None:
       from app.ui.views.metadata_form import MetadataFormView  # lazy — nie na poziomie modułu
       self._app_window.show_view(MetadataFormView)
   ```

Przepływ walidacji po wyborze pliku:
1. Pokaż `CTkProgressBar` (start indeterminate)
2. Ukryj etykietę statusu
3. Uruchom `threading.Thread(target=_validate_worker, daemon=True)`
4. `_validate_worker` wywołuje `eeg_file.validate_eeg_header(path)`;
   wynik (None lub EEGFileError) przekazuje przez `self.after(0, _on_result, result)`
5. `_on_result` zatrzymuje progress bar, wyświetla status, ustawia `app_state.eeg_path`
   (lub None przy błędzie), aktywuje/dezaktywuje 'Analizuj'

Kliknięcie 'Analizuj' (stub S-01): wywołuje `print("Analiza: gotowe do S-02")` —
właściwa nawigacja do widoku analizy zostanie dodana w S-02.

### Success Criteria

#### Automated Verification

- `mypy app/ --strict` bez błędów dla `eeg_file.py` i `file_import.py`
- `pytest -q` zielony

#### Manual Verification

- Po kliknięciu 'Wczytaj plik' otwiera się dialog z filtrami .edf i .vhdr
- Wybór poprawnego pliku .edf → progress bar → "✓ Plik wczytany poprawnie", 'Analizuj' aktywny
- Wybór pliku z błędnym rozszerzeniem (np. .txt) → "✗ Nieobsługiwane rozszerzenie: .txt"
- Wybór pliku .vhdr bez towarzyszącego .eeg → "✗ Brak pliku .eeg obok wybranego .vhdr"
- Kliknięcie '← Wróć' → powrót do MetadataFormView (dane metryki zachowane w AppState)
- UI nie zamraża się podczas walidacji pliku (progress bar się kręci)

**Implementation Note**: Przetestuj oba formaty pliku (jeśli dostępne) przed Phase 4.

---

## Phase 4: Testy jednostkowe

### Overview

Dodaje testy jednostkowe pokrywające logikę domenową `eeg_file.py` (walidacja pliku)
oraz uzupełnia testy `types.py` o scenariusze S-01 dla `PatientMetadata.is_excluded()`.

### Changes Required

#### 1. Testy walidatora pliku EEG

**File**: `tests/unit/test_eeg_file.py`

**Intent**: Pokryć wszystkie ścieżki błędów `eeg_file.py` używając mock MNE, bez potrzeby
prawdziwego pliku EDF.

**Contract**: Testy dla:
- `validate_extension`: nieobsługiwane rozszerzenie → `EEGFileError`; `.edf` / `.vhdr` → brak wyjątku
- `resolve_brainvision_companions`: brak `.vmrk` → `EEGFileError`; brak `.eeg` → `EEGFileError`;
  oba obecne → zwraca tuple ścieżek (użyj `tmp_path` z pytest do tworzenia pliku)
- `validate_eeg_header` (.edf): mock `mne.io.read_raw_edf` rzuca wyjątek → `EEGFileError`
- `validate_eeg_header` (.edf): mock `mne.io.read_raw_edf` OK → brak wyjątku
- `validate_eeg_header` (.vhdr): towarzyszące pliki obecne, mock `read_raw_brainvision` OK → brak wyjątku

Użyj `unittest.mock.patch("mne.io.read_raw_edf", ...)` i
`unittest.mock.patch("mne.io.read_raw_brainvision", ...)`.

---

#### 2. Uzupełnienie test_types.py — scenariusze is_excluded()

**File**: `tests/unit/test_types.py`

**Intent**: Upewnić się, że `is_excluded()` zwraca True dla każdego z trzech wykluczeń osobno
(regresja guard dla logiki blokady w MetadataFormView).

**Contract**: Dodać **2 brakujące** testy (EPILEPSY samodzielnie jest już pokryte przez
`test_patient_metadata_single_exclusion` w istniejącym pliku — nie duplikować):
- `ExclusionDiagnosis.BRAIN_INJURY` samodzielnie → `is_excluded() == True`
- `ExclusionDiagnosis.INTELLECTUAL_DISABILITY` samodzielnie → `is_excluded() == True`

(`frozenset()` → `False` pokryte przez `test_patient_metadata_no_exclusions` — nie duplikować.)

### Success Criteria

#### Automated Verification

- `pytest -q` — 0 failed, wszystkie nowe testy zielone
- `pytest tests/unit/test_eeg_file.py -v` — każdy test case wymieniony i zaliczony
- `mypy app/ --strict` — 0 błędów

#### Manual Verification

- `pytest -q --tb=short` wypisuje podsumowanie bez żadnego FAILED ani ERROR

**Implementation Note**: Po przejściu wszystkich testów S-01 jest gotowy do code review
i archiwizacji przed startem S-02.

---

## Testing Strategy

### Unit Tests

- `tests/unit/test_eeg_file.py` — walidator pliku (mock MNE, tmp_path dla BrainVision companions)
- `tests/unit/test_types.py` — uzupełnienie `is_excluded()` dla każdego wykluczenia

### Integration Tests

Brak w S-01. Pełne testy E2E (wczytanie pliku .edf do siatki wyników) należą do S-02/S-03.

### Manual Testing Steps

1. Uruchom `python -m app.main`
2. Sprawdź MetadataFormView: wypełnij dane (wiek=9, płeć=Z, brak wykluczeń), kliknij 'Dalej →'
3. W FileImportView kliknij 'Wczytaj plik' i wybierz plik .edf (testowy)
4. Poczekaj na walidację — sprawdź "✓ Plik wczytany poprawnie" i aktywność 'Analizuj'
5. Kliknij '← Wróć' — sprawdź powrót do MetadataFormView
6. Uruchom ponownie z wykluczeniem zaznaczonym — sprawdź blokadę i komunikat

## References

- Roadmap: `context/foundation/roadmap.md` (S-01)
- PRD: `context/foundation/prd.md` (FR-001, FR-010, US-01)
- Typy domenowe: `app/domain/types.py`
- Loader norm: `app/domain/norms.py` (wzorzec dla eeg_file.py)
- F-01 plan: `context/changes/project-foundation/plan.md`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: AppWindow — powłoka nawigacyjna i AppState

#### Automated

- [x] 1.1 `python -m app.main --smoke-test` kończy się kodem 0 — a255733
- [x] 1.2 `mypy app/ --strict` bez błędów dla nowych plików Phase 1 — a255733
- [x] 1.3 `pytest -q` zielony (brak regresji) — a255733

#### Manual

- [x] 1.4 Aplikacja uruchamia się, wyświetla okno 900×650 z tytułem "NeuroFlag — Badanie przesiewowe EEG" — a255733
- [x] 1.5 Okno zamyka się przez przycisk X bez błędów w konsoli — a255733

### Phase 2: MetadataFormView

#### Automated

- [x] 2.1 `mypy app/ --strict` bez błędów dla `metadata_form.py` — 4ebce96
- [x] 2.2 `pytest -q` zielony — 4ebce96

#### Manual

- [x] 2.3 MetadataFormView wyświetla się jako pierwszy ekran; CTkOptionMenu pokazuje wartości 6–10 — 4ebce96
- [x] 2.4 Zaznaczenie wykluczenia → komunikat ostrzegawczy widoczny, 'Dalej →' wyszarzony — 4ebce96
- [x] 2.5 Odznaczenie → komunikat znika, 'Dalej →' aktywny — 4ebce96
- [x] 2.6 Kliknięcie 'Dalej →' z poprawnymi danymi (wiek=8, płeć=Z) → otwiera FileImportView — 4ebce96

### Phase 3: EEG file validator + FileImportView

#### Automated

- [x] 3.1 `mypy app/ --strict` bez błędów dla `eeg_file.py` i `file_import.py` — 06d9647
- [x] 3.2 `pytest -q` zielony — 06d9647

#### Manual

- [x] 3.3 Dialog pliku otwiera się z filtrami .edf i .vhdr — 06d9647
- [x] 3.4 Poprawny plik .edf → "✓ Plik wczytany poprawnie"; 'Analizuj' aktywny — 06d9647
- [x] 3.5 Plik .txt → komunikat błędu "✗ Nieobsługiwane rozszerzenie" — 06d9647
- [x] 3.6 Plik .vhdr bez .eeg → komunikat błędu "✗ Brak pliku .eeg..." — 06d9647
- [x] 3.7 UI nie zamraża się podczas walidacji (progress bar widoczny) — 06d9647
- [x] 3.8 Przycisk '← Wróć' → powrót do MetadataFormView z zachowanymi danymi w AppState — 06d9647

### Phase 4: Testy jednostkowe

#### Automated

- [x] 4.1 `pytest tests/unit/test_eeg_file.py -v` — wszystkie testy zielone — a2143b1
- [x] 4.2 `pytest -q --tb=short` — 0 FAILED, 0 ERROR — a2143b1
- [x] 4.3 `mypy app/ --strict` — 0 błędów — a2143b1

#### Manual

- [x] 4.4 `pytest -q` wypisuje podsumowanie bez FAILED ani ERROR — a2143b1
