<!-- PLAN-REVIEW-REPORT -->
# Plan Review: Motyw z ulotki i ekran Informacje

- **Plan**: `context/changes/flyer-theme-info-screen/plan.md`
- **Mode**: Deep
- **Date**: 2026-07-07
- **Verdict**: REVISE → **SOUND** (po triage — wszystkie findings poprawione w planie)
- **Findings**: 0 critical, 4 warnings, 2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | PASS |
| Lean Execution | WARNING |
| Architectural Fitness | PASS |
| Blind Spots | WARNING |
| Plan Completeness | WARNING |

## Grounding

Grounding: 7/9 paths ✓ (2 planned new files not yet created — expected), 4/4 symbols ✓, brief↔plan ✓

## Findings

### F1 — `COLOR_ACCENT` w Pythonie nie steruje CTk

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Plan Completeness
- **Location**: Phase 1 — `theme.py` vs `neuroflag.json`
- **Detail**: Plan aktualizuje `COLOR_ACCENT` w `theme.py:26`, ale stała nie jest importowana nigdzie poza `theme.py`. Widoczny akcent CTk pochodzi wyłącznie z `neuroflag.json` (`CTkButton`, `CheckBox`, `ProgressBar` itd. — `#2563A8`). Implementer, który zrobi tylko punkt 1 Phase 1, nie osiągnie Desired End State (pomarańczowe przyciski).
- **Fix**: W Phase 1 dodać w Critical Implementation Details lub kontrakcie item 1 zdanie: „`COLOR_ACCENT` dotyczy nowego kodu Python (nagłówki sekcji w `info_dialog`); widoczne widgety CTk wymagają obowiązkowej aktualizacji `neuroflag.json` (item 2) — samo `theme.py` nie zmienia UI.”
- **Decision**: FIXED — dopisano notatkę Phase 1 w Critical Implementation Details

### F2 — Brak aktualizacji type hintów `master` w widokach

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 2 — `AppWindow` / `_view_host`
- **Detail**: Sześć widoków deklaruje `master: ctk.CTk` (`metadata_form.py:44`, `file_import.py`, `analysis.py`, `results_grid.py`, `history.py`, `channel_mapping.py`). Po montowaniu w `_view_host: CTkFrame` mypy `--strict` (wymagane w Success Criteria) może zgłosić błąd typów.
- **Fix**: W kontrakcie Phase 2 item 3 dodać: poszerzyć `master` we wszystkich widokach na `ctk.CTkBaseClass` (lub `CTk | CTkFrame`).
- **Decision**: FIXED — dopisano poszerzenie master na CTkBaseClass w Phase 2

### F3 — Pomarańcz akcentu blisko żółtego RAG

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Blind Spots
- **Location**: Phase 1 — manual verification
- **Detail**: Proponowany akcent `#F9A825` jest wizualnie bliski żółtej komórce RAG `#F5A800` (`rag_colors.py:7`). Kod jest rozdzielony poprawnie, ale plan nie wymaga jawnego porównania na ekranie wyników (przycisk vs komórka). Brief wspomina ryzyko; Phase 1 manual tego nie wymusza explicite.
- **Fix**: Rozszerzyć Progress 1.3 / manual Phase 1: „Na `ResultsGridView` potwierdzić, że pomarańcz przycisków ≠ żółte komórki RAG (obok siebie).”
- **Decision**: FIXED — rozszerzono manual Phase 1 i Progress 1.3

### F4 — README nie korzysta z `info_content.py`

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Lean Execution
- **Location**: Implementation Approach + Phase 3 README
- **Detail**: Plan deklaruje single source of truth w `info_content.py`, ale README to statyczny markdown — nie importuje modułu. Formułka „README może skrócić, ale dane identyczne” zaprasza drift (e-mail/telefon).
- **Fix A ⭐ Recommended**: W Phase 3 dodać test `test_info_content.py` (lub osobny) assertujący, że `README.md` zawiera oba e-maile kontaktów z `EXPERT_CONTACT` / `TECH_CONTACT`.
  - Strength: Wykrywa drift bez ręcznej synchronizacji przy każdej edycji.
  - Tradeoff: Test coupling README ↔ Python.
  - Confidence: HIGH — wzorzec już użyty dla PDF bytes.
  - Blind spot: Skrócone nazwy ról w README mogą nadal się różnić.
- **Fix B**: README tylko linkuje do GitHub Issues + „pełne dane: menu Informacje w aplikacji” — bez duplikacji kontaktów.
  - Strength: Zero drift.
  - Tradeoff: Kontakt niewidoczny bez uruchomienia aplikacji.
  - Confidence: HIGH.
  - Blind spot: Placówki czytające tylko README tracą telefon eksperta.
- **Decision**: FIXED via Fix A — dodano test README ↔ info_content w Phase 3

### F5 — `--smoke-test` nie waliduje UI ani PDF

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Testing Strategy / CI
- **Detail**: `main.py:81-82` kończy przed `AppWindow`. CI (`python-app.yml:109`) nie wykryje regresji chrome, dialogu Informacje ani stopki PDF. Plan to wspomina jako opcjonalne w `distribution.md`.
- **Fix**: W Phase 2/3 Manual Verification lub Testing Strategy dopisać punkt obowiązkowy przed release: ręczny smoke „Informacje na każdym ekranie + PDF stopka” (nie polegać na `--smoke-test`).
- **Decision**: FIXED — dopisano obowiązkowy smoke przed release w Testing Strategy

### F6 — Phase 1 item 3 (`widgets.py`) to weryfikacja no-op

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Lean Execution
- **Location**: Phase 1 — item 3
- **Detail**: `primary_button()` nie ustawia `fg_color` — deleguje do motywu CTk (`widgets.py:94-101`). Item 3 to tylko „upewnij się” bez kodu do napisania.
- **Fix**: Scalić item 3 z Success Criteria Phase 1 manual (verify-only) lub usunąć osobny Changes Required block.
- **Decision**: FIXED — usunięto osobny block widgets.py; verify-only w kontrakcie JSON
