<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Project Foundation (F-01)

- **Plan**: context/changes/project-foundation/plan.md
- **Scope**: Fazy 1–4 (pełny plan)
- **Date**: 2026-05-31
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical  3 warnings  3 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS ✅ |
| Scope Discipline | PASS ✅ |
| Safety & Quality | WARNING ⚠️ |
| Architecture | PASS ✅ |
| Pattern Consistency | WARNING ⚠️ |
| Success Criteria | PASS ✅ |

## Findings

### F1 — _as_int() cicho obcina floaty (3.9 → 3)

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/domain/norms.py:31
- **Detail**: _as_int robi int(float(value)). Wartość "3.9" lub 3.9 w JSON przechodzi bez błędu i zostaje obcięta do 3. Dotyczy version, recommendation_threshold i norm_id.
- **Fix**: Dodaj guard `if f != int(f): raise NormsLoadError(...)`.
- **Decision**: FIXED — _as_int dodaje guard `if f != int(f): raise NormsLoadError(...)`.

### F2 — VALID_BANDS martwy kod po triage Phase 2

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/domain/norms.py:11
- **Detail**: VALID_BANDS zadeklarowany ale nie używany w żadnej walidacji po fix F2 (triage Phase 2). Dezorientuje przyszłych deweloperów.
- **Fix**: Usunąć linię VALID_BANDS.
- **Decision**: FIXED — linia VALID_BANDS usunięta z norms.py.

### F3 — NormsConfig mutowalny — jedyny dataclass bez frozen=True

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality / Architecture
- **Location**: app/domain/types.py:74
- **Detail**: Każdy inny dataclass w types.py jest frozen=True. NormsConfig jest wyjątkiem. Poprzedni triage (Phase 2, F4) → SKIPPED.
- **Fix A ⭐ Recommended**: Dodaj frozen=True; band_ranges dict pozostaje mutowalny wewnętrznie.
  - Strength: Spójność z resztą types.py; load() kontrakt jasny.
  - Tradeoff: band_ranges wewnętrzny dict nadal mutowalny.
  - Confidence: HIGH
- **Fix B**: Zostaw bez frozen, dodaj komentarz "# mutable by design".
  - Strength: Brak ryzyka regresu.
  - Tradeoff: Wzorzec niekonsekwentny.
  - Confidence: LOW
- **Decision**: FIXED via Fix A — dodano frozen=True do NormsConfig.

### F4 — app/domain/__init__.py brak from __future__ import annotations

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/domain/__init__.py:1
- **Detail**: Wszystkie inne pliki mają from __future__ import annotations. __init__.py nie.
- **Fix**: Dodać jako pierwszą linię.
- **Decision**: FIXED — dodano from __future__ import annotations.

### F5 — AnalysisResult bez guard cells == 10

- **Severity**: 💡 OBSERVATION
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: app/domain/types.py:51
- **Detail**: Plan mówi "dokładnie 10 elementów" dla cells. Typ nie wymusza długości. Algorithm/UI zakłada 10 — bez guardu błąd pojawi się daleko od źródła.
- **Fix**: Dodać __post_init__ z assert len(self.cells) == 10.
- **Decision**: FIXED — dodano __post_init__ z ValueError gdy len(cells) != 10.

### F6 — Wspólne fikstury w test_norms.py są mutowalne

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Test Safety
- **Location**: tests/unit/test_norms.py:10-45
- **Detail**: _VALID_NORMS i _VALID_PAYLOAD to module-level mutowalne struktury. Testy mutują je przez dict()/slice — poprawnie dziś, ryzyko przy rozbudowie.
- **Fix**: Zamienić na funkcje pomocnicze lub użyć copy.deepcopy.
- **Decision**: FIXED — _VALID_NORMS/_VALID_PAYLOAD zamienione na _valid_norms()/_valid_payload() zwracające świeże kopie.
