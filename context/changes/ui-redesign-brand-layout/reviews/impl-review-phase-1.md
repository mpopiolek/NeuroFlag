<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Redesign UI — Wariant B (nagłówek + dwie kolumny)

- **Plan**: context/changes/ui-redesign-brand-layout/plan.md
- **Scope**: Phase 1 of 5
- **Date**: 2026-07-08
- **Commit**: a43fd54
- **Verdict**: APPROVED
- **Findings**: 0 critical, 2 warnings, 3 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

## Automated Verification

| Command | Result |
|---------|--------|
| `python -m pytest tests/unit/test_theme.py -q` | PASS (2/2) |
| `python -m mypy app/ --strict` | PASS (30 files) |
| Manual 1.4 (granatowe kontrolki, pomarańcz CTA) | PASS — potwierdzone przez użytkownika |

## Findings

### F1 — CTkSwitch pozostaje pomarańczowy bez testu synchronizacji

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/ui/assets/themes/neuroflag.json:52
- **Detail**: `CTkProgressBar` i `CTkSlider` są w `_accent_pairs`, ale `CTkSwitch.progress_color` nadal `#F9A825` i nie jest objęty żadnym testem. Switch nie występuje w kodzie aplikacji dziś — niskie ryzyko regresji, ale luka w kontrakcie accent vs control.
- **Fix**: Jeśli Switch nie będzie używany, zostaw bez zmian i dodaj komentarz w planie/testach; jeśli ma być spójny z kontrolkami formularza, przenieś na granat i dodaj parę do `_control_pairs`.
- **Decision**: FIXED — dodano `CTkSwitch.progress_color` do `_accent_pairs` (spójnie z progress/slider)

### F2 — context_panel ma sztywne wraplength=320

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/ui/components/widgets.py:227
- **Detail**: Istniejący `info_box` przyjmuje konfigurowalne `wraplength`; `context_panel` hardkoduje 320 px. Przy stackowaniu kolumn (<900 px, Faza 3) tekst może się nieoptimalnie łamać.
- **Fix**: Dodać opcjonalny parametr `wraplength: int = 320` do `context_panel` przed Fazą 3.
- **Decision**: FIXED — dodano parametr `wraplength: int = 320`

### F3 — COLOR_CARD to duplikat literału, nie alias Pythona

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: app/ui/theme.py:28-29
- **Detail**: Plan wymaga aliasu względem `COLOR_SURFACE_ELEVATED`; implementacja ustawia oba na `"#FFFFFF"` osobno. Wartości identyczne — brak wpływu wizualnego.
- **Fix**: `COLOR_CARD = COLOR_SURFACE_ELEVATED` zamiast osobnego literału.
- **Decision**: FIXED

### F4 — test_theme.py używa dict[str, Any]

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: tests/unit/test_theme.py:4,16,27
- **Detail**: AGENTS.md wymaga uzasadnienia dla `Any`. Wzorzec dziedziczony z poprzedniej wersji testu; nie blokuje CI.
- **Fix**: Zamienić na `dict[str, object]` i usunąć nieużywany parametr `theme` z helperów.
- **Decision**: FIXED — usunięto `Any` i nieużywany parametr `theme`

### F5 — border_color kontrolek nieobjęty testem synchronizacji

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: tests/unit/test_theme.py
- **Detail**: JSON ustawia `border_color: #CBD5E0` (= `COLOR_CONTROL_BORDER`) na CheckBox/RadioButton, ale `_control_pairs` tego nie weryfikuje.
- **Fix**: Dodać pary border_color do `_control_pairs` lub zaakceptować ryzyko dryfu.
- **Decision**: FIXED — dodano border_color dla CheckBox i RadioButton

## Plan Adherence Summary

| Planned item | Verdict |
|--------------|---------|
| theme.py tokens | MATCH (+ EXTRA: CORNER_RADIUS_CARD, COLOR_CONTROL_HOVER) |
| neuroflag.json control colors | MATCH (+ EXTRA: OptionMenu white text — fix UX zgłoszony przez użytkownika) |
| test_theme.py accent/control split | MATCH (+ EXTRA: hover + text_color assertions) |
| widgets.py primitives (4 factories) | MATCH |
| context_copy.py | MATCH |

Brak pozycji MISSING. Wiring `context_copy` do widoków — świadomie odłożony do Fazy 3.
