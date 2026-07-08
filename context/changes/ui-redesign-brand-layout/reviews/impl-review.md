<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Redesign UI — Wariant B

- **Plan**: context/changes/ui-redesign-brand-layout/plan.md
- **Scope**: Phases 1–3 of 5 (completed phases)
- **Date**: 2026-07-08
- **Commits**: a43fd54, 71e420d, 803c1d7, c0047d1
- **Verdict**: APPROVED
- **Findings**: 0 critical, 3 warnings, 4 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | WARNING |
| Scope Discipline | PASS |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

## Automated Verification

| Command | Result |
|---------|--------|
| `python -m pytest tests/unit/test_navigation.py tests/unit/test_theme.py -q` | PASS (4/4) |
| `python -m mypy app/ --strict` | PASS (32 files) |
| `python -m pytest -q` | PASS (full suite) |

## Findings

### F1 — FileImportView resetuje wczytany plik przy ponownym wejściu

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: app/ui/views/file_import.py:47-48
- **Detail**: Każde `__init__` zeruje `eeg_path` i `recording_date`. Powrót z mapowania kanałów lub Wstecz→Dalej wymusza ponowny wybór pliku mimo że `available_channels` mogą nadal być w stanie.
- **Fix**: Nie czyścić stanu przy re-entry; przywracać UI z `app_state` gdy `eeg_path` jest ustawiony (zerować tylko przy „Nowe badanie”).
- **Decision**: FIXED — `_restore_from_state()` + brak resetu w `__init__`

### F2 — Callback walidacji pliku po zniszczeniu widoku

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/ui/views/file_import.py:210-238
- **Detail**: Wątek walidacji woła `self.after(0, _on_result)`. Użytkownik może kliknąć Wstecz w trakcie — callback dotknie zniszczonego widgetu.
- **Fix**: Guard `if not self.winfo_exists(): return` na początku `_on_result` lub token walidacji anulowany w `destroy`.
- **Decision**: FIXED — guard w `_on_result`

### F3 — Historia zawsze aktywna (plan: disabled gdy pusto)

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: app/ui/app_window.py:153-155
- **Detail**: Plan Fazy 2 wymagał `Historia disabled gdy history_store pusty`. Implementacja zawsze `state="normal"` — świadoma zmiana UX po feedbacku użytkownika; Progress 2.4 opis nieaktualny.
- **Fix**: Udokumentować w planie jako addendum ALBO przywrócić disabled z czytelnym `text_color_disabled`.
- **Decision**: FIXED — addendum w plan.md Phase 2

### F4 — Aktywny krok steppera bez bold etykiety

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: app/ui/components/stepper.py:95-99
- **Detail**: Plan: aktywny krok — „etykieta bold”. Kod używa `font_caption()` bez `weight="bold"`.
- **Fix**: Dla aktywnego kroku użyć `font_subheading()` lub `font_caption()` z `weight="bold"`.
- **Decision**: FIXED — `font_subheading()` dla aktywnego kroku

### F5 — return_view zamiast return_target

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: app/ui/app_window.py:138-148, app/ui/views/history.py
- **Detail**: Plan przewidywał `return_target="results"|"metadata"`. Implementacja używa `return_view=type(current_view)` — lepsze UX (powrót na dowolny ekran źródłowy).
- **Fix**: Zaktualizować kontrakt w planie; kod zostawić.
- **Decision**: FIXED — addendum Phase 2 w plan.md

### F6 — category_chip nieużywany w HistoryView

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/ui/views/history.py:231-238
- **Detail**: Phase 1 dodał `category_chip()`; historia nadal inline `CTkLabel` z `corner_radius=4`. Plan Phase 4 przewiduje migrację.
- **Fix**: Odłożyć do Phase 4 (zgodnie z planem).
- **Decision**: SKIPPED — Phase 4

### F7 — HistoryView ma własny przycisk powrotu (Phase 4 debt)

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: app/ui/views/history.py:57-62
- **Detail**: Phase 4 przenosi powrót do stopki shell. Obecnie header_row z „← Wróć do …” nadal w widoku.
- **Fix**: Phase 4 — `set_footer` + usunięcie `header_row`.
- **Decision**: SKIPPED — Phase 4

## Phase Summary

| Phase | Verdict | Notes |
|-------|---------|-------|
| P1 Tokeny + prymitywy | PASS | Triage 71e420d domknął review gaps |
| P2 Shell | PASS z driftem | Historia, return_view, stepper bold |
| P3 Formularze 60/40 | PASS | Footer, responsywność, checkbox wrap |

Brak pozycji MISSING blokujących Phase 4.
