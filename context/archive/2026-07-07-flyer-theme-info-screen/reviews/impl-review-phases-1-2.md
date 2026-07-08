<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Motyw z ulotki i ekran Informacje

- **Plan**: context/changes/flyer-theme-info-screen/plan.md
- **Scope**: Phases 1–2 of 3 (Phase 3 pending)
- **Date**: 2026-07-07
- **Verdict**: APPROVED
- **Findings**: 0 critical, 0 warnings, 5 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS ✅ |
| Scope Discipline | PASS ✅ |
| Safety & Quality | PASS ✅ |
| Architecture | PASS ✅ |
| Pattern Consistency | PASS ✅ |
| Success Criteria | PASS ✅ |

## Automated Verification (re-run 2026-07-07)

| Command | Result |
|---------|--------|
| `python -m pytest tests/unit/test_info_content.py -q` | PASS (4/4) |
| `python -m pytest -q` | PASS (full suite) |
| `python -m mypy app/ --strict` | PASS (29 files) |

Manual Progress items 1.3 and 2.4 marked `[x]` with user confirmation in session.

## Phase 1 Carry-over

Prior review (`impl-review-phase-1.md`) findings F1–F4 were fixed in commit `867a187`:
- `COLOR_ACCENT_HOVER_DEEP` added for JSON third hover tier
- CTkButton/OptionMenu light-mode text → `#1A2B3C` (accessibility vs flyer white-on-orange)
- `tests/unit/test_theme.py` sync test added

Intentional drift from original plan contract: dark text on orange buttons (documented in Phase 1 triage). No open blockers.

## Findings

### F1 — Stacked modals on repeated „Informacje” clicks

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/ui/app_window.py:71-72
- **Detail**: `_show_info()` always creates a new `InfoDialog`. Repeated clicks can stack modals and steal `grab_set`. Same pattern as `_EditStudyDialog` in `history.py`.
- **Fix**: Track `_info_dialog: InfoDialog | None` and skip creation if `winfo_exists()`, or disable the chrome button while open.
- **Decision**: FIXED — singleton guard in `app_window._show_info()`

### F2 — Silent `webbrowser.open` failure

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/ui/components/info_dialog.py:161-162
- **Detail**: `webbrowser.open()` has no error handling; failure is silent. Plan notes browser behavior is OS-controlled.
- **Fix**: Wrap in `try/except OSError` and show a Polish `messagebox.showerror` with the URL to copy manually.
- **Decision**: FIXED — `try/except OSError` + polski messagebox

### F3 — `CTk` vs `CTkBaseClass` in dialog signature

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/ui/components/info_dialog.py:12,20
- **Detail**: `show_info_dialog(parent: ctk.CTk, …)` uses `CTk` while Phase 2 widened all flow views to `CTkBaseClass` for mypy. Works today because caller passes `AppWindow`.
- **Fix**: Widen to `CTkBaseClass` for consistency with flow views.
- **Decision**: FIXED — typy poszerzone na `CTkBaseClass`

### F4 — Dual import path for `show_info_dialog`

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/ui/app_window.py:14 / app/ui/components/__init__.py:3-5
- **Detail**: `app_window` imports from `info_dialog` directly; `components/__init__.py` also re-exports. Dual paths, not harmful.
- **Fix**: Pick one convention (direct submodule import or package re-export).
- **Decision**: FIXED — import z pakietu `app.ui.components`

### F5 — Partial NEUROD branding test coverage

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: tests/unit/test_info_content.py:19-20
- **Detail**: NEUROD guard only asserts `PRODUCT_DESCRIPTION`. `VALUE_BULLETS`, `OFFLINE_NOTE`, contact roles untested. Grep over `app/ui/` has zero NEUROD matches.
- **Fix**: Parametrize over all string constants in `info_content.py`.
- **Decision**: FIXED — `@pytest.mark.parametrize` po `_all_info_strings()`
