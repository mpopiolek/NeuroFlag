<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Project Foundation

- **Plan**: context/changes/project-foundation/plan.md
- **Scope**: Phase 2 of 4
- **Date**: 2026-05-31
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical  2 warnings  2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS ✅ |
| Scope Discipline | PASS ✅ |
| Safety & Quality | WARNING ⚠️ |
| Architecture | PASS ✅ |
| Pattern Consistency | PASS ✅ |
| Success Criteria | PASS ✅ |

## Findings

### F1 — Konwersje numeryczne mogą wyciekać ValueError/TypeError

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/domain/norms.py:38, 54–59, 93–95
- **Detail**: int() i float() nie są owinięte try/except. Dla malformed JSON (np. "version": "abc", "l_freq": null) wycieknie surowy ValueError zamiast NormsLoadError. Wywołujący musi łapać dwa typy zamiast jednego.
- **Fix**: Opakować konwersje w try/except (ValueError, TypeError) i re-raise jako NormsLoadError.
- **Decision**: FIXED — wrapped int()/float() calls with _as_int()/_as_float() helpers that re-raise ValueError/TypeError as NormsLoadError.

### F2 — VALID_BANDS rozłączne z band_ranges — możliwy KeyError downstream

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: app/domain/norms.py:11, 48–52, 89–90
- **Detail**: VALID_BANDS jest hardcoded. NormEntry z band "Theta" przechodzi walidację, ale jeśli band_ranges nie zawiera "Theta" (np. pusty obiekt), pipeline dostanie KeyError przy lookup. Dwa niezależne źródła prawdy.
- **Fix A ⭐ Recommended**: Zastąp VALID_BANDS cross-check z band_ranges — po parsowaniu obu, zwaliduj że każdy entry.band istnieje w band_ranges.
  - Strength: band_ranges staje się single source of truth; pipeline nigdy nie dostanie KeyError.
  - Tradeoff: VALID_BANDS traci rolę fast-fail przed band_ranges parse.
  - Confidence: HIGH
  - Blind spot: None significant.
- **Fix B**: Zostaw VALID_BANDS, dodaj cross-check jako drugi krok.
  - Strength: Zachowuje czytelną stałą dla developerów.
  - Tradeoff: Dwa sources of truth — ryzyko desynchronizacji.
  - Confidence: MEDIUM
  - Blind spot: None significant.
- **Decision**: FIXED via Fix A — usunięto VALID_BANDS check z _parse_norm_entry; dodano cross-check w load() po parsowaniu band_ranges i norm_entries.

### F3 — Brak testu dla ścieżki OSError (plik nieistniejący)

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality / Test Coverage
- **Location**: tests/unit/test_norms.py (brak)
- **Detail**: load() ma obsługę OSError (norms.py:65–68), ale brak testu. Wszystkie inne 7 ścieżek błędów mają pokrycie.
- **Fix**: Dodać test_file_not_found z pytest.raises(NormsLoadError, match="Cannot read").
- **Decision**: FIXED — dodano test_file_not_found do tests/unit/test_norms.py.

### F4 — NormsConfig jest mutowalny (@dataclass bez frozen=True)

- **Severity**: 💡 OBSERVATION
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Architecture / Pattern Consistency
- **Location**: app/domain/types.py:74 (pre-existing)
- **Detail**: Wszystkie inne dataclassy mają frozen=True. NormsConfig jest mutowalny — pre-existing w types.py, nie wprowadzone przez Phase 2.
- **Fix**: Dodać frozen=True do NormsConfig; band_ranges (dict) wymagałby MappingProxyType lub akceptacji mutowalności wewnętrznej.
- **Decision**: SKIPPED — NormsConfig traktowany jako konfiguracja, nie value object; mutowalność akceptowalna.
