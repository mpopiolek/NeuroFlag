<!-- PLAN-REVIEW-REPORT -->
# Plan Review: Project Foundation Implementation Plan

- **Plan**: `context/changes/project-foundation/plan.md`
- **Mode**: Deep
- **Date**: 2026-05-30
- **Verdict**: SOUND (po naprawach)
- **Findings**: 1 critical · 1 warning · 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | PASS |
| Lean Execution | PASS |
| Architectural Fitness | WARNING → FIXED |
| Blind Spots | WARNING → FIXED |
| Plan Completeness | FAIL → FIXED |

## Grounding

6/6 paths ✓ (`app/main.py`, `tests/test_app_endpoints.py`, `tests/test_imports.py`, `norms.json`, `neuroflag.spec`, `pyproject.toml`), 3/3 symbols ✓ (`neuroflag.spec:110` entry point, CI `--smoke-test` line 88, `pyproject.toml` `strict = true`), brief↔plan ✓

## Findings

### F1 — Progress section nie ma 1:1 z Success Criteria bullets

- **Severity**: ❌ CRITICAL
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: ## Progress — Phase 1 Manual + Phase 4 Manual
- **Detail**: Phase 1 miała 2 Manual bullets ale 1 Progress item (zmergowane). Phase 4 miała 2 Manual bullets ale 1 Progress item (brakujący review step dla test_norms.py).
- **Fix**: Dodano 2 brakujące Progress items: `1.4` (instancjacja PatientMetadata) i `4.6` (przejrzyj test_norms.py).
- **Decision**: FIXED

### F2 — NormsConfig(frozen=True) z dict[str, BandRange] jest unhashable

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Architectural Fitness
- **Location**: Phase 1 — app/domain/types.py, NormsConfig contract
- **Detail**: `@dataclass(frozen=True)` generuje `__hash__` bazujący na wszystkich polach. `dict[str, BandRange]` nie jest hashowalny — `hash(config)` podnosi `TypeError` w runtime. `mypy --strict` tego nie wykrywa. `NormsConfig` to config object, nie value type — `frozen=True` semantycznie nieprawidłowe.
- **Fix A ⭐ Applied**: Usunięto `frozen=True` z `NormsConfig`. Pozostałe value types (`PatientMetadata`, `CellResult`, `AnalysisResult`, `BandRange`, `NormEntry`) zachowują `frozen=True`.
- **Decision**: FIXED via Fix A

### F3 — import customtkinter w test_deps.py: zachowanie na headless Ubuntu CI niezweryfikowane

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 4 — tests/unit/test_deps.py
- **Detail**: CI test job działa na ubuntu-latest (headless). Obecny `test_imports.py` NIE importuje customtkinter — plan wprowadzał nowe ryzyko. `import customtkinter` na headless Linux zależy od dostępności `python3-tk` na runner'ze. Jeśli import zawiedzie, `pytest -q` blokuje CI.
- **Fix Applied**: Kontrakt `test_deps.py` zaktualizowany — `test_customtkinter_importable()` opatrzony `@pytest.mark.skipif(sys.platform != "win32", ...)`. PyInstaller smoke-test na `windows-latest` weryfikuje importowalność w naturalny sposób.
- **Decision**: FIXED
