<!-- PLAN-REVIEW-REPORT -->
# Plan Review: PDF Report & Save

- **Plan**: context/changes/pdf-report-and-save/plan.md
- **Mode**: Deep
- **Date**: 2026-06-22
- **Verdict**: REVISE
- **Findings**: 0 critical | 2 warnings | 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | PASS |
| Lean Execution | PASS |
| Architectural Fitness | PASS |
| Blind Spots | WARNING |
| Plan Completeness | WARNING |

## Grounding

5/5 paths ✓, 3/3 symbols ✓, brief↔plan ✓

Paths verified: `app/ui/views/results_grid.py`, `app/ui/app_window.py`, `app/domain/types.py`, `app/__init__.py`, `neuroflag.spec`.
Symbols verified: `_COLOR_BG/_COLOR_FG/_TASK_LABELS/_CATEGORY_COLOR` at `results_grid.py:13–35`, `AppState.{metadata,analysis_result,norms_config}` at `app_window.py:14–17`, `NormsConfig.observation_checklist` at `types.py:118`.
Blast radius: only `analysis.py` imports `ResultsGridView`; color constants are private with no external callers. `norms.json` `observation_checklist` shape confirmed (title, intro, categories[{title, items}]).

## Findings

### F1 — test_disclaimer_present will fail on Polish diacritics

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Blind Spots
- **Location**: Phase 4 — Unit Tests, test_disclaimer_present
- **Detail**: `DISCLAIMER_PL[:40]` = "Raport jest narzędziem przesiewowym i nie" contains "ę" (U+0119). ReportLab encodes text using PDFDocEncoding/WinAnsiEncoding in content streams, where "ę" is byte 0xe9 — NOT the UTF-8 sequence \xc4\x99. Searching `DISCLAIMER_PL[:40].encode()` (UTF-8) in raw PDF bytes will not find it. The test fails deterministically.
- **Fix A ⭐ Recommended**: Use `b"NeuroFlag"` as the ASCII-safe search anchor (appears in the disclaimer's final sentence; pure ASCII; survives any ReportLab encoding).
  - Strength: Zero extra deps; reliable regardless of font/encoding config.
  - Tradeoff: Weaker assertion — proves "NeuroFlag appears" not "full disclaimer is present".
  - Confidence: HIGH — ASCII identifiers are written as-is in ReportLab PDF streams.
  - Blind spot: Would fail if ReportLab enabled content stream compression (not the case for Platypus SimpleDocTemplate defaults).
- **Fix B**: Add `pdfminer.six` as test-only dev dep; decode content stream before searching.
  - Strength: Robust; tests actual rendered text.
  - Tradeoff: Adds dev dependency; increases test complexity.
  - Confidence: MED — pdfminer is well-established but adds install weight; plan explicitly wanted to avoid it.
  - Blind spot: pdfminer must be kept out of pyproject.toml `[project.dependencies]` to avoid shipping in .exe.
- **Decision**: FIXED via Fix A — plan.md Phase 4 updated to use `b"NeuroFlag"` anchor with rationale comment.

### F2 — _on_save_pdf: None guards missing → mypy --strict failure

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 3 — _on_save_pdf contract
- **Detail**: `AppState.metadata` is typed `PatientMetadata | None` and `AppState.analysis_result` is `AnalysisResult | None`. `generate_report()` expects non-optional types. Under `mypy --strict`, passing these fields directly is a type error. Phase 3's own success criterion includes `mypy app/ --strict` — it will fail without explicit narrowing guards.
- **Fix**: Add at the top of `_on_save_pdf`:
  ```python
  if self._app_state.analysis_result is None or self._app_state.metadata is None:
      return  # structurally unreachable; satisfies mypy --strict
  ```
- **Decision**: FIXED — guard added to Phase 3 contract in plan.md.

### F3 — generate_report() exception not caught in _on_save_pdf

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 3 — _on_save_pdf error handling contract
- **Detail**: The plan's `messagebox.showerror` wraps only `Path.write_bytes()`. If `generate_report()` raises (e.g. a ReportLab internal error, unexpected None field), the exception propagates uncaught to the tkinter event loop — silently dropped or shown as a console traceback.
- **Fix**: Extend the try/except block to cover both `generate_report()` and `write_bytes()` in one block with a Polish-language error message.
- **Decision**: FIXED — Phase 3 contract updated to show unified try/except covering both calls.
