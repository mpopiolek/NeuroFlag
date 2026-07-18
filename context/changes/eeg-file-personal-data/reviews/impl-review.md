<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Dane osobowe w plikach EEG

- **Plan**: context/changes/eeg-file-personal-data/plan.md
- **Scope**: All phases (1–3)
- **Date**: 2026-06-26
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical, 1 warning, 5 observations

## Verdicts

| Dimension | Verdict |
|---|---|
| Plan Adherence | PASS ✅ |
| Scope Discipline | PASS ✅ |
| Safety & Quality | WARNING ⚠️ (F1) |
| Architecture | PASS ✅ |
| Pattern Consistency | WARNING ⚠️ (F2) |
| Success Criteria | PASS ✅ |

## Findings

### F1 — Checkbox label implies on-disk file modification

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: app/ui/views/file_import.py:62–66
- **Detail**: The checkbox text `"Wyczyść dane identyfikacyjne z nagłówka pliku przed analizą"` implies to a clinical user that the file itself is sanitised. In practice `raw.anonymize()` operates in-memory only — the original file on disk is never touched. In a medical context staff may archive or forward the same file assuming PII was removed. The only disclaimer about in-memory operation sits in `MetadataFormView`, a separate screen the user may not recall at the moment they see the checkbox.
- **Fix A ⭐ Recommended**: Append `" (tylko w pamięci — plik nie jest modyfikowany)"` to the checkbox text.
  - Strength: Inline clarification at the exact decision point; no extra widget, no layout change.
  - Tradeoff: Slightly longer label — but wraplength on the container allows it.
  - Confidence: HIGH — the existing privacy block in MetadataFormView uses the same in-memory framing.
  - Blind spot: None significant.
- **Fix B**: Add a small `CTkLabel` sub-note directly under the checkbox.
  - Strength: Visually separate and easier to style/translate.
  - Tradeoff: More widget clutter; requires layout adjustment.
  - Confidence: MEDIUM — depends on preferred UX density.
  - Blind spot: None significant.
- **Decision**: FIXED via Fix A

### F2 — `_info_frame` local variable uses misleading `_` prefix

- **Severity**: 👁️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/ui/views/metadata_form.py:106
- **Detail**: `_info_frame` uses the `_` prefix convention. In this codebase `_` consistently marks private *instance* attributes (`self._warning_label`, `self._age_var`, etc.). A plain local variable with that prefix is misleading to future readers.
- **Fix**: Rename to `info_frame` (no underscore).
- **Decision**: FIXED

### F3 — `raw.anonymize()` raises unhandled exception with generic error surfaced to user

- **Severity**: 👁️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality (Reliability)
- **Location**: app/domain/pipeline.py:332–333
- **Detail**: `raw.anonymize(daysback=None, keep_his=False)` has no dedicated `try/except`. If it raises (e.g. malformed `raw.info` from a non-standard device), the outer catch in `AnalysisView._analysis_worker` surfaces `"unexpected_error"` — a generic Polish message with no actionable guidance.
- **Fix**: Wrap in `try/except Exception` and raise `PipelineError("anonymize_failed", "Nie udało się wyczyścić nagłówka pliku.")`, or add `"anonymize_failed"` to `_ERROR_CODE_PL` in `analysis.py`.
- **Decision**: FIXED (both: PipelineError raised + error code added to analysis.py)

### F4 — Untracked `# TODO` inside `DISCLAIMER_PL` production constant

- **Severity**: 👁️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/reports/pdf_generator.py:53
- **Detail**: `# TODO: weryfikacja eksperta domenowego przed wdrożeniem produkcyjnym` sits inside the parentheses of `DISCLAIMER_PL`. It represents a production-blocking legal review that is not tracked in the plan's Progress, in any open issue, or in `context/`. Easy to miss in a `grep TODO app/` scan.
- **Fix**: Move to `context/foundation/lessons.md` or a tracked risk entry, and remove the inline comment before the production build.
- **Decision**: FIXED (inline TODO removed; risk tracked in plan.md Open Risks section)

### F5 — `test_disclaimer_contains_privacy_text` pins only two words, not the full new sentence

- **Severity**: 👁️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: tests/unit/test_pdf_generator.py:155–157
- **Detail**: Only `"lokalnie"` and `"nagłówku"` are asserted. Removing the entire key clause about identifiers not being stored in the report would leave the test green. The plan spec drove this shape, so it is an intentional trade-off, not an oversight.
- **Fix**: Add `assert "nie są wyświetlane ani zapisywane w raporcie" in DISCLAIMER_PL` to pin the full new sentence.
- **Decision**: FIXED

### F6 — Anonymize test assertions throw `AttributeError` if MNE nullifies `subject_info` to `None`

- **Severity**: 👁️ OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality (Reliability)
- **Location**: tests/unit/test_pipeline.py:274–276
- **Detail**: `raw.info["subject_info"].get("first_name")` assumes `subject_info` is a non-`None` dict. MNE 1.8.0 replaces PII with `"mne_anonymize"` (not `None`) so the test is correct today. If MNE's behaviour changes, the test throws `AttributeError` instead of a clean assertion failure.
- **Fix**: Guard the assertion: `subj = raw.info["subject_info"]; assert subj is None or subj.get("first_name") != "Jan"`.
- **Decision**: FIXED
