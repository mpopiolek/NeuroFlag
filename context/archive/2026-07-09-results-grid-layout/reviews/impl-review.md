<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Siatka wyników A′ — PDF i domknięcie change

- **Plan**: context/changes/results-grid-layout/plan.md
- **Scope**: Phases 1–4 of 4 (full plan)
- **Date**: 2026-07-09
- **Commits**: 3729d27, 2ee1768, e53b34b, b11e67e, 019f6fc, e8e9d38
- **Verdict**: APPROVED (post-triage)
- **Findings**: 0 critical, 5 warnings, 3 observations — 6 fixed, 2 accepted

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | WARNING |
| Scope Discipline | PASS |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | WARNING |

## Automated Verification

| Command | Result |
|---------|--------|
| `python -m pytest -q` | PASS |
| `python -m mypy app/ --strict` | PASS (47 files) |
| `python -m pytest tests/unit/test_cell_layout.py tests/unit/test_pdf_generator.py -q` | PASS |

## Findings

### F1 — PDF bez pionowej linii między C3 a O1

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — świadoma zmiana UX; print vs ekran
- **Dimension**: Plan Adherence
- **Location**: app/reports/pdf_generator.py (`_build_task_section_table`)
- **Detail**: Plan fazy 3 i research przewidywały linię pionową między klastrami (jak UI). Użytkownik podczas manualnej weryfikacji poprosił o usunięcie kresek — PDF ma tylko `_PDF_CHANNEL_GAP`; UI zachowuje linię w `_build_channel_cluster`.
- **Fix A ⭐ Recommended**: Zaakceptować i utrzymać research.md (UI z linią, PDF bez)
  - Strength: Odzwierciedla potwierdzony feedback; testy przechodzą.
  - Tradeoff: Niewielka niespójność print vs ekran.
  - Confidence: HIGH — decyzja użytkownika 2026-07-09.
  - Blind spot: Brak.
- **Fix B**: Przywrócić linię w PDF jak w UI
  - Strength: Pełna zgodność z planem i research.
  - Tradeoff: Regresja zaakceptowanego UX PDF.
  - Confidence: LOW — użytkownik jawnie odrzucił kreski.
  - Blind spot: Brak.
- **Decision**: ACCEPTED — Fix A; research.md dokumentuje UI≠PDF

### F2 — Progress 1.3 (smoke UI retro) nadal `[ ]`

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — proceduralny; kod UI zgodny z kontraktem
- **Dimension**: Success Criteria
- **Location**: context/changes/results-grid-layout/plan.md — Progress 1.3
- **Detail**: Faza 1 ukończona przed planem (`3729d27`); checkbox manualny 1.3 nie został zamknięty mimo retro-weryfikacji w review.
- **Fix**: Zamknąć 1.3 jako `[x]` przy `/10x-archive` lub zostawić jako informacyjny brak SHA.
- **Decision**: FIXED — 1.3 zamknięty retro SHA 3729d27

### F3 — Brak jawnej asercji anty-regresji 2×5 w PDF

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — luka pokrycia testów, nie błąd funkcjonalny
- **Dimension**: Success Criteria
- **Location**: tests/unit/test_pdf_generator.py
- **Detail**: Plan fazy 4 wymaga wykrycia powrotu do płaskiej 2×5. Obecne testy sprawdzają etykiety zadań i pasma w story (monkeypatch `Paragraph`), ale nie strukturę zagnieżdżonych `Table` ani brak `idx // 5`.
- **Fix**: Dodać test importujący `_build_rag_grid_story` i asertujący liczbę sekcji / typy flowables (3 task headings + tabele klastrów).
- **Decision**: FIXED — `test_build_rag_grid_story_uses_task_sections_not_flat_grid`

### F4 — Duplikacja stałych kanałów C3/O1

- **Severity**: ⚠️ WARNING
- **Impact**: 🔬 HIGH — ryzyko rozjazdu przy zmianie kanałów domenowych
- **Dimension**: Pattern Consistency
- **Location**: app/domain/cell_layout.py:8, app/domain/channels.py, app/domain/pipeline.py
- **Detail**: `CHANNEL_DISPLAY_ORDER` w `cell_layout` jest niezależne od `_REQUIRED_CANONICAL` / `_REQUIRED_CHANNELS` w pipeline i channels. Zadania i pasma są scentralizowane; kanały — nie.
- **Fix A ⭐ Recommended**: Wydzielić `CANONICAL_CHANNELS: tuple[str, ...]` w module domenowym i importować w `cell_layout`, `channels`, `pipeline`
  - Strength: Jedno źródło prawdy dla całego stacku EEG.
  - Tradeoff: Szerszy diff poza change; dotyka modułów spoza planu.
  - Confidence: MEDIUM — poprawna architektura, ale scope creep.
  - Blind spot: Kalibracja i harness mają własne kopie.
- **Fix B**: Zostawić jak jest — dokumentować w research
  - Strength: Zero dodatkowego diffu.
  - Tradeoff: Przy dodaniu kanału trzeba pamiętać o 4 miejscach.
  - Confidence: HIGH — obecny stan działa dla 2 kanałów 10-20.
  - Blind spot: Brak.
- **Decision**: ACCEPTED — Fix B; poza zakresem change, działa dla 2 kanałów

### F5 — PDF reimplementuje `RAG_COLOR_FG` zamiast importu

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — szybka poprawka przy zmianie palety
- **Dimension**: Pattern Consistency
- **Location**: app/reports/pdf_generator.py:111–114
- **Detail**: `_cell_text_color()` duplikuje logikę `RAG_COLOR_FG` (RED/GREEN → white, YELLOW → #1A1A1A). UI importuje oba słowniki z `rag_colors.py`.
- **Fix**: Import `RAG_COLOR_FG` i mapuj hex → `colors.HexColor` w helperze PDF.
- **Decision**: FIXED — `_cell_text_color` używa `RAG_COLOR_FG`

### F6 — `range(3)` hardkodowane w UI klastrów

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — kruchość przy rozszerzeniu `CHANNEL_DISPLAY_ORDER`
- **Dimension**: Reliability
- **Location**: app/ui/views/results_grid.py:179–180
- **Detail**: `for col in range(3)` zakłada dokładnie 2 kanały + 1 kolumna dividera. Zmiana `CHANNEL_DISPLAY_ORDER` nie zaktualizuje siatki automatycznie.
- **Fix**: Wyprowadzić liczbę kolumn z `len(CHANNEL_DISPLAY_ORDER) * 2 - 1` lub budować kolumny w pętli po kanałach.
- **Decision**: FIXED — `cluster_col_count` i `grid_col = channel_idx * 2`

### F7 — `cell_layout.py` bez docstringów modułu

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🏃 LOW — dokumentacja kontraktu
- **Dimension**: Pattern Consistency
- **Location**: app/domain/cell_layout.py
- **Detail**: Sąsiednie moduły (`channels.py`, `algorithm.py`) mają docstringi opisujące kontrakt. `cell_layout` nie rozróżnia jawnie „display order vs pipeline order”.
- **Fix**: Krótki module docstring + jedna linia na `cells_for_task_channel`.
- **Decision**: FIXED — docstringi dodane

### F8 — Warstwa reports zależy od `app.ui.components`

- **Severity**: ℹ️ OBSERVATION
- **Impact**: 🔬 HIGH — długoterminowa separacja warstw (pre-existing)
- **Dimension**: Architecture
- **Location**: app/reports/pdf_generator.py:37–38
- **Detail**: PDF importuje `TASK_LABELS` i `RAG_COLOR_BG` z UI components. `cell_layout` poprawił decoupling domeny, ale tokeny prezentacji pozostają w UI.
- **Fix**: Przenieść palety/etykiety do neutralnego modułu (`app/presentation/` lub domain-adjacent) — poza zakresem tego change.
- **Decision**: FIXED — `app/presentation/rag_colors.py`; PDF importuje stamtąd; UI re-eksportuje

## Conclusion

Implementacja domyka change `results-grid-layout`: UI A′ (retro), wspólna logika `cell_layout`, PDF A′ z testami regresji layoutu tekstowego. **Brak CRITICAL findings.** Główne punkty uwagi: zaakceptowany drift PDF (brak linii), luka testów strukturalnych PDF, duplikacja stałych kanałów i `RAG_COLOR_FG`. Bezpieczne do archiwizacji po triage lub świadomym pominięciu ostrzeżeń.
