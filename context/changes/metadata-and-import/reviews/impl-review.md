<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: S-01 — Formularz metryki + import EEG

- **Plan**: context/changes/metadata-and-import/plan.md
- **Scope**: Phases 1–3 of 4 (Phase 4 pending)
- **Date**: 2026-06-02
- **Commits**: a255733, 4ebce96, 6c97834, 06d9647
- **Verdict**: APPROVED (with Phase 4 outstanding)
- **Findings**: 0 critical, 1 warning, 3 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | WARNING |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

## Findings

### F1 — Phase 4 niezaimplementowana (planowane)

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: tests/unit/test_eeg_file.py (brak), tests/unit/test_types.py
- **Detail**: Progress Phase 4 ma wszystkie `[ ]`. Brakuje `test_eeg_file.py` oraz dwóch testów `is_excluded()` dla `BRAIN_INJURY` i `INTELLECTUAL_DISABILITY` solo (plan 4.2). Fazy 1–3 są kompletne; to oczekiwany następny krok, nie regresja.
- **Fix**: Uruchomić `/10x-implement metadata-and-import phase 4` z mockami MNE (`patch` na `mne.io.read_raw_edf` / `read_raw_brainvision` w module `app.domain.eeg_file` po `_load_mne()`).
- **Decision**: SKIPPED — Phase 4

### F2 — Szeroki commit 4ebce96 (norms-replacement)

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: commit 4ebce96
- **Detail**: W historii S-01 jest commit z `context/changes/norms-replacement/*` i `roadmap.md` poza zakresem S-01. Świadoma decyzja użytkownika przy „stage all”; nie blokuje jakości kodu UI.
- **Fix**: Kolejne commity trzymać w touched-set per faza.
- **Decision**: ACCEPTED

### F3 — `plan.md` z SHA poza ostatnim commitem kodu

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: context/changes/metadata-and-import/plan.md
- **Detail**: Wiersze Progress 3.x mają suffix `06d9647` w working tree; `git status` pokazuje zmodyfikowany `plan.md` niezcommitowany po `06d9647`. Spójność tracking: chore commit lub epilogue.
- **Fix**: Zacommitować `plan.md` przy starcie Phase 4 lub w epilogue.
- **Decision**: FIXED — commit plan.md

### F4 — Mock MNE w testach Phase 4

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/domain/eeg_file.py:29–48
- **Detail**: `validate_eeg_header` ładuje MNE przez `_load_mne()` wewnątrz funkcji. Plan Phase 4 wskazuje `patch("mne.io.read_raw_edf")` — działa, o ile patch trafia przed wywołaniem w teście; alternatywnie `patch.object` na module po imporcie. Nie wymaga zmiany produkcyjnego kodu.
- **Fix**: W `test_eeg_file.py` użyć `@patch("mne.io.read_raw_edf")` / `@patch("mne.io.read_raw_brainvision")` — import w `_load_mne` widzi zamockowany moduł.
- **Decision**: SKIPPED — notatka na Phase 4

## Plan drift matrix (Phases 1–3)

| Plik | Plan | Implementacja | Werdykt |
|------|------|---------------|---------|
| `app/ui/app_window.py` | AppState, show_view destroy+create | Zgodne | MATCH |
| `app/main.py` | AppWindow + MetadataFormView | Zgodne | MATCH |
| `pyproject.toml` | mypy overrides CTk | + `build_meta` fix | MATCH (addendum) |
| `metadata_form.py` | Formularz, lazy import, wykluczenia | + `_restore_from_state` | MATCH |
| `file_import.py` | Dialog, thread, progress, Analizuj stub | Zgodne | MATCH |
| `eeg_file.py` | Walidacja ext/companions/header | + lazy MNE | MATCH |

## Success criteria verification

### Automated (Phases 1–3)

| Check | Result |
|-------|--------|
| `python -m app.main --smoke-test` | PASS |
| `mypy app/ --strict` | PASS (11 files) |
| `pytest -q` | PASS (17 tests) |

### Manual (Progress 1.4–3.8)

All `[x]` with SHAs — potwierdzone w sesji (w tym fix 3.8 `_restore_from_state`, 3.5 dowolne nieobsługiwane rozszerzenie np. `.css`).

### Phase 4

Pending — brak `test_eeg_file.py`.

## Cross-phase notes

- Lazy import `mne` + `eeg_file` w wątku: poprawia UX gdy MNE nie zainstalowane; po `pip install -e .` walidacja działa (potwierdzone EEGBCI + BrainVision manual).
- `FileImportView.__init__` resetuje `eeg_path` — zgodne z planem, zapobiega fałszywemu `ready_for_analysis()`.
