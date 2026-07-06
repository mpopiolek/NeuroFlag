<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: PDF Report & Save

- **Plan**: context/changes/pdf-report-and-save/plan.md
- **Scope**: All phases (1–4 of 4)
- **Date**: 2026-06-23
- **Verdict**: NEEDS ATTENTION → APPROVED after triage
- **Findings**: 0 critical  5 warnings  4 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | WARNING |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

## Automated Checks

| Check | Result |
|-------|--------|
| pytest (all 100 tests) | PASS |
| test_pdf_generator.py (7 tests after triage) | PASS |
| mypy app/ --strict (22 source files) | PASS |
| coverage >80% | SKIP (pytest-cov not installed) |

## Findings

### F1 — Hardcoded C:/Windows/Fonts path

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/reports/pdf_generator.py:24
- **Detail**: `_FONTS_DIR = Path("C:/Windows/Fonts")` — on machines with Windows on a drive other than C: Arial is never found, Helvetica fallback activates silently.
- **Fix**: `_FONTS_DIR = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"`
- **Decision**: FIXED

### F2 — _register_fonts() called at module level without try/except

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: app/reports/pdf_generator.py:38
- **Detail**: If a .ttf file exists but is corrupt, TTFont() raises at import time — entire module fails to load. Also `pdfmetrics.registerFont` is not idempotent — re-importing in tests causes KeyError for "Arial".
- **Fix**: Wrapped in `try/except Exception: _BASE_FONT = "Helvetica"` + idempotency guard `if "Arial" not in pdfmetrics.getRegisteredFontNames()`.
- **Decision**: FIXED (Fix A)

### F3 — tests/unit/run_pdf_test.py — temporary debug script committed

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: tests/unit/run_pdf_test.py
- **Detail**: Marked `# tymczasowy, do usunięcia`. Uses relative path to norms.json (fragile), writes test_output.pdf without cleanup, uses `__import__` antipattern. All cases covered by test_pdf_generator.py.
- **Fix**: Deleted the file.
- **Decision**: FIXED

### F4 — Enum comparison via string instead of object identity

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/reports/pdf_generator.py:169
- **Detail**: `cell.color.value in ("red", "green")` compares raw strings. If CellColor values change, yellow cells silently get white text. Established pattern in algorithm.py uses `is CellColor.RED`.
- **Fix**: `fg = colors.white if cell.color in (CellColor.RED, CellColor.GREEN) else colors.HexColor("#1A1A1A")`
- **Decision**: FIXED

### F5 — test_no_uv_values_in_output only scans PDF metadata, not content

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: tests/unit/test_pdf_generator.py:120
- **Detail**: Test scanned only uncompressed /Info dictionary. Domain rule "µV never in PDF" is critical, but test would not catch future regression if a description string contained µV values.
- **Fix (Fix A)**: Split into two tests: `test_no_uv_in_pdf_metadata` (original /Info scan) + `test_no_uv_values_in_output` (UTF-8 µV `\xc2\xb5V` scan on raw bytes). Single-byte `\xb5V` excluded from raw scan as it collides with binary PDF data.
- **Decision**: FIXED (Fix A)

### F6 — norms.py: unplanned ObservationChecklist additions

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: app/domain/norms.py
- **Detail**: Plan did not list norms.py. Implementation added `_parse_observation_checklist()`, `_DEFAULT_OBSERVATION_CHECKLIST` (~72 lines), and `load()` update — required prerequisites for PDF Section 3. Plan assumed `NormsConfig.observation_checklist` already existed.
- **Fix**: Addendum added to plan.md documenting norms.py as required change.
- **Decision**: FIXED

### F7 — No visual confirmation after successful PDF save

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/ui/views/results_grid.py:161
- **Detail**: Success path was silent — errors had messagebox.showerror but success had no counterpart. User might click the button again thinking it failed.
- **Fix**: Added `messagebox.showinfo("Raport zapisany", f"Raport PDF zapisano w:\n{path}")` after `write_bytes()`.
- **Decision**: FIXED

### F8 — test_disclaimer_present checks b"NeuroFlag", not disclaimer text

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: tests/unit/test_pdf_generator.py:128
- **Detail**: Test name implied DISCLAIMER_PL content check but asserted `b"NeuroFlag"` in /Title metadata.
- **Fix**: Renamed to `test_pdf_metadata_title_present`.
- **Decision**: FIXED

### F9 — _hex_to_color(): one-liner wrapper with no added value

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/reports/pdf_generator.py:52
- **Detail**: `return colors.HexColor(hex_str)` with no validation or logic. Line 120 already called `colors.HexColor("#555555")` directly — inconsistency.
- **Fix**: Removed function; replaced call site with `colors.HexColor(RAG_COLOR_BG[cell.color])` directly.
- **Decision**: FIXED
