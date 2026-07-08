<!-- PLAN-REVIEW-REPORT -->
# Plan Review: Redesign UI — Wariant B

- **Plan**: `context/changes/ui-redesign-brand-layout/plan.md`
- **Mode**: Deep
- **Date**: 2026-07-08
- **Verdict**: SOUND (po triage)
- **Findings**: 2 critical, 5 warnings, 2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | WARNING ⚠️ |
| Lean Execution | WARNING ⚠️ |
| Architectural Fitness | PASS ✅ |
| Blind Spots | WARNING ⚠️ |
| Plan Completeness | WARNING ⚠️ |

## Grounding

Grounding: 12/12 paths ✓, 6/6 symbols ✓, brief↔plan ✓

## Findings

### F1 — minsize(900) vs test „Okno 820 px”

- **Severity**: ❌ CRITICAL
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 2 (Contract `minsize`) + Phase 3 Manual + Testing Strategy
- **Detail**: Plan Phase 2 ustawia `minsize(900, 640)`, ale Phase 3 wymaga manualnego testu przy „Okno 820 px” (także Testing Strategy pkt 6). Przy `minsize=900` użytkownik nie może zmniejszyć okna do 820 px. Obecny kod ma `minsize(820, 600)` (`app_window.py:46`). Breakpoint stacku to 900 px — test przy minimum powinien być 900 px, nie 820.
- **Fix**: Zmień manual verification 3.4 i Testing Strategy na „Okno 900 px (minimum): kolumny stackują się pionowo”.
- **Decision**: FIXED — test przy 900 px (minimum), spójne z minsize(900)

### F2 — set_footer bez czyszczenia w show_view

- **Severity**: ❌ CRITICAL
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Blind Spots
- **Location**: Critical Implementation Details + Phase 2 AppWindow
- **Detail**: Plan zakłada czyszczenie stopki w `destroy()` widoku, ale żaden widok nie nadpisuje `destroy()` (`grep` → 0 w `app/`). `show_view` niszczy widok bez resetu chrome (`app_window.py:78-88`). Po nawigacji A→B stopka może zostawić etykiety/komendy z widoku A.
- **Fix A ⭐ Recommended**: W `show_view` wołaj `_clear_footer()` przed `destroy()`; widoki ustawiają stopkę w `__init__`. Nie polegaj na per-view `destroy()`.
  - Strength: Jedno miejsce, zgodne z destroy-recreate pattern już w `show_view`.
  - Tradeoff: `show_view` musi znać domyślny stan stopki (ukryte przyciski).
  - Confidence: HIGH — standardowy wzorzec shell-owned chrome.
  - Blind spot: Overlay (Phase 5) musi też resetować stopkę przy starcie/końcu.
- **Fix B**: Bazowa klasa `ShellView(CTkFrame)` z `destroy()` wołającym `_clear_footer()`.
  - Strength: Enkapsulacja w widokach.
  - Tradeoff: Wszystkie 6+ widoków muszą dziedziczyć; łatwo pominąć nowy widok.
  - Confidence: MEDIUM — więcej refaktoru niż Fix A.
  - Blind spot: Modale (`_EditStudyDialog`) poza hierarchią.
- **Decision**: FIXED via Fix A — `_clear_footer()` w `show_view` przed `destroy()`

### F3 — COLOR_CARD brak w Phase 1

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 1 — `surface_card` contract vs token list
- **Detail**: `surface_card` używa `COLOR_CARD`, ale Phase 1 lista stałych go nie zawiera. W `theme.py` jest `COLOR_SURFACE_ELEVATED = "#FFFFFF"` — brak aliasu `COLOR_CARD`.
- **Fix**: Dodać do Phase 1 contract: `COLOR_CARD = "#FFFFFF"` (alias do `COLOR_SURFACE_ELEVATED` lub jedna stała).
- **Decision**: FIXED

### F4 — Przycisk Historia w nagłówku bez specyfikacji

- **Severity**: ⚠️ WARNING
- **Impact**: 🔬 HIGH — architectural stakes; think carefully before deciding
- **Dimension**: End-State Alignment
- **Location**: Phase 2 AppWindow + Phase 4 HistoryView
- **Detail**: Plan dodaje „Historia” w headerze (disabled gdy pusto), ale nie definiuje handlera. Dziś Historia otwiera się tylko z `ResultsGridView._on_history` (`results_grid.py:198-201`). Powrót z historii woła `show_view(ResultsGridView)` (`history.py:275-278`), który bez `analysis_result` pokazuje stub błędu (`results_grid.py:45-60`). Otwarcie Historii z kroku 1–3 lub po „Nowe badanie” → „Wróć” może złamać flow.
- **Fix A ⭐ Recommended**: `AppWindow._on_history()` → `show_view(HistoryView)`; `HistoryView.set_footer` z back zależnym od kontekstu: jeśli `analysis_result` → ResultsGridView, inaczej MetadataFormView.
  - Strength: Obsługuje globalny skrót i bezpieczny powrót.
  - Tradeoff: HistoryView potrzebuje parametru/kontekstu wejścia.
  - Confidence: HIGH — jedyny sposób na globalny przycisk bez regresji.
  - Blind spot: Czy Historia dostępna mid-wizard — decyzja produktowa (plan powinien ją zapisać).
- **Fix B**: Historia w headerze tylko na krokach 4+ (enabled gdy `analysis_result` lub na Results/History).
  - Strength: Prostsze back — zawsze Results.
  - Tradeoff: Mniej użyteczny skrót podczas formularza.
  - Confidence: MEDIUM — ogranicza obietnicę „Historia w nagłówku”.
  - Blind spot: Użytkownik z wcześniejszymi badaniami na kroku 1 nie zobaczy historii.
- **Decision**: FIXED via Fix A — `_on_history()` + `return_target` w HistoryView

### F5 — Duplikacja CTA na ekranie wyników

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Plan Completeness
- **Location**: Phase 4 ResultsGridView
- **Detail**: Contract mówi: przyciski PDF/Nowe badanie/Historia „w karcie **lub** stopce shell (PDF jako primary w stopce)” — implementer może zostawić oba zestawy i naruszyć zasadę „jeden pomarańczowy primary”.
- **Fix**: Jednoznacznie: **wszystkie** akcje w stopce shell (primary=PDF, secondary back=Nowe badanie); w karcie lewej **zero** przycisków. „Historia badań” tylko w nagłówku (F4).
- **Decision**: FIXED — akcje wyłącznie w stopce shell

### F6 — Stepper krok 3 przy overlay analizy

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: End-State Alignment
- **Location**: Phase 5 + Critical Implementation Details
- **Detail**: Stepper aktualizowany przez `VIEW_STEP` przy `show_view`. Overlay nie zmienia widoku → krok 3 (Analiza) nie zapali się bez jawnego `set_active_step(3)` przy starcie overlay. Phase 2 manual wymaga „Metadata→Import→Analysis→Results aktualizuje stepper” — po Phase 5 AnalysisView znika z nawigacji.
- **Fix**: W Phase 5 contract: `start_analysis_overlay()` woła `_stepper.set_active_step(3)` na starcie i `set_active_step(4)` po sukcesie; zaktualizuj Phase 2 manual verification na overlay-aware flow po Phase 5.
- **Decision**: FIXED — explicit set_active_step w overlay

### F7 — CONTEXT_METADATA musi zawierać pełny tekst RODO

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 1 context_copy + Phase 3 MetadataFormView
- **Detail**: `metadata_form.py:183-191` ma rozszerzony tekst (historia badań, PDF, diagnozy opcjonalne). Plan Phase 1 wspomina skrót „RODO/offline” — ryzyko utraty zdań przy przeniesieniu do `context_copy.py`.
- **Fix**: W Phase 1 contract: `CONTEXT_METADATA` = dokładna kopia obecnego `info_box` z `metadata_form.py` (verbatim), nie skrót.
- **Decision**: FIXED — verbatim copy w contract

### F8 — Chip historii już istnieje jako CTkLabel

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Lean Execution
- **Location**: Phase 4 HistoryView + Current State Analysis
- **Detail**: Plan twierdzi „kategoria jako czerwony przycisk” (`plan.md:15`), ale kod używa `CTkLabel` z `fg_color=cat_bg` (`history.py:204-212`). Phase 4 to głównie ekstrakcja `category_chip()` i dopasowanie stylu (corner_radius, brak button chrome) — mniejszy zakres niż sugeruje Current State.
- **Fix**: Zaktualizuj Current State; Phase 4 ogranicz do `category_chip()` + ewentualnie mniejszy corner_radius / bez szerokości 84 px jak button.
- **Decision**: FIXED — Current State skorygowany

### F9 — smoke-test nie ładuje AnalysisView

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Lean Execution
- **Location**: Phase 5 AnalysisView fallback
- **Detail**: `main.py:81-82` — `--smoke-test` kończy przed `show_view`. Klauzula „AnalysisView jako fallback dla smoke-test” w Phase 5 jest martwa.
- **Fix**: Usuń smoke-test fallback z Phase 5; smoke-test weryfikuje tylko start + motyw (Testing Strategy pkt 7).
- **Decision**: FIXED — usunięto smoke-test fallback
