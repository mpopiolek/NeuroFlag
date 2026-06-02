<!-- PLAN-REVIEW-REPORT -->
# Plan Review: S-01 Formularz metryki dziecka + import pliku EEG

- **Plan**: context/changes/metadata-and-import/plan.md
- **Mode**: Deep
- **Date**: 2026-06-01
- **Verdict**: SOUND (po triażu; przed triażem: REVISE)
- **Findings**: 0 critical  2 warnings  2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | PASS ✅ |
| Lean Execution | PASS ✅ |
| Architectural Fitness | PASS ✅ (F1 fixed) |
| Blind Spots | PASS ✅ (F2, F5 fixed) |
| Plan Completeness | PASS ✅ (F3, F4 fixed) |

## Grounding

9/9 paths verified (4 exist, 5 new — expected); 4/4 symbols ✓; brief↔plan ✓

## Findings

### F1 — Circular import metadata_form ↔ file_import

- **Severity**: ❌ CRITICAL
- **Impact**: 🏃 LOW — quick decision; fix jest oczywisty i wąsko zlokalizowany
- **Dimension**: Architectural Fitness
- **Location**: Phase 2 + Phase 3
- **Detail**: metadata_form.py i file_import.py importują się nawzajem na poziomie modułu → ImportError przy starcie aplikacji.
- **Fix**: Lazy imports wewnątrz callbacków _on_next / _on_back (import wewnątrz ciała metody).
- **Decision**: FIXED — dodano lazy import pattern do kontraktu obu widoków w plan.md.

### F2 — Sex RadioButton: brak domyślnej wartości → ValueError w runtime

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix jest oczywisty i wąsko zlokalizowany
- **Dimension**: Blind Spots
- **Location**: Phase 2 — MetadataFormView
- **Detail**: StringVar dla płci bez wartości domyślnej → Sex("") rzuca ValueError przy kliknięciu 'Dalej →' bez zaznaczenia opcji.
- **Fix**: sex_var = StringVar(value="Z") — "Dziewczynka" wstępnie zaznaczona.
- **Decision**: FIXED — zaktualizowano kontrakt MetadataFormView w plan.md.

### F3 — eeg_file API: validate_extension nie wpięte w validate_eeg_header

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix jest oczywisty i wąsko zlokalizowany
- **Dimension**: Plan Completeness
- **Location**: Phase 3 — eeg_file.py kontrakt
- **Detail**: validate_eeg_header() nie wołał validate_extension() → plik .txt dawał niejasny błąd MNE zamiast "Nieobsługiwane rozszerzenie"; test manualny 3.5 nieosiągalny.
- **Fix**: Zaktualizowano docstring validate_eeg_header() — jawnie Step 1: validate_extension(path).
- **Decision**: FIXED — zaktualizowano kontrakt validate_eeg_header w plan.md.

### F4 — test_types.py: EPILEPSY samodzielnie już przetestowane

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix jest oczywisty
- **Dimension**: Plan Completeness
- **Location**: Phase 4 — test_types.py §2
- **Detail**: Plan prosił o 3 testy; EPILEPSY samodzielnie już pokryte przez test_patient_metadata_single_exclusion().
- **Fix**: Zmieniono opis na "2 brakujące testy: BRAIN_INJURY i INTELLECTUAL_DISABILITY samodzielnie".
- **Decision**: FIXED — zaktualizowano Phase 4 w plan.md.

### F5 — AppState.eeg_path nie zerowane przy rekonstrukcji FileImportView

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix jest oczywisty
- **Dimension**: Blind Spots
- **Location**: Phase 3 — FileImportView __init__
- **Detail**: Back-navigation tworzy nową FileImportView, ale stary eeg_path w AppState może powodować ready_for_analysis() == True mimo pustego UI.
- **Fix**: FileImportView.__init__ ustawia app_state.eeg_path = None jako pierwszy krok.
- **Decision**: FIXED — dodano note do kontraktu FileImportView w plan.md.
