<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Testing Critical Path Domain

- **Plan**: context/changes/testing-critical-path-domain/plan.md
- **Scope**: Phase 1 of 2
- **Date**: 2026-06-30
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical  3 warnings  2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | WARNING |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

## Findings

### F1 — norm: object + isinstance guard zamiast poprawnej adnotacji NormEntry

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: tests/unit/test_algorithm_real_norms.py:22–55
- **Detail**: Cztery parametryzowane funkcje używają `norm: object` + `assert isinstance(norm, NormEntry)` wewnątrz ciała + lokalnego `from app.domain.types import NormEntry` w każdej funkcji. Przyczyną jest brak importu `NormEntry` na poziomie modułu. `_REAL_CONFIG.norms` jest typowane jako `tuple[NormEntry, ...]`, więc isinstance nigdy nie może się nie powieść — to martwy kod defensywny. W siostrzanym `test_algorithm.py` wszystkie importy są na poziomie modułu.
- **Fix**: Dodaj `NormEntry` do bloku importów na górze pliku, zmień sygnatury z `norm: object` na `norm: NormEntry`, usuń 4 lokalne importy i 4 isinstance asserty.
- **Decision**: FIXED — NormEntry przeniesiony do importu modułowego, sygnatury zmienione na `norm: NormEntry`, 4 lokalne importy i 4 isinstance asserty usunięte.

### F2 — Moduł-level load() bez obsługi błędu przy kolekcji testów

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: tests/unit/test_algorithm_real_norms.py:9
- **Detail**: `_REAL_CONFIG: NormsConfig = load(resolve_norms_path())` wykonuje się podczas fazy kolekcji pytest. Jeśli `norms.json` jest nieobecny lub uszkodzony, pytest przerywa kolekcję całego modułu z generycznym błędem zamiast właściwego skip/fail na poziomie testu.
- **Fix A ⭐ Recommended**: Pozostaw as-is z komentarzem — norms.json jest commitowany do repo, więc ryzyko jest tylko teoretyczne.
  - Strength: Zero zmian; norms.json zawsze obecny w repo root.
  - Tradeoff: Nie chroni przed brzegowym przypadkiem CI bez pliku.
  - Confidence: HIGH — norms.json jest w repo (nie gitignored).
  - Blind spot: CI workflow nie był sprawdzany pod kątem norms.json w checkout.
- **Fix B**: Owiń w try/except z `pytest.skip` gdy load() rzuci wyjątek.
  - Strength: Semantyka skip jest czytelniejsza niż crash przy kolekcji.
  - Tradeoff: Boilerplate; `pytest.skip` w module scope jest niestandardowe.
  - Confidence: MEDIUM — działa, ale rzadko stosowane w tej bazie kodu.
  - Blind spot: Nie sprawdzano, czy inne pliki testowe używają tego wzorca.
- **Decision**: FIXED via Fix A — dodano komentarz wyjaśniający ryzyko i akceptowalność wzorca.

### F3 — Podwójne ładowanie norms.json w tej samej sesji

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: tests/unit/test_algorithm_real_norms.py:62–69
- **Detail**: `_REAL_CONFIG` (linia 9) i fixture `real_norms_config` (conftest.py:10) oboje wywołują `load(resolve_norms_path())`. Dwa agregujące testy używają fixture, mimo że `_REAL_CONFIG` jest już dostępny na poziomie modułu.
- **Fix**: W obu funkcjach agregujących zastąp parametr `real_norms_config: NormsConfig` bezpośrednim użyciem `_REAL_CONFIG`.
- **Decision**: FIXED — oba testy agregujące używają teraz `_REAL_CONFIG` bezpośrednio; fixture usunięta z sygnatur.

### F4 — Częściowe pokrycie z test_classify_with_real_norms_config

- **Severity**: 💬 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: tests/unit/test_algorithm.py:243
- **Detail**: `test_classify_with_real_norms_config` w `test_algorithm.py` testuje to samo: amplitudy 0.0 < mean_z → WSKAZANIE z realnym norms.json. Konceptualne pokrycie się nakłada; nie jest to duplikat 1:1.
- **Fix**: Opcjonalnie usuń stary test lub zostaw oba z komentarzem wyjaśniającym różnicę.
- **Decision**: FIXED — dodano komentarz w test_algorithm.py wyjaśniający różnicę między smoke testem (0.0) a precyzyjnymi testami granicznymi (mean_z ± 2ε).

### F5 — Ekstrakty _NORM_IDS i typowanie _REAL_CONFIG nie były w planie

- **Severity**: 💬 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: tests/unit/test_algorithm_real_norms.py:9–11
- **Detail**: Plan zakładał `_REAL_CONFIG = load(...)` (bez adnotacji) i ids inlined w dekoratorach. Implementacja wyodrębniła `_NORM_IDS` i dodała typ do `_REAL_CONFIG` — oba są ulepszeniami DRY, semantycznie identyczne.
- **Fix**: Brak działania potrzebny — pozytywna adaptacja.
- **Decision**: SKIPPED — pozytywna adaptacja DRY, brak działania potrzebny.
