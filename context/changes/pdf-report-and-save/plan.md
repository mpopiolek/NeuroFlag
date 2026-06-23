# PDF Report & Save — Implementation Plan

## Overview

Dodanie generatora raportów PDF do aplikacji NeuroFlag. Po zakończeniu analizy EEG użytkownik może kliknąć "Zapisz raport PDF" w widoku wyników, wybrać lokalizację przez systemowy dialog i otrzymać plik PDF z 4 sekcjami zgodnymi z PRD: intro, siatka RAG, checklist obserwacyjna, klauzula odpowiedzialności. Surowe wartości µV nigdy nie trafiają do raportu.

## Current State Analysis

Aplikacja S-02 jest kompletna: `app/domain/pipeline.py` produkuje amplitudy µV, `app/domain/algorithm.py` klasyfikuje je w `AnalysisResult` (10 `CellResult` z kolorami RAG + kategoria), a `ResultsGridView` wyświetla siatkę. Brakuje:
- modułu `app/reports/` (pdf_generator.py)
- przycisku "Zapisz raport PDF" w `ResultsGridView`
- wspólnych stałych kolorów RAG (są hardcode w `results_grid.py:19-35`)
- stałej APP_VERSION (wymagana w stopce — `distribution.md:48`)

`NormsConfig` zawiera już `observation_checklist` i `category_descriptions` gotowe do użycia w PDF (`types.py:101-107, 111-118`). ReportLab jest w zależnościach i wpisany w `neuroflag.spec:39-46`.

### Key Discoveries:

- Kolory RAG definiuje `results_grid.py:19-35` (`_COLOR_BG`, `_COLOR_FG`); PDF musi używać tych samych hex — AGENTS.md wskazuje `app/ui/components/` jako miejsce na "kolory RAG" (`AGENTS.md:46`)
- `AppState` (`app_window.py:12-24`) przechowuje `metadata`, `analysis_result`, `norms_config` — wszystko co potrzebuje PDF generator
- `PatientMetadata` nie ma pola imię/nazwisko — raport jest anonimowy; wyświetlamy wiek, płeć i datę z `AnalysisResult.analyzed_at`
- `_TASK_LABELS` w `results_grid.py:13-17` mapuje kody `OO/OZ/ZP` na polskie etykiety — musi być dostępne w PDF generatorze
- `APP_VERSION` nie istnieje nigdzie — dodajemy przez `importlib.metadata.version("neuroflag")` w `app/__init__.py`
- Tekst klauzuli odpowiedzialności nie istnieje w repozytorium — hardcode jako `DISCLAIMER_PL` w pdf_generator.py

## Desired End State

Po implementacji kliknięcie "Zapisz raport PDF" na ekranie wyników otwiera systemowy dialog zapisu (domyślna nazwa `neuroflag_YYYY-MM-DD.pdf`), po wybraniu ścieżki zapisuje plik PDF z 4 sekcjami. W przypadku błędu pojawia się `messagebox.showerror` po polsku. Jeśli użytkownik anuluje dialog — nic się nie dzieje, wraca do ekranu wyników.

## What We're NOT Doing

- Drukowanie bezpośrednie z aplikacji (użytkownik drukuje przez systemowy PDF viewer)
- Zbieranie imienia/nazwiska dziecka (anonimowe badanie)
- Konfigurowalne szablony PDF (statyczny layout)
- Podgląd PDF przed zapisem
- Historia zapisanych raportów
- Jakiekolwiek wartości µV w raporcie (bezwzględny zakaz per PRD)
- Zmiana `PatientMetadata` o pole ID pacjenta (poza zakresem S-03)

## Implementation Approach

Cztery fazy: (1) wyodrębnij stałe kolorów RAG do `app/ui/components/rag_colors.py` + dodaj `APP_VERSION`; (2) zaimplementuj `app/reports/pdf_generator.py` z ReportLab — czysta funkcja `generate_report() -> bytes`; (3) zintegruj przycisk + zapis w `ResultsGridView`; (4) testy jednostkowe weryfikujące format wyjścia, brak µV, obecność kluczowych sekcji.

## Critical Implementation Details

- **Ordering: faza 1 przed fazą 2** — `pdf_generator.py` importuje `RAG_COLORS_BG` z `app/ui/components/rag_colors.py`; bez fazy 1 import się nie powiedzie.
- **Typ wyjścia `generate_report`** — funkcja zwraca `bytes` (in-memory PDF z `io.BytesIO`), nie pisze do pliku sama. Zapis do pliku należy do warstwy UI (`ResultsGridView`), co pozwala testować generator bez systemu plików.
- **Klauzula odpowiedzialności** — wymagana przez PRD, ale tekst nie był zatwierdzony przez eksperta domenowego. Hardcode wersji roboczej z komentarzem `# TODO: weryfikacja eksperta`; nie blokuje implementacji.

---

## Phase 1: Shared Infrastructure — RAG Colors & APP_VERSION

### Overview

Wyodrębnienie stałych kolorów RAG do dedykowanego modułu zgodnie z AGENTS.md + dodanie `APP_VERSION` przez `importlib.metadata`. Ta faza nie zmienia zachowania UI — jest refaktorem przygotowawczym.

### Changes Required:

#### 1. Nowy moduł `app/ui/components/`

**File**: `app/ui/components/__init__.py`

**Intent**: Inicjalizacja pakietu `components` zgodnie ze strukturą z AGENTS.md.

**Contract**: Pusty plik `__init__.py`.

#### 2. Stałe kolorów RAG

**File**: `app/ui/components/rag_colors.py`

**Intent**: Przenieś `_COLOR_BG`, `_COLOR_FG`, `_TASK_LABELS`, `_CATEGORY_COLOR` z `results_grid.py` do wspólnego modułu. Zmień nazwy na publiczne (bez wiodącego `_`).

**Contract**:
```python
# Publiczne stałe używane przez ResultsGridView i pdf_generator
RAG_COLOR_BG: dict[CellColor, str]  # hex tła komórki
RAG_COLOR_FG: dict[CellColor, str]  # hex tekstu w komórce
TASK_LABELS: dict[str, str]          # "OO" -> "Oczy otwarte"
CATEGORY_COLOR: dict[ScreeningCategory, str]  # hex koloru kategorii
```

#### 3. Aktualizacja `results_grid.py` — import z nowego modułu

**File**: `app/ui/views/results_grid.py`

**Intent**: Zastąp lokalne definicje `_COLOR_BG`, `_COLOR_FG`, `_TASK_LABELS`, `_CATEGORY_COLOR` importami z `app.ui.components.rag_colors`. Zachowanie UI nie zmienia się.

**Contract**: Importuj `RAG_COLOR_BG as _COLOR_BG` itd. (aliasy zachowują czytelność kodu bez zmiany wszystkich odwołań).

#### 4. APP_VERSION w `app/__init__.py`

**File**: `app/__init__.py`

**Intent**: Dodaj `__version__` ładowany przez `importlib.metadata`, żeby PDF generator miał jedno źródło prawdy dla wersji.

**Contract**:
```python
from importlib.metadata import version, PackageNotFoundError
try:
    __version__: str = version("neuroflag")
except PackageNotFoundError:
    __version__ = "dev"
```

### Success Criteria:

#### Automated Verification:

- Testy przechodzą bez regresji: `python -m pytest -q`
- Brak błędów importu: `python -c "from app.ui.components.rag_colors import RAG_COLOR_BG; from app import __version__; print(__version__)"`
- Mypy przechodzi: `mypy app/ --strict`

#### Manual Verification:

- Aplikacja uruchamia się normalnie i wyświetla siatkę wyników (kolory bez zmian)

**Implementation Note**: Po zakończeniu tej fazy i przejściu testów automatycznych, poczekaj na ręczne potwierdzenie przed przejściem do fazy 2.

---

## Phase 2: PDF Generator Module

### Overview

Nowy moduł `app/reports/pdf_generator.py` z czystą funkcją `generate_report()` zwracającą `bytes`. Generuje 4 sekcje PDF zgodnie z PRD: (1) intro, (2) siatka 10 komórek RAG, (3) checklist "Co obserwować", (4) klauzula odpowiedzialności.

### Changes Required:

#### 1. Inicjalizacja pakietu `app/reports/`

**File**: `app/reports/__init__.py`

**Intent**: Pusty plik inicjalizujący pakiet.

**Contract**: Pusty.

#### 2. Generator PDF

**File**: `app/reports/pdf_generator.py`

**Intent**: Implementacja `generate_report()` produkującej kompletny raport A4 ze wszystkimi 4 sekcjami wymaganymi przez PRD. Funkcja nie zna ścieżki zapisu — zwraca `bytes`.

**Contract**:
```python
def generate_report(
    metadata: PatientMetadata,
    result: AnalysisResult,
    config: NormsConfig,
) -> bytes:
    """Generuje raport PDF; nigdy nie zawiera wartości µV."""
    ...
```

Wewnętrzna stała:
```python
DISCLAIMER_PL: str = (
    "Raport jest narzędziem przesiewowym i nie stanowi diagnozy medycznej. "
    "Wyniki należy interpretować wyłącznie w połączeniu z pełną oceną kliniczną "
    "przez uprawnionego specjalistę. Autorzy aplikacji NeuroFlag nie ponoszą "
    "odpowiedzialności za decyzje podjęte wyłącznie na podstawie niniejszego raportu."
    # TODO: weryfikacja eksperta domenowego przed wdrożeniem produkcyjnym
)
```

Sekcje w kolejności PRD (`prd.md:88`):
1. **Nagłówek/Intro** — logo-tekst "NeuroFlag", data badania (`result.analyzed_at.strftime("%d.%m.%Y")`), wiek (`metadata.age` lat), płeć (`metadata.sex.value`), wynik słowny: `result.category.value` + `result.description`
2. **Siatka 10 komórek** — 2 rzędy × 5 komórek; każda komórka to prostokąt ReportLab z kolorem tła z `RAG_COLOR_BG[cell.color]`, wewnątrz: kanał (bold), `TASK_LABELS[cell.task]`, `cell.band`
3. **Checklist "Co obserwować"** — `config.observation_checklist.title`, `config.observation_checklist.intro`, następnie każda `ObservationCategory`: nagłówek + lista `items`
4. **Disclaimer** — `DISCLAIMER_PL`, kursywa, małą czcionką; stopka z wersją aplikacji (`from app import __version__`)

Kolory importuje z `app.ui.components.rag_colors`.

Layout techniczny: `reportlab.lib.pagesizes.A4`, marginesy 2 cm, `SimpleDocTemplate` + `Platypus` Flowables (`Paragraph`, `Spacer`, `Table`). Siatka komórek jako `Table` z `TableStyle` — kolory tła przez `BACKGROUND`.

### Success Criteria:

#### Automated Verification:

- Testy jednostkowe przechodzą: `python -m pytest tests/unit/test_pdf_generator.py -v`
- Mypy: `mypy app/reports/ --strict`
- Import smoke: `python -c "from app.reports.pdf_generator import generate_report; print('ok')"`

#### Manual Verification:

- Wywołaj `generate_report()` z fixtureami i otwórz wygenerowany plik PDF — sprawdź, czy 4 sekcje są widoczne
- Sprawdź, że siatka 2×5 wyświetla kolory RAG
- Sprawdź, że żadna wartość numeryczna µV nie pojawia się w dokumencie

**Implementation Note**: Przed przejściem do fazy 3 — ręczne obejrzenie wygenerowanego PDF.

---

## Phase 3: UI Integration — "Zapisz raport PDF" Button

### Overview

Dodanie przycisku "Zapisz raport PDF" do `ResultsGridView`, wywołującego `generate_report()` i zapisującego do pliku wybranego przez użytkownika w `filedialog.asksaveasfilename`.

### Changes Required:

#### 1. Przycisk i logika zapisu w `ResultsGridView`

**File**: `app/ui/views/results_grid.py`

**Intent**: Dodaj przycisk "Zapisz raport PDF" poniżej siatki wyników. Po kliknięciu: (a) otwórz dialog zapisu, (b) wygeneruj bytes przez `generate_report()`, (c) zapisz plik, (d) obsłuż błędy przez `messagebox.showerror`.

**Contract**: Nowa metoda `_on_save_pdf(self) -> None` wywoływana przez przycisk. Przycisk ma `width=200` i pojawia się obok "← Nowe badanie".

Na początku metody — guard dla mypy strict (oba pola są `... | None` w `AppState`):
```python
if self._app_state.analysis_result is None or self._app_state.metadata is None:
    return  # structurally unreachable; satisfies mypy --strict
```

Dialog:

```python
path = filedialog.asksaveasfilename(
    defaultextension=".pdf",
    filetypes=[("PDF", "*.pdf")],
    initialfile=f"neuroflag_{result.analyzed_at.strftime('%Y-%m-%d')}.pdf",
)
```

Jeśli `path` jest pustym stringiem (użytkownik anulował) — wyjdź bez akcji. Zarówno `generate_report()` jak i `Path.write_bytes()` muszą być objęte wspólnym `try/except Exception`:
```python
try:
    pdf_bytes = generate_report(metadata, result, norms_config)
    Path(path).write_bytes(pdf_bytes)
except Exception as exc:
    messagebox.showerror("Błąd zapisu PDF", f"Nie można zapisać raportu:\n{exc}")
```
Plik otwieramy binarnie: `Path(path).write_bytes(pdf_bytes)`.

### Success Criteria:

#### Automated Verification:

- Testy przechodzą: `python -m pytest -q`
- Mypy: `mypy app/ --strict`

#### Manual Verification:

- Pełny flow: metadane → import EEG → analiza → ekran wyników → klik "Zapisz raport PDF" → dialog → plik zapisany → otwórz PDF w przeglądarce
- Kliknięcie "Anuluj" w dialogu — nic się nie dzieje, ekran wyników pozostaje
- Symuluj błąd zapisu (ścieżka tylko do odczytu) — pojawia się komunikat po polsku

**Implementation Note**: To jest ostatni widoczny etap dla użytkownika. Przeprowadź pełny flow przed przejściem do testów.

---

## Phase 4: Unit Tests

### Overview

Testy jednostkowe dla `generate_report()` weryfikujące format wyjścia, brak µV i obecność kluczowych sekcji w outputcie.

### Changes Required:

#### 1. Fixture helpers

**File**: `tests/unit/test_pdf_generator.py`

**Intent**: Zdefiniuj minimalne fixtury `PatientMetadata`, `AnalysisResult` i `NormsConfig` (używając danych z `norms.json` lub hardcode minimal), wywołaj `generate_report()` i assertuj na wyjściu.

**Contract**: Testy muszą obejmować:
- `test_generate_report_returns_bytes` — wynik jest instancją `bytes` i nie jest pusty
- `test_pdf_starts_with_pdf_magic` — `pdf_bytes[:4] == b"%PDF"`
- `test_no_uv_values_in_output` — stringowa reprezentacja nie zawiera wzorca liczb zmiennoprzecinkowych z "µV" / "uV" / "microV"
- `test_disclaimer_present` — szukaj `b"NeuroFlag"` w raw bytes (ASCII-safe anchor z ostatniego zdania disclaimera; `DISCLAIMER_PL[:40]` zawiera polskie diakrytyki kodowane przez ReportLab jako PDFDocEncoding, nie UTF-8 — raw bytes search by nie znalazł)
- `test_all_10_cells_represented` — każdy `cell.channel + cell.band` pojawia się gdzieś w raw bytes
- `test_category_in_output` — `result.category.value.encode()` lub przynajmniej pierwsze słowo categorii w output

### Success Criteria:

#### Automated Verification:

- Wszystkie 6 testów przechodzą: `python -m pytest tests/unit/test_pdf_generator.py -v`
- Brak nowych ostrzeżeń mypy: `mypy tests/ --ignore-missing-imports`
- Pełny pytest suite: `python -m pytest -q` (zero regresji)

#### Manual Verification:

- Code coverage dla `pdf_generator.py` jest > 80% (`python -m pytest --cov=app/reports`)

---

## Testing Strategy

### Unit Tests:

- `tests/unit/test_pdf_generator.py` — 6 testów: format bytes, magic bytes, brak µV, disclaimer, 10 komórek, kategoria
- Brak nowych deps dev — bez pdfminer; weryfikacja przez `raw bytes` search

### Integration Tests:

- Pełny flow manualny (opisany w Phase 3 Manual Verification)
- Smoke test `.exe`: `dist/neuroflag/neuroflag.exe --smoke-test` po buildzie

### Manual Testing Steps:

1. Uruchom aplikację, wprowadź dane (wiek 8, płeć Z)
2. Wczytaj przykładowy plik EEG (.edf lub .vhdr)
3. Przeprowadź analizę do końca
4. Na ekranie wyników kliknij "Zapisz raport PDF"
5. Wybierz ścieżkę zapisu i potwierdź
6. Otwórz plik PDF — sprawdź 4 sekcje, brak µV, poprawne kolory RAG
7. Sprawdź stopkę z wersją aplikacji

## Performance Considerations

ReportLab generuje PDF synchronicznie w wątku UI. Przy typowych danych (10 komórek, ~20 pozycji checklist) czas generowania powinien być < 200 ms. Brak potrzeby wątku w tle — dialog zapisu i tak blokuje UI.

## References

- PRD — wymagania PDF: `context/foundation/prd.md:88, 104-106`
- Roadmap S-03: `context/foundation/roadmap.md:100-109`
- Typy domenowe: `app/domain/types.py`
- Obecny widok wyników: `app/ui/views/results_grid.py`
- AppState: `app/ui/app_window.py:12-24`
- ReportLab w spec: `neuroflag.spec:39-46`

---

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Shared Infrastructure — RAG Colors & APP_VERSION

#### Automated

- [x] 1.1 Testy przechodzą bez regresji: `python -m pytest -q` — 7410338
- [x] 1.2 Brak błędów importu: `python -c "from app.ui.components.rag_colors import RAG_COLOR_BG; from app import __version__; print(__version__)"` — 7410338
- [x] 1.3 Mypy przechodzi: `mypy app/ --strict` — 7410338

#### Manual

- [x] 1.4 Aplikacja uruchamia się normalnie i wyświetla siatkę wyników (kolory bez zmian) — 7410338

### Phase 2: PDF Generator Module

#### Automated

- [x] 2.1 Testy jednostkowe przechodzą: `python -m pytest tests/unit/test_pdf_generator.py -v` — 34cf664
- [x] 2.2 Mypy: `mypy app/reports/ --strict` — 2d9300a
- [x] 2.3 Import smoke: `python -c "from app.reports.pdf_generator import generate_report; print('ok')"` — 2d9300a

#### Manual

- [x] 2.4 Wygenerowany PDF ma 4 sekcje, siatka 2×5 z kolorami RAG, brak wartości µV — 2d9300a

### Phase 3: UI Integration

#### Automated

- [x] 3.1 Testy przechodzą: `python -m pytest -q` — ebf8481
- [x] 3.2 Mypy: `mypy app/ --strict` — ebf8481

#### Manual

- [x] 3.3 Pełny flow: metadane → EEG → analiza → siatka → klik "Zapisz" → dialog → plik PDF zapisany — ebf8481
- [x] 3.4 Kliknięcie "Anuluj" w dialogu nie powoduje błędu — ebf8481
- [x] 3.5 Błąd zapisu wyświetla komunikat po polsku — ebf8481

### Phase 4: Unit Tests

#### Automated

- [x] 4.1 Wszystkie 6 testów przechodzą: `python -m pytest tests/unit/test_pdf_generator.py -v` — 34cf664
- [x] 4.2 Brak nowych ostrzeżeń mypy: `mypy tests/ --ignore-missing-imports` — 34cf664
- [x] 4.3 Pełny suite: `python -m pytest -q` (zero regresji) — 34cf664

#### Manual

- [x] 4.4 Coverage > 80%: `python -m pytest --cov=app/reports` — 34cf664
