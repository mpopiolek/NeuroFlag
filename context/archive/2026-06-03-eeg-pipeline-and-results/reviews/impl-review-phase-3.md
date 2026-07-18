<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Pipeline EEG i wyniki

- **Plan**: context/changes/eeg-pipeline-and-results/plan.md
- **Scope**: Phases 1–3 of 4
- **Date**: 2026-06-09
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical, 5 warnings, 4 observations

## Verdicts

| Dimension            | Verdict |
|----------------------|---------|
| Plan Adherence       | WARNING — 1 DRIFT (norms.py recommendation_rules obowiązkowy zamiast domyślny) |
| Scope Discipline     | WARNING — 2 EXTRA (ObservationChecklist — bezpieczne przygotowanie pod S-03) |
| Safety & Quality     | WARNING — 4 findings (brak CRITICAL; µV nigdy nie wycieka do UI) |
| Architecture         | PASS |
| Pattern Consistency  | WARNING — AppState pod TYPE_CHECKING w nowych widokach vs. runtime w starych |
| Success Criteria     | WARNING — automated PASS; manual 1.3, 1.4, 3.4–3.6 PENDING (brak pliku EEG) |

## Findings

### F1 — getattr(sys, "_MEIPASS") bez default — crash przy starcie .exe

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: app/domain/norms.py:127
- **Detail**: `getattr(sys, "_MEIPASS")` (2 arg) rzuca `AttributeError` gdy atrybut nie istnieje. Jeśli aplikacja jest spakowana i `norms.json` nie leży obok `.exe`, wyjątek propaguje przez `norms.load()` i NIE jest łapany przez `except NormsLoadError` w `main()` — aplikacja crashuje cicho bez dialogu dla użytkownika.
- **Fix**: Zmień na `getattr(sys, "_MEIPASS", None)`; gdy wynik to `None` rzuć jawny `NormsLoadError` z czytelnym komunikatem.
  - Strength: Eliminuje klasę crash przy starcie; zachowuje istniejący dialog błędu.
  - Tradeoff: 2-3 linie kodu.
  - Confidence: HIGH — identyczny wzorzec używany w analogicznych projektach PyInstaller.
  - Blind spot: Brak smoke-testu frozen path w CI.
- **Decision**: FIXED — getattr(sys, "_MEIPASS", None) + NormsLoadError gdy None

### F2 — cancel_requested bez synchronizacji wątków

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/ui/views/analysis.py:30,67
- **Detail**: Flaga `cancel_requested` jest pisana na main thread (`_on_cancel`) i czytana na daemon worker przez `lambda`. Działa w CPython dzięki GIL, ale jest formalnie niezdefiniowane w threading memory model Pythona. Idiomatycznym rozwiązaniem jest `threading.Event`.
- **Fix**: Zastąp `AppState.cancel_requested: bool` przez `cancel_event: threading.Event`; `_on_cancel` wywołuje `.set()`; worker sprawdza `.is_set()`.
  - Strength: Jawne, dokumentuje intencję; eliminuje ukryte zależności od GIL.
  - Tradeoff: Wymaga aktualizacji AppState, analysis.py i ewentualnie Fazy 4.
  - Confidence: MEDIUM — GIL chroni w praktyce, ale warto naprawić przed Fazą 4.
  - Blind spot: Faza 4 (picker kanałów) też będzie używać tego wzorca.
- **Decision**: FIXED — threading.Event (cancel_event) w AppState; clear()/set()/is_set w analysis.py i results_grid.py

### F3 — assert eeg_path usuwany przez python -O

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/ui/views/analysis.py:73
- **Detail**: `assert self._app_state.eeg_path is not None` jest usuwany przy `python -O` (i PyInstaller `--optimize`). Jeśli osiągnięty z `eeg_path = None`, `pipeline.run(None, …)` rzuca `TypeError` łapany tylko przez bare `except Exception`, co daje nieprzydatny komunikat `"Nieoczekiwany błąd analizy: TypeError"`.
- **Fix**: Zamień assert na jawny guard: `if self._app_state.eeg_path is None: self.after(0, self._on_done, PipelineError("no_file", "Brak wybranego pliku EEG.")); return`.
- **Decision**: FIXED — jawny PipelineError("no_file", …) zamiast assert

### F4 — assert analysis_result usuwany przez python -O w ResultsGridView

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/ui/views/results_grid.py:52
- **Detail**: `assert app_state.analysis_result is not None` usuwany przez `-O`. `result = None` → `result.category` na linii 58 rzuca `AttributeError` łapany przez Tkinter event loop (cichy, bez komunikatu użytkownikowi).
- **Fix**: Zamień assert na `if app_state.analysis_result is None: return` (lub show_view z powrotem do FileImportView).
- **Decision**: FIXED — jawny guard if None: return zamiast assert

### F5 — AppState pod TYPE_CHECKING w nowych widokach vs. runtime w starych

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/ui/views/analysis.py:10–11, app/ui/views/results_grid.py:9–10
- **Detail**: `metadata_form.py` i `file_import.py` importują `AppState` bezwarunkowo w runtime, `AppWindow` pod `TYPE_CHECKING`. Nowe widoki (`analysis.py`, `results_grid.py`) wrzucają oba pod `TYPE_CHECKING`. Jeśli ktoś doda `isinstance(x, AppState)` w nowych widokach, dostanie `NameError` którego mypy nie wykryje.
- **Fix**: Przenieś `AppState` z bloku `TYPE_CHECKING` do zwykłego importu w `analysis.py` i `results_grid.py` — zgodnie z wzorcem siblings.
- **Decision**: FIXED — AppState przeniesiony do runtime import w obu nowych widokach

### F6 — DRIFT: recommendation_rules obowiązkowy zamiast z domyślnym fallback

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: app/domain/norms.py:281–289
- **Detail**: Plan mówił "Default fallback for both if missing." `category_descriptions` ma cichy fallback (linie 291–294) — OK. Ale `recommendation_rules` rzuca `NormsLoadError` gdy brak obu `recommendation_rules` i `recommendation_threshold`. Zachowanie jest bezpieczniejsze niż plan zakładał, ale niezgodne z literą specyfikacji. Produkcja nienaruszona bo `norms.json` zawiera blok.
- **Fix**: Udokumentować decyzję w planie jako intentional deviation — lub dodać cichy fallback na `_DEFAULT_RECOMMENDATION_RULES` dla maksymalnej zgodności.
- **Decision**: FIXED (Fix A) — adnotacja "Intentional deviation" dodana do plan.md §Phase 2 §Loader norms

### F7 — raw.copy() wywoływane 10× w pętli (Performance)

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/domain/pipeline.py:175
- **Detail**: Pętla po 10 normach wywołuje `raw.copy().crop(…).pick(…)` dla każdej normy. Cache jednej kopii per `(task, channel)` zredukowałoby pracę ~3–4×.
- **Decision**: SKIPPED — optymalizacja po pomiarach manualnych (manual test 1.3)

### F8 — _load_mne() wywoływany per norma wewnątrz pętli

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/domain/pipeline.py:167
- **Detail**: `_load_mne()` owija `import mne` w try/except; wywołanie raz przed pętlą jest czystsze.
- **Decision**: SKIPPED — niska priorytet; naprawić przy optymalizacji F7

### F9 — mean_z < mean_k nie walidowane per norma

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/domain/norms.py (walidacja w load())
- **Detail**: Brak sprawdzenia `mean_z < mean_k` per wpis normy powoduje ciche błędne klasyfikacje.
- **Decision**: FIXED — walidacja `mean_z >= mean_k` → NormsLoadError dodana do pętli post-parse w load()

### F10 — Częściowe anotacje (2/3 zadań znalezione) zastąpiane fallbackiem

- **Severity**: 👁 OBSERVATION
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: app/domain/pipeline.py:123–125
- **Detail**: Nagranie z OO i OZ prawidłowo zanotowanymi ale bez ZP odpada do fallbacku 180s bez informacji które zadania znaleziono.
- **Decision**: SKIPPED — ulepszyć komunikat PipelineError przy okazji Fazy 4
