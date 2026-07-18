<!-- PLAN-REVIEW-REPORT -->
# Plan Review: Natywny czytnik EEGDigiTrack (Elmiko)

- **Plan**: `context/changes/eegdigitrack-native-reader/plan.md`
- **Mode**: Deep
- **Date**: 2026-06-26
- **Verdict**: REVISE → SOUND (after triage fixes)
- **Findings**: 2 critical, 1 warning, 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | FAIL |
| Lean Execution | PASS |
| Architectural Fitness | PASS |
| Blind Spots | FAIL |
| Plan Completeness | WARNING |

## Grounding

7/7 paths ✓ (2 new files expected), 5/5 symbols ✓, brief↔plan ✓

## Findings

### F1 — ECG header channel inflates n_ch → data_start < 0 → file never loads

- **Severity**: ❌ CRITICAL
- **Impact**: 🔬 HIGH — architectural stakes; think carefully before deciding
- **Dimension**: End-State Alignment + Blind Spots
- **Location**: Phase 1 — Critical Implementation Details, n_ch logic
- **Detail**: research.md (line 114–116) shows channel index 19 ("ECG", cal=2.5 µV/LSB) is in the binary header but NOT in the data stream. The n_ch stop condition (`name.strip() in ("", "Default")`) does NOT stop at "ECG" → n_ch=20. For Kuczyński.EEG: data_start = 13,095,336 − 343,500×20×2 = −644,664. The guard "raise EEGFileError when data_start < 0" fires on every valid file. Plan contradicts its own research.md which hardcodes 19 data channels.
- **Fix A ⭐ Recommended**: After scanning, compute n_ch_data = channels with cal ≤ 1.0 µV/LSB. Use n_ch_data for data_start + reshape.
  - Strength: Principled; derived from format's own calibration values.
  - Tradeoff: Assumes EEG channels always cal < 1.0 µV/LSB.
  - Confidence: HIGH — 0.179266 EEG vs 2.5 ECG unambiguous in research.
  - Blind spot: Unknown if future gain-switched models exceed 1.0 µV/LSB.
- **Fix B**: Drop channels named "ECG" (case-insensitive) from data-channel list.
  - Strength: Explicit, easy to audit.
  - Tradeoff: Hardcodes name sentinel.
  - Confidence: MED — confirmed in 2 test files only.
  - Blind spot: EEG-1040 header unknown.
- **Decision**: FIXED via Fix A

### F2 — Progress phase titles don't match body phase titles

- **Severity**: ❌ CRITICAL
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Progress section (lines 378, 390, 413 vs body lines 70, 162, 278)
- **Detail**: 3 of 4 Progress `### Phase N:` headers differ from body `## Phase N:` titles (missing backticks, path prefixes, truncated name). `/10x-implement` parses by exact match — mismatches break the mechanical contract.
- **Fix**: Rename three Progress headers to match body titles exactly.
- **Decision**: FIXED

### F3 — EEGFileError from read_raw_digitrack() swallowed by generic handler

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 2 — Gałąź .eeg w _load_raw()
- **Detail**: EEGFileError subclasses Exception. Placing the .eeg branch inside `except (OSError, Exception)` would swallow specific diagnostic messages ("kalibracja kanału X = 0", "sygnatura nieobecna") and replace with generic "Nie można odczytać pliku EEG".
- **Fix**: Wrap read_raw_digitrack() in its own `except EEGFileError` before the generic handler, passing `str(exc)` to PipelineError.
- **Decision**: FIXED

### F4 — _digitrack_annotations() stub has no reachable future call path

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 2 — Stub dekodera markerów DigiTrack
- **Detail**: Stub signature is `(data: bytes, sfreq: float)` but pipeline.run() only has the RawArray after loading — raw bytes are discarded. Future activation requires refactoring read_raw_digitrack() to return (RawArray, bytes).
- **Fix**: Add docstring note about required refactor for future implementor.
- **Decision**: FIXED
