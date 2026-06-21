<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Pipeline EEG i wyniki

- **Plan**: context/changes/eeg-pipeline-and-results/plan.md
- **Scope**: Pełny plan (Fazy 1–4)
- **Date**: 2026-06-09
- **Verdict**: NEEDS ATTENTION → APPROVED po triage
- **Findings**: 0 critical  7 warnings  4 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

## Findings

### F1 — analysis_result zapisywane z wątku roboczego

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — race condition między wątkiem a GUI
- **Dimension**: Safety & Quality (race condition)
- **Location**: app/ui/views/analysis.py:94
- **Detail**: `self._app_state.analysis_result = result` wywoływane z wątku roboczego zamiast z callbacka after(0,...).
- **Fix**: Przeniesiono przypisanie do `_on_done`, przekazano `result` przez parametr.
- **Decision**: FIXED

### F2 — Angielskie OS-errors w komunikatach pipeline

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision
- **Dimension**: Safety & Quality (UI language)
- **Location**: app/domain/pipeline.py:152, 157
- **Detail**: `f"Nie można odczytać pliku EEG: {exc}"` osadzał angielski tekst OSError.
- **Fix**: Zamieniono `{exc}` na stały tekst PL.
- **Decision**: FIXED

### F3 — Angielskie OS-errors w EEGFileError

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision
- **Dimension**: Safety & Quality (UI language)
- **Location**: app/domain/eeg_file.py:52, 54
- **Detail**: `f"Plik niedostępny: {exc}"` — analogicznie jak F2.
- **Fix**: Zamieniono na stały tekst PL.
- **Decision**: FIXED

### F4 — EEGFileError z validate_extension gubi komunikat PL

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision
- **Dimension**: Safety & Quality (reliability)
- **Location**: app/domain/pipeline.py:141
- **Detail**: `validate_extension` wywoływane przed blokiem try; `EEGFileError` trafiał do analysis.py:100 i gubił oryginalny komunikat.
- **Fix**: Opakowano `validate_extension` w try/except EEGFileError → PipelineError w `_load_raw`.
- **Decision**: FIXED

### F5 — Cichy return w ResultsGridView bez komunikatu błędu

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision
- **Dimension**: Safety & Quality (reliability)
- **Location**: app/ui/views/results_grid.py:53-54
- **Detail**: Gdy `analysis_result is None` — widok renderował pusty frame.
- **Fix**: Dodano etykietę PL z błędem i przycisk powrotu.
- **Decision**: FIXED

### F6 — NormsLoadError bez code/user_message_pl jak PipelineError

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff
- **Dimension**: Pattern Consistency
- **Location**: app/domain/norms.py:101
- **Detail**: `NormsLoadError` bez ustrukturyzowanych pól `code` i `user_message_pl`.
- **Fix A ⭐ Applied**: Dodano `code` i `user_message_pl` do `NormsLoadError.__init__`.
- **Decision**: FIXED via Fix A

### F7 — Kod błędu po angielsku w panelu Szczegóły

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision
- **Dimension**: Scope Discipline (UI PL requirement)
- **Location**: app/ui/views/analysis.py:148
- **Detail**: `"Kod błędu: missing_channels"` — identyfikator angielski widoczny dla pedagoga.
- **Fix**: Dodano `_ERROR_CODE_PL` mapę i `_error_code_pl()` helper; panel pokazuje "Typ błędu: Brak wymaganych kanałów (C3/O1)".
- **Decision**: FIXED

### F8 — Nadmiarowy except Exception po except OSError w _load_raw

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW
- **Dimension**: Safety & Quality
- **Location**: app/domain/pipeline.py:154
- **Detail**: Duplikat kodu — except Exception łapał też OSError.
- **Fix**: Połączono w `except (OSError, Exception)`.
- **Decision**: FIXED

### F9 — _load_mne() wołany dwukrotnie

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW
- **Dimension**: Pattern Consistency
- **Location**: app/domain/pipeline.py:168
- **Detail**: Moduł mne importowany osobno w `_amplitude_for_norm`.
- **Decision**: SKIPPED

### F10 — EXTRA: observation_checklist poza scope planu

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW
- **Dimension**: Scope Discipline
- **Location**: app/domain/types.py, norms.py, norms.json
- **Detail**: `ObservationChecklist` nie był w żadnej fazie S-02; spójny dodatek z innego kontekstu.
- **Decision**: SKIPPED

### F11 — generate_test_edfs.py: set_channel_types EOG niespójność

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW
- **Dimension**: Pattern Consistency
- **Location**: tests/fixtures/generate_test_edfs.py:76
- **Detail**: Tylko test_standard.edf ustawia typ EOG.
- **Decision**: SKIPPED
