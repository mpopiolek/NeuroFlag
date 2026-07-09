# Zgłaszanie błędów nieoczekiwanych — Implementation Plan

## Overview

Dodanie mechanizmu zgłaszania błędów na GitHubie z pre-fill diagnostyki sesji dla **błędów nieoczekiwanych** (`PipelineError` z kodem `unexpected_error` oraz nieobsłużonych wyjątków GUI) oraz dla **ręcznego zgłoszenia** z widoku Informacje. Użytkownik otwiera przeglądarkę, widzi wstępnie wypełnioną sekcję techniczną, dopisuje opis i wysyła issue sam.

## Current State Analysis

- Przycisk w Informacjach: `info_dialog.py:45-53` → `webbrowser.open(GITHUB_NEW_ISSUE_URL)` bez parametrów.
- Błędy analizy: `AnalysisRunner._worker` (`analysis.py:134-138`) owija nieznane wyjątki jako `unexpected_error` z samą nazwą klasy; typ ginie w `user_message_pl`.
- Wyświetlanie: `FileImportView.show_analysis_error()` (`file_import.py:270-276`) — status label, brak akcji zgłoszenia.
- Brak `sys.excepthook` / `report_callback_exception` w `app/`.
- Segmentacja: `detect_task_segments()` (`pipeline.py:251-263`) — wynik nie trafia do `AppState`.
- Szablon issue: `.github/ISSUE_TEMPLATE/bug_report.md` — sekcje ręczne; brak auto-fill.

### Key Discoveries

- `AppState` (`app_window.py:19-35`) ma `eeg_path`, `available_channels`, `channel_overrides`, `anonymize_header`, `norms_config` — wystarczy do diagnostyki bez PII.
- `VIEW_STEP` (`navigation.py:12-19`) mapuje widok na krok; overlay analizy wymusza krok 3 (`app_window.py:248-249`).
- `get_missing_canonical()` (`channels.py:67-77`) daje status C3/O1 dla nagłówka; **mapowanie ręczne** (`channel_overrides`) wymaga osobnej gałęzi `mapped` w `collect_bug_report_context`.
- GitHub obsługuje `?template=bug_report.md&title=&body=` (URL-encoded).

## Desired End State

1. **`unexpected_error` po analizie** — komunikat `✗ …` na ekranie importu + w stopce przycisk „Zgłoś błąd na GitHubie”; klik otwiera issue z pre-fill.
2. **Nieobsłużony wyjątek GUI** — modal CTk (polski komunikat) + ten sam przycisk zgłoszenia.
3. **Informacje → Zgłoś błąd** — ten sam pre-fill diagnostyki sesji (bez kodu/typu błędu; pole „Opis problemu” puste do uzupełnienia).
4. **Treść auto-fill** (sekcja „Diagnostyka (auto-wypełnione)” w body):
   - wersja NeuroFlag
   - Windows (wersja + architektura)
   - wersje MNE / NumPy (gdy import dostępny)
   - kod błędu + komunikat PL (tylko przy `unexpected_error`)
   - typ wyjątku (tylko przy `unexpected_error`)
   - krok aplikacji (Dane / Plik / Analiza / Wynik / Informacje / Historia)
   - rozszerzenie pliku EEG (`.edf` / `.vhdr` / `.eeg` / brak)
   - liczba kanałów w nagłówku
   - status C3/O1 (obecne / brak / mapowanie ręczne)
   - znaczniki OO/OZ/ZP: wykryte z adnotacji / fallback 3×3 min / nie dotyczy / nieznane
   - checkbox „Wyczyść dane identyfikacyjne”: tak/nie
   - wersja `norms.json`
5. **Poza auto-fill** — użytkownik uzupełnia kroki reprodukcji, zrzut ekranu, oczekiwane zachowanie.

### Weryfikacja końcowa

- `python -m pytest -q` i `mypy app/ --strict` — pass
- Symulacja `unexpected_error` → przycisk w stopce → GitHub z body zawierającym diagnostykę
- Informacje → przycisk → body z wersją i krokiem, bez inicjałów/ścieżek

## What We're NOT Doing

- Przycisk zgłoszenia przy oczekiwanych kodach (`missing_channels`, `insufficient_duration`, …)
- Pełny traceback / ścieżki plików użytkownika w body issue
- Lista wszystkich nazw kanałów (poza statusem C3/O1)
- Dane `PatientMetadata` (inicjały, rok, diagnozy)
- GitHub API, token, automatyczne tworzenie issue
- Automatyczne załączanie screenshotów lub plików EEG
- Persystentny plik logów na dysku
- Zmiana flow RAG / algorytmu / pipeline poza snapshotem segmentacji

## Implementation Approach

Wydzielić logikę zgłoszeń do `app/ui/bug_report.py`. Pipeline raportuje milestone segmentacji przez mutowalny `AnalysisDiagnostics` przekazywany z `AnalysisRunner`. UI: warunkowa stopka w `FileImportView` dla `unexpected_error`; modal `UncaughtErrorDialog` dla globalnego hooka; podmiana `_open_github_issue` w Informacjach na wersję z kontekstem.

## Critical Implementation Details

**Globalny hook a wątek analizy:** `AnalysisRunner` już łapie wyjątki w wątku — hook dotyczy wyłącznie main thread / Tk callback. Nie duplikować dialogu dla `unexpected_error` (stopka wystarczy).

**Sanityzacja:** `eeg_path` → tylko `.suffix.lower()`; nigdy `path.name` ani `str(path)`. Komunikat błędu — przepuścić `user_message_pl` (kontrolowany przez domenę); typ wyjątku — `type(exc).__name__` bez `str(exc)` (może zawierać ścieżki).

**Limit URL:** Jeśli zakodowane body > 6000 znaków, skopiuj body do schowka (`tkinter` clipboard) i otwórz krótszy URL z instrukcją w body.

## Phase 1: Moduł diagnostyki i URL GitHub

### Overview

Wspólny builder kontekstu zgłoszenia i otwierania GitHub Issue z pre-fill.

### Changes Required:

#### 1. Typy diagnostyczne

**File**: `app/domain/types.py`

**Intent**: Dodać strukturę przechowującą snapshot analizy i kontekst zgłoszenia bez PII.

**Contract**: Nowe frozen dataclass:
- `SegmentDetectionMode`: `Literal["annotations", "fallback", "not_reached", "unknown"]`
- `AnalysisDiagnostics` z polami: `segment_mode` (bez liczby kanałów — ta pochodzi z AppState)
- `BugReportContext` z polami: wersja app, OS string, opcjonalne wersje lib, opcjonalny `error_code` / `error_message_pl` / `exception_type_name`, krok PL, suffix EEG, `header_channel_count`, `c3_o1_status` (`present` | `missing` | `mapped`), `segment_mode`, `anonymize_header`, `norms_version`, flaga `manual_report: bool`

#### 2. Moduł bug_report

**File**: `app/ui/bug_report.py` (nowy)

**Intent**: Zbierać kontekst z `AppWindow`/`AppState`, formatować body po polsku, budować URL, otwierać przeglądarkę.

**Contract**:
- `collect_bug_report_context(app_window, *, error: PipelineError | None = None, exception_type_name: str | None = None, manual: bool = False) -> BugReportContext`
- `c3_o1_status`: `mapped` gdy `bool(app_state.channel_overrides)`; `present` gdy brak overrides i `get_missing_canonical(app_state.available_channels) == []`; w pozostałych `missing`
- `header_channel_count = len(app_state.available_channels)` (0 gdy brak wczytanego pliku); pole w `BugReportContext` jako `header_channel_count: int`
- `format_bug_report_body(ctx: BugReportContext) -> str` — sekcja markdown „## Diagnostyka (auto-wypełnione)” + krótka nota „Uzupełnij sekcje szablonu poniżej”
- `build_github_issue_url(ctx: BugReportContext) -> str` — `GITHUB_NEW_ISSUE_URL` + `template=bug_report.md` + `labels=bug` + `title=[Bug] …` + `body=…` (urllib.parse.quote)
- `open_bug_report(ctx: BugReportContext) -> None` — `webbrowser.open`; przy `OSError` → `messagebox.showerror` (jak dziś); przy długim URL → clipboard fallback

Krok aplikacji: `analysis_in_progress` → `"Analiza (overlay)"`; w przeciwnym razie mapowanie `type(_current_view)`:
- `MetadataFormView` → `"Dane"`
- `FileImportView` / `ChannelMappingView` → `"Plik"`
- `ResultsGridView` → `"Wynik"`
- `InfoView` → `"Informacje"` (poza `VIEW_STEP`)
- `HistoryView` → `"Historia"` (poza `VIEW_STEP`)
- fallback → `"Nieznany"`

Wersje lib: `try: import mne, numpy` — tylko w body, nie crash przy braku.

#### 3. Testy jednostkowe

**File**: `tests/unit/test_bug_report.py` (nowy)

**Intent**: Zweryfikować sanityzację i URL bez uruchamiania GUI.

**Contract**:
- Body nie zawiera `C:\`, inicjałów, `@` z metadata
- URL zawiera `template=bug_report.md`, `github.com/mpopiolek/NeuroFlag`
- `manual_report=True` → brak `error_code` w body
- `exception_type_name="RuntimeError"` → obecny w body

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/test_bug_report.py -q`
- `mypy app/ --strict`

#### Manual Verification:

- Wywołanie `format_bug_report_body` w REPL — czytelna sekcja PL bez PII

**Implementation Note**: Po przejściu testów i mypy — pauza na potwierdzenie manualne przed Phase 2.

---

## Phase 2: Snapshot segmentacji w pipeline

### Overview

Zapisać tryb detekcji OO/OZ/ZP w `AppState` podczas analizy, aby trafił do raportu przy `unexpected_error`.

### Changes Required:

#### 1. Refaktor detekcji segmentów

**File**: `app/domain/pipeline.py`

**Intent**: Zwracać tryb segmentacji obok słownika segmentów bez zmiany publicznego API `run()` return type.

**Contract**:
- Wewnętrzna funkcja `_detect_task_segments_with_mode(raw) -> tuple[dict[str, tuple[float, float]], SegmentDetectionMode]`
- Logika jak dziś: pełne adnotacje → `"annotations"`; `_fallback_segments` → `"fallback"`; `missing_task_segments` → raise (bez zmiany)
- `detect_task_segments()` deleguje do helpera (zachowanie publiczne)

#### 2. Aktualizacja pipeline.run

**File**: `app/domain/pipeline.py`

**Intent**: Aktualizować przekazany obiekt diagnostyczny na milestone segmentacji.

**Contract**: Nowy opcjonalny parametr `diagnostics: AnalysisDiagnostics | None = None`. Na początku `run`: jeśli `diagnostics` podany, `diag = replace(diagnostics, segment_mode="not_reached")`. Po udanej detekcji: `diag = replace(diag, segment_mode=mode)`. **Zwracany typ**: `tuple[tuple[float, ...], AnalysisDiagnostics | None]` — drugi element to zaktualizowany snapshot (lub `None` gdy `diagnostics` nie przekazano). Caller (`AnalysisRunner`) przypisuje drugi element do `app_state.last_analysis_diagnostics`.

#### 3. AppState + AnalysisRunner

**File**: `app/ui/app_window.py`, `app/ui/views/analysis.py`

**Intent**: Tworzyć i przekazywać diagnostykę; zapisać typ wyjątku przy wrapowaniu.

**Contract**:
- `AppState.last_analysis_diagnostics: AnalysisDiagnostics | None = None`
- `AppState.last_exception_type_name: str | None = None`
- `AnalysisRunner` przed `pipeline.run`: `diag = AnalysisDiagnostics(segment_mode="unknown"); app_state.last_analysis_diagnostics = diag`
- `amplitudes, updated_diag = pipeline.run(..., diagnostics=diag)`; jeśli `updated_diag is not None`: `app_state.last_analysis_diagnostics = updated_diag`
- W `except Exception`: `app_state.last_exception_type_name = type(exc).__name__` przed utworzeniem `PipelineError("unexpected_error", …)`
- Przekazać `diagnostics=diag` do `pipeline.run(...)`

#### 4. Test pipeline

**File**: `tests/unit/test_pipeline.py`

**Intent**: Potwierdzić ustawianie `segment_mode` przy mock raw z adnotacjami vs fallback.

**Contract**: Test z istniejącym fixture — po `amplitudes, updated = run(..., diagnostics=diag)` sprawdzić `updated is not None` i `updated.segment_mode in ("annotations", "fallback")` zależnie od fixture.

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/test_pipeline.py tests/unit/test_bug_report.py -q`
- `mypy app/ --strict`

#### Manual Verification:

- Brak regresji w istniejących testach pipeline

---

## Phase 3: UI błędu nieoczekiwanego w analizie

### Overview

Przy `unexpected_error` pokazać przycisk zgłoszenia w stopce ekranu importu.

### Changes Required:

#### 1. Przechowanie ostatniego błędu

**File**: `app/ui/app_window.py` lub `AppState`

**Intent**: Stopka musi wiedzieć, czy pokazać przycisk zgłoszenia.

**Contract**: `AppState.last_pipeline_error: PipelineError | None = None` — ustawiane w `finish_analysis_overlay` gdy `error is not None`; czyszczone przy sukcesie i nowej analizie.

#### 2. Stopka zgłoszenia w FileImportView

**File**: `app/ui/views/file_import.py`

**Intent**: Gdy `error.code == "unexpected_error"`, stopka **zastępuje** primary „Analizuj” przyciskiem „Zgłoś błąd na GitHubie” (API stopki ma tylko jeden slot primary — bez rozszerzania `set_footer`). Wstecz bez zmian; retry analizy przez ponowne wczytanie pliku lub restart aplikacji.

**Contract**:
- `show_analysis_error(error)` — jeśli `unexpected_error`, woła `set_footer` z `primary_text="Zgłoś błąd na GitHubie"` i `primary_cmd=…` → `open_bug_report(collect_bug_report_context(...))`; **nie** woła `restore_import_footer()`
- Dla pozostałych kodów błędu — bez zmian (`restore_import_footer()` jak dziś)
- `restore_import_footer()` / sukces — przywraca normalną stopkę z „Analizuj”, czyści `last_pipeline_error`

#### 3. Tekst informacyjny (opcjonalny)

**File**: `app/ui/views/file_import.py`

**Intent**: Krótka wskazówka pod statusem: „Możesz zgłosić ten błąd deweloperowi przyciskiem w stopce.”

**Contract**: Tylko gdy `unexpected_error`; `font_small`, `COLOR_TEXT_SECONDARY`.

### Success Criteria:

#### Automated Verification:

- `mypy app/ --strict`
- `python -m pytest -q` (pełny suite)

#### Manual Verification:

- Wymusić `unexpected_error` (np. tymczasowy `raise RuntimeError` w pipeline) → status + przycisk w stopce
- Klik przycisku → GitHub z diagnostyką, bez ścieżek pliku

---

## Phase 4: Globalny excepthook + pre-fill Informacje

### Overview

Obsłużyć nieobsłużone wyjątki GUI i podłączyć pre-fill do ręcznego zgłoszenia.

### Changes Required:

#### 1. Modal nieobsłużonego błędu

**File**: `app/ui/components/uncaught_error_dialog.py` (nowy)

**Intent**: CTkToplevel z komunikatem PL i przyciskiem zgłoszenia (nie zamyka aplikacji automatycznie).

**Contract**:
- Parametry: `parent`, `app_window`, `exc_type_name: str` (bez `exc_value` w UI — `str(exc)` może zawierać ścieżki)
- Treść modalu: ogólny komunikat PL + typ wyjątku (`exc_type_name`); **nie** wyświetlać `str(exc)` ani tracebacku
- Przyciski: „Zgłoś błąd na GitHubie”, „Zamknij”
- Zgłoszenie: `collect_bug_report_context(..., exception_type_name=exc_type_name)` + syntetyczny `PipelineError("unexpected_error", "Nieobsłużony błąd aplikacji.")` lub osobne pola w kontekście

#### 2. Rejestracja hooków

**File**: `app/ui/exception_hooks.py` (or `app/main.py` / `app/ui/app_window.py`)

**Intent**: Przechwycić nieobsłużone wyjątki w main thread.

**Contract**:
- `sys.excepthook = _gui_excepthook` — schedule dialog via `app.after(0, …)` jeśli `AppWindow` istnieje
- `tkinter.Tk.report_callback_exception` override na instancji CTk (CustomTkinter dziedziczy z Tk)
- Hook ignoruje `KeyboardInterrupt` / `SystemExit`
- Przechowuj referencję `AppWindow` w module-level weak ref do kontekstu

#### 3. Informacje — pre-fill ręczny

**File**: `app/ui/components/info_dialog.py`, `app/ui/views/info_view.py`

**Intent**: Przycisk „Zgłoś błąd” używa `open_bug_report` z kontekstem sesji.

**Contract**:
- `build_info_content(parent, *, wraplength, app_window: AppWindow | None = None)`
- `_open_github_issue(app_window)` → `collect_bug_report_context(app_window, manual=True)` gdy `app_window` dostępny; fallback na stary URL przy `None`
- `InfoView` przekazuje `self._app_window` do `build_info_content`

#### 4. Aktualizacja szablonu issue (opcjonalne, poza MVP)

**File**: `.github/ISSUE_TEMPLATE/bug_report.md`

**Intent**: Dodać komentarz, że sekcja diagnostyki może być pre-fill z aplikacji. **Poza zakresem MVP** — wykonać tylko jeśli zespół chce zsynchronizować szablon z auto-fill; nie blokuje implementacji.

**Contract**: Jedna linia w „Dodatkowy kontekst” — bez zmiany YAML labels.

#### 5. Testy

**File**: `tests/unit/test_bug_report.py`

**Intent**: `manual=True` → body zawiera wersję i krok, nie zawiera „Kod błędu” gdy brak error.

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/test_bug_report.py tests/unit/test_info_content.py -q`
- `mypy app/ --strict`

#### Manual Verification:

- Informacje → Zgłoś błąd → GitHub z diagnostyką bieżącej sesji
- Sztuczny `raise` w handlerze przycisku (dev) → modal + zgłoszenie
- Potwierdzenie: body issue nie zawiera inicjałów ani ścieżek dysku

---

## Testing Strategy

### Unit Tests:

- `test_bug_report.py`: URL encoding, sanityzacja PII, manual vs error context, długi body → clipboard flag (mock clipboard)
- `test_pipeline.py`: `segment_mode` na diagnostics
- `test_info_content.py`: bez regresji URL repo

### Integration Tests:

- Brak E2E GUI — weryfikacja manualna

### Manual Testing Steps:

1. Uruchom app → Informacje → Zgłoś błąd → sprawdź pre-fill (wersja, Windows, krok „Informacje”)
2. Wczytaj plik .edf → wymuś `unexpected_error` → przycisk w stopce → sprawdź suffix, liczbę kanałów, segment_mode
3. Dev: raise w callback → modal globalny
4. Odznacz „Wyczyść dane…” → powtórz błąd → body pokazuje „nie”

## Performance Considerations

Zbieranie kontekstu to kilka odczytów ze stanu + opcjonalne `import mne` — pomijalne. URL build O(n) na długości body; clipboard fallback rzadki.

## Migration Notes

Brak migracji danych. Istniejący flow błędów oczekiwanych bez zmian.

## References

- Istniejący przycisk: `app/ui/components/info_dialog.py:111-115`
- `unexpected_error` wrap: `app/ui/views/analysis.py:134-138`
- Szablon issue: `.github/ISSUE_TEMPLATE/bug_report.md`
- RODO copy: `app/ui/context_copy.py`
- Plan brief: `context/changes/github-bug-report-unexpected/plan-brief.md`

## Progress

### Phase 1: Moduł diagnostyki i URL GitHub

#### Automated

- [x] 1.1 `python -m pytest tests/unit/test_bug_report.py -q` — 620a365
- [x] 1.2 `mypy app/ --strict` — 620a365

#### Manual

- [x] 1.3 Body w REPL — sekcja PL bez PII — 620a365

### Phase 2: Snapshot segmentacji w pipeline

#### Automated

- [x] 2.1 `python -m pytest tests/unit/test_pipeline.py tests/unit/test_bug_report.py -q` — 620a365
- [x] 2.2 `mypy app/ --strict` — 620a365

#### Manual

- [x] 2.3 Brak regresji pipeline w pełnym `pytest -q` — 620a365

### Phase 3: UI błędu nieoczekiwanego w analizie

#### Automated

- [x] 3.1 `mypy app/ --strict` — 620a365
- [x] 3.2 `python -m pytest -q` — 620a365

#### Manual

- [x] 3.3 Wymuszony `unexpected_error` → status + stopka → GitHub z diagnostyką — 620a365

### Phase 4: Globalny excepthook + pre-fill Informacje

#### Automated

- [x] 4.1 `python -m pytest tests/unit/test_bug_report.py tests/unit/test_info_content.py -q` — 620a365
- [x] 4.2 `mypy app/ --strict` — 620a365

#### Manual

- [x] 4.3 Informacje → pre-fill sesji bez kodu błędu — 620a365
- [x] 4.4 Nieobsłużony wyjątek GUI → modal + zgłoszenie (`python -m app.main --debug-crash-gui`, potem klik „Informacje”) — 620a365
- [x] 4.5 Body issue bez inicjałów i ścieżek dysku — 620a365
