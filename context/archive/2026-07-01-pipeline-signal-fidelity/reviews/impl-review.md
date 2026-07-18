<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Pipeline Signal Fidelity

- **Plan**: `context/changes/pipeline-signal-fidelity/plan.md`
- **Scope**: Full plan (Phases 1–4)
- **Date**: 2026-07-06
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical, 2 warnings, 3 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | PASS |
| Scope Discipline | PASS |
| Safety & Quality | WARNING |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | PASS |

## Findings

### F1 — Segment extension applies to OO/OZ, not only ZP

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: `app/domain/pipeline.py:134-137`
- **Detail**: `_MIN_USABLE_SEGMENT_S` extension runs for every zero-duration segment when the next onset is 1–16 s away — including OO→OZ and OZ→ZP via `selected[index+1]`. If task markers were <16 s apart (non-clinical but possible), OO could extend to +180 s and overlap the next segment, contradicting `docs/EEG-segmentacja.md` (segment ends at next task marker). Plan Phase 4 specified extension for ZP + ending markers only; implementation is broader.
- **Fix A ⭐ Recommended**: Scope extension to the last selected task (ZP) and/or `_next_annotation_onset_after` path only — keep OO/OZ ending at next task onset regardless of gap.
  - Strength: Matches domain docs and plan contract; eliminates overlap class.
  - Tradeoff: Requires passing task index or a `is_last_segment` flag into `_annotation_segment_end`.
  - Confidence: HIGH — existing tests use gaps ≥160 s; scoped change should not break them.
  - Blind spot: Haven't verified all real patient EDF marker spacing <16 s between OO and OZ.
- **Fix B**: Document broader rule in `docs/EEG-segmentacja.md` as intentional
  - Strength: No code change.
  - Tradeoff: Leaves overlap edge case for abnormal marker spacing.
  - Confidence: LOW — product docs currently say opposite.
  - Blind spot: Clinical frequency of <16 s OO→OZ gaps unknown.
- **Decision**: FIXED via Fix A — `enforce_min_segment_length` only on last task (ZP) in `_segments_from_annotations`

### F2 — R4 multi-band synthetic may flirt with 200 µV gate

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria / Reliability
- **Location**: `tests/integration/test_pipeline_fidelity.py:34-39,70`
- **Detail**: Four in-phase sinusoids at 50 µV peak each can sum to theoretical p-p up to ~400 µV on a single epoch, phase-dependent. Tests pass today but R4 bounds test could become flaky across MNE versions or phase alignment.
- **Fix**: Lower `peak_uv` to ~25–30 µV in the bounds test (still >5 µV post-filter) or use single 6 Hz component like unit `test_pipeline.py` with per-band parametrized runs.
- **Decision**: FIXED — bounds test uses `peak_uv=30.0`

### F3 — Fixture generator docstring size estimate stale

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: `tests/fixtures/generate_digitrack_fixture.py:6`
- **Detail**: Docstring says `~1–2 MB`; committed fixture is ~4.5 MB (within plan <5 MB). Intent met; estimate misleading for regenerators.
- **Fix**: Update docstring to `~4–5 MB` (120k blocks × 19 ch).
- **Decision**: FIXED — docstring updated

### F4 — Duplicated synthetic EEG helper

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: `tests/integration/test_pipeline_fidelity.py:24-53` vs `tests/unit/test_pipeline.py:16-36`
- **Detail**: Two `_synthetic_raw_with_annotations()` implementations (multi-band vs 6 Hz). Plan allowed optional extract; unit comment correctly points to integration for bounds.
- **Fix**: Extract shared helper to `tests/helpers/synthetic_eeg.py` when next touch — not blocking.
- **Decision**: SKIPPED — acceptable duplication with cross-reference comment

### F5 — Hardcoded patient path in fixture generator

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Maintainability
- **Location**: `tests/fixtures/generate_digitrack_fixture.py:17`
- **Detail**: `SOURCE = D:/CVGOSI/NF dane/Testowe/Kuczyński.EEG` — manual-only script per docstring; CI uses committed binary. Other devs cannot regenerate without edit.
- **Fix**: Add `NEUROFLAG_DIGITRACK_SOURCE` env var override with current path as default.
- **Decision**: SKIPPED — manual-only script; CI uses committed binary

## Success Criteria Verification

| Phase | Check | Result |
|-------|-------|--------|
| 1–4 | `pytest tests/integration/ -v` | PASS (6/6) |
| 4 | `pytest tests/unit/test_pipeline.py -v` | PASS (17/17) |
| 4 | `mypy app/ --strict` | PASS |
| 1–4 | `pytest -q` | PASS (full suite) |
| Manual | Progress items `[x]` with SHA | All 4 phases complete (2db6eb7, 63a826b, 38d12c6, 6e5fd36) |

**Conditional items correctly skipped:** DigiTrack calibration fix in `eeg_file.py` — smoke passes, `any(v > 1.0)` holds; no change required per plan contract.

## Commits Reviewed

- `2db6eb7` — Phase 1 fixture + scaffold
- `63a826b` — Phase 2 R4 tests
- `38d12c6` — Phase 3 R5 tests
- `6e5fd36` — Phase 4 ZP fix + test-plan
- `666ddff` — epilogue
