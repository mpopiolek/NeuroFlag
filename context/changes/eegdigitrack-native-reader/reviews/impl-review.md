<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Natywny czytnik EEGDigiTrack

- **Plan**: context/changes/eegdigitrack-native-reader/plan.md
- **Scope**: Fazy 1–4 (pełny plan)
- **Date**: 2026-06-29
- **Verdict**: APPROVED (po poprawkach triage)
- **Findings**: 2 critical  5 warnings  7 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | PASS (po poprawkach) |
| Architecture | PASS |
| Pattern Consistency | PASS (po poprawkach) |
| Success Criteria | PASS |

## Findings

### F1 — sfreq=0 rzuca ValueError zamiast EEGFileError

- **Severity**: ❌ CRITICAL
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/domain/eeg_file.py:93
- **Detail**: Gdy offset 0x0004=0 (korupcja), mne.create_info() rzuca ValueError — nie EEGFileError. pipeline._load_raw() nie łapie ValueError.
- **Fix**: Dodaj guard `if sfreq <= 0: raise EEGFileError(...)` po rozpakowaniu sfreq.
- **Decision**: FIXED — 44cdd02

### F2 — Fixture generator: ciche przycinanie → korupcja sample_digitrack.eeg

- **Severity**: ❌ CRITICAL
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: tests/fixtures/generate_digitrack_fixture.py:57–64
- **Detail**: Brak walidacji długości wycinka; nagłówek deklaruje TARGET_BLOCKS niezależnie od faktycznej liczby skopiowanych bajtów.
- **Fix**: Sprawdź `actual_blocks = len(data_section)//(n_ch_data*2)`, wyjdź gdy < TARGET_BLOCKS.
- **Decision**: FIXED — 44cdd02

### F3 — struct.error na skróconym pliku ucieka poza EEGFileError

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/domain/eeg_file.py:93–106
- **Detail**: Plik z sygnaturą ale zbyt krótki na pełny nagłówek rzuca struct.error.
- **Fix**: try/except struct.error → EEGFileError("Uszkodzony nagłówek: zbyt krótki plik.")
- **Decision**: FIXED — 44cdd02

### F4 — total_blocks=0 zwraca pusty RawArray → IndexError w pipeline

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/domain/eeg_file.py:123
- **Detail**: Guard `data_start < 0` nie łapie total_blocks==0 (data_start=len(data)≥0).
- **Fix**: `if total_blocks == 0: raise EEGFileError(...)`
- **Decision**: FIXED — 44cdd02

### F5 — Brak limitu rozmiaru pliku w read_raw_digitrack()

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/domain/eeg_file.py:84
- **Detail**: fh.read() bez limitu. Przypadkowy 2 GB plik wyczerpie RAM.
- **Fix**: path.stat().st_size > 200 MB → EEGFileError przed read()
- **Decision**: FIXED — 44cdd02

### F6 — Duplikacja importu EEGFileError w _load_raw()

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/domain/pipeline.py:268, 277
- **Detail**: `EEGFileError as _EEGErr` to bezpowodowy alias — ten sam obiekt.
- **Fix**: Usuń alias, użyj EEGFileError bezpośrednio.
- **Decision**: FIXED — 44cdd02

### F7 — generate_digitrack_fixture.py: brak sprawdzenia ujemnego orig_data_start

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: tests/fixtures/generate_digitrack_fixture.py:56
- **Detail**: Ujemny indeks w Pythonie nie rzuca błędu — data[:orig_data_start] daje błędny fragment.
- **Fix**: `if orig_data_start < 0: sys.exit(1)`
- **Decision**: FIXED — 44cdd02

### O-1 — errors="replace" może wkraść garbage channel names

- **Severity**: OBSERVATION
- **Location**: app/domain/eeg_file.py:101
- **Detail**: Znak U+FFFD (replacement) ma ord > 0x20, więc loop-termination guard nie przerywa.
- **Fix**: Użyj decode("ascii") w try/except UnicodeDecodeError → break
- **Decision**: FIXED — 44cdd02

### O-2 — Podwójny odczyt pliku w validate_eeg_header

- **Severity**: OBSERVATION
- **Location**: app/domain/eeg_file.py:167
- **Detail**: _is_digitrack() czyta 512 B, potem read_raw_digitrack() czyta cały plik.
- **Fix**: Usuń _is_digitrack() pre-check — read_raw_digitrack() sam rzuca EEGFileError.
- **Decision**: FIXED — 44cdd02

### O-3 — _digitrack_annotations() stub niewywoływany

- **Severity**: OBSERVATION
- **Location**: pipeline.py:251–264
- **Detail**: Funkcja nie może być aktywowana bez refaktoru read_raw_digitrack().
- **Fix**: # pragma: no cover na return None
- **Decision**: FIXED — 44cdd02

### O-4 — except (OSError, Exception) — OSError zbędny

- **Severity**: OBSERVATION
- **Location**: pipeline.py:288
- **Detail**: OSError ⊂ Exception — klauzula redundantna.
- **Fix**: except Exception
- **Decision**: FIXED — 44cdd02

### O-5 — Misleading test name

- **Severity**: OBSERVATION
- **Location**: test_eeg_file.py:65
- **Detail**: test_validate_extension_rejects_eeg_without_signature wywołuje validate_eeg_header().
- **Fix**: Rename → test_validate_eeg_header_rejects_eeg_without_digitrack_signature
- **Decision**: FIXED — 44cdd02

### O-6 — Brak testu dla data_start < 0

- **Severity**: OBSERVATION
- **Location**: test_eeg_file.py
- **Detail**: Guard `if data_start < 0` nie był pokryty testami.
- **Fix**: test_read_raw_digitrack_corrupt_total_blocks_raises z total_blocks=0xFFFFFF
- **Decision**: FIXED — 44cdd02

### O-7 — Hardcoded absolutna ścieżka w generate_digitrack_fixture.py

- **Severity**: OBSERVATION
- **Location**: tests/fixtures/generate_digitrack_fixture.py:17
- **Detail**: SOURCE = Path("D:/CVGOSI/NF dane/Testowe/Kuczyński.EEG") — machine-specific.
- **Decision**: SKIPPED — akceptowalne dla jednorazowego skryptu
