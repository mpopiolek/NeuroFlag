<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Motyw z ulotki i ekran Informacje

- **Plan**: context/changes/flyer-theme-info-screen/plan.md
- **Scope**: Phase 1 of 3
- **Date**: 2026-07-07
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical, 2 warnings, 2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | WARNING ⚠️ |
| Scope Discipline | PASS ✅ |
| Safety & Quality | WARNING ⚠️ |
| Architecture | PASS ✅ |
| Pattern Consistency | PASS ✅ |
| Success Criteria | PASS ✅ |

## Findings

### F1 — CTkOptionMenu hover uses undeclared third-tier orange

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: app/ui/assets/themes/neuroflag.json:89
- **Detail**: Plan contract maps all blue accent replacements to `theme.py` values (`#F9A825` / `#E09000`). `CTkOptionMenu.button_hover_color` uses `#C87F00`, which has no corresponding constant in `theme.py`. Pre-commit blue theme also had a third hover tier (`#163F6E`), so this mirrors prior JSON structure — but Phase 1 contract explicitly ties JSON to `theme.py`.
- **Fix**: Add `COLOR_ACCENT_HOVER_DEEP = "#C87F00"` to `theme.py` (or change JSON to `#E09000` for strict two-tier parity).
- **Decision**: FIXED via Fix A — added `COLOR_ACCENT_HOVER_DEEP = "#C87F00"` to theme.py

### F2 — Primary button contrast below WCAG AA

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: app/ui/assets/themes/neuroflag.json:18-22 (CTkButton and mirrored accent widgets)
- **Detail**: White text (`#FFFFFF`) on orange accent (`#F9A825`) yields ~2.0:1 contrast ratio vs ~6.1:1 on previous blue `#2563A8`. Fails WCAG AA (4.5:1 normal, 3:1 large). Manual step 1.3 passed (user confirmed readability), and flyer fidelity is the stated goal — but accessibility regressed.
- **Fix A ⭐ Recommended**: Accept as flyer-faithful trade-off; document in plan or change notes that orange-on-white is intentional per NEUROD branding.
  - Strength: Preserves approved visual design; manual verification already passed.
  - Tradeoff: WCAG AA non-compliance on primary CTAs.
  - Confidence: HIGH — plan explicitly specifies `#F9A825` from flyer.
  - Blind spot: Users with low vision not covered by single manual check.
- **Fix B**: Darken accent to ~`#C87F00` or use dark text on buttons for ≥3:1 while keeping orange identity.
  - Strength: Better accessibility.
  - Tradeoff: Deviates from flyer orange; may affect brand match.
  - Confidence: MED — requires re-manual verification.
  - Blind spot: Darker orange may still fail 4.5:1 for body-sized label text.
- **Decision**: FIXED via Fix B — kept `#F9A825` accent; CTkButton and CTkOptionMenu light-mode text → `#1A2B3C`

### F3 — Accent palette duplicated across Python and JSON

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/ui/theme.py:26-27 / app/ui/assets/themes/neuroflag.json
- **Detail**: `COLOR_ACCENT` and `COLOR_ACCENT_HOVER` exist in Python but JSON repeats hex literals. Phase 1 updated both consistently; no sync test exists. Drift risk on future edits.
- **Fix**: Optional — add unit test asserting JSON accent keys match `theme.py` constants; Phase 2 custom widgets should import from `theme.py`.
- **Decision**: FIXED — added `tests/unit/test_theme.py` sync test

### F4 — Accent orange adjacent to RAG yellow

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: app/ui/theme.py:26 / app/ui/components/rag_colors.py:7
- **Detail**: CTk accent `#F9A825` vs RAG yellow `#F5A800` are visually close (Δ mainly in green channel). Plan requires distinguishability; manual 1.3 confirmed pass.
- **Fix**: No action needed if manual check holds; monitor on real displays during Phase 2 results view testing.
- **Decision**: FIXED — accepted; monitor during Phase 2 manual verification
