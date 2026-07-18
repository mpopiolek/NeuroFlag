<!-- PLAN-REVIEW-REPORT -->
# Plan Review: Opcjonalne hasło startowe (FR-009)

- **Plan**: context/changes/priority-improvements/plan.md
- **Mode**: Deep
- **Date**: 2026-07-18
- **Verdict**: SOUND (after triage; was REVISE)
- **Findings**: 0 critical  2 warnings  2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | PASS |
| Lean Execution | PASS |
| Architectural Fitness | WARNING → addressed (F1, F4) |
| Blind Spots | WARNING → addressed (F2, F3) |
| Plan Completeness | WARNING → addressed (via F1/F2) |

## Grounding

7/7 existing paths ✓, 2/2 create-targets correctly absent ✓, 6/6 symbols ✓, brief↔plan ✓

## Findings

### F1 — Nieokreślony lifecycle CTk: destroy unlock → AppWindow

- **Severity**: ⚠️ WARNING
- **Impact**: 🔬 HIGH — architectural stakes; think carefully before deciding
- **Dimension**: Architectural Fitness
- **Location**: Implementation Approach / Phase 2 — Unlock gate
- **Detail**: Plan zakładał osobne okno CTk, potem destroy i AppWindow; w kodzie jeden root + Toplevel modale — sekwencja dwóch CTk() ryzykowna.
- **Fix A ⭐ Recommended**: Tymczasowy root unlock + jasna strategia przejścia do AppWindow
- **Fix B**: AppWindow withdraw + unlock Toplevel (otwiera HistoryStore wcześniej)
- **Decision**: FIXED via Fix A

### F2 — Odświeżenie statusu hasła w Informacjach niedookreślone

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Blind Spots
- **Location**: Phase 3 — Password management UI
- **Detail**: open_info() early-return gdy już na InfoView — status może nie odświeżyć się po set/clear.
- **Fix A ⭐ Recommended**: Uchwyt do labela statusu + callback z dialogu
- **Fix B**: show_view(InfoView) po sukcesie (nie open_info)
- **Decision**: FIXED via Fix A

### F3 — settings.json nie jest w .gitignore

- **Severity**: 💬 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 1 / Migration Notes
- **Detail**: Lokalny settings.json w root dev może trafić do gita.
- **Fix**: Dodać settings.json do .gitignore w Phase 1
- **Decision**: FIXED

### F4 — Kolizja nazwy „settings” z tabelą SQLite w HistoryStore

- **Severity**: 💬 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Architectural Fitness
- **Location**: Phase 1 — app/config/settings.py
- **Detail**: HistoryStore ma tabelę settings; łatwo pomylić z settings.json.
- **Fix**: Nota w Phase 1 — nie mylić z tabelą settings w history.db
- **Decision**: FIXED
