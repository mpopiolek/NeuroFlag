<!-- PLAN-REVIEW-REPORT -->
# Plan Review: Zgłaszanie błędów nieoczekiwanych

- **Plan**: context/changes/github-bug-report-unexpected/plan.md
- **Mode**: Deep
- **Date**: 2026-07-09
- **Verdict**: SOUND (po triage)
- **Findings**: 2 critical  4 warnings  2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | PASS |
| Lean Execution | PASS |
| Architectural Fitness | PASS (po F1) |
| Blind Spots | PASS (po F3, F4, F7) |
| Plan Completeness | PASS (po F2, F5, F6) |

## Grounding

Grounding: 8/8 ścieżek ✓, 9/9 symboli ✓, brief↔plan ✓

## Findings

### F1 — Stopka obsługuje tylko jeden przycisk primary

- **Severity**: ❌ CRITICAL
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Architectural Fitness
- **Location**: Phase 3 — Stopka zgłoszenia w FileImportView
- **Detail**: `AppWindow.set_footer` ma wyłącznie jeden slot primary; plan mówił „obok / zamiast”.
- **Fix A ⭐ Recommended**: Przy `unexpected_error` zamienić primary stopki na „Zgłoś błąd na GitHubie”.
- **Decision**: FIXED via Fix A

### F2 — AnalysisDiagnostics frozen vs mutacja w pipeline

- **Severity**: ❌ CRITICAL
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 1 (typy) + Phase 2 (pipeline.run)
- **Detail**: Frozen dataclass + in-place mutation jest niespójne z `types.py`.
- **Fix**: `dataclasses.replace()` + zwracanie zaktualizowanego snapshotu z `pipeline.run`.
- **Decision**: FIXED

### F3 — Status C3/O1 „mapped” wymaga channel_overrides

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Blind Spots
- **Location**: Phase 1 — collect_bug_report_context
- **Detail**: `get_missing_canonical` ignoruje `channel_overrides`.
- **Fix A ⭐ Recommended**: Gałąź `mapped` z `bool(channel_overrides)`.
- **Decision**: FIXED via Fix A

### F4 — VIEW_STEP nie obejmuje InfoView / HistoryView

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 1 — mapowanie kroku aplikacji
- **Detail**: Brak jawnego mapowania widoków pomocniczych.
- **Fix**: Jawne mapowanie InfoView / HistoryView w kontrakcie Phase 1.
- **Decision**: FIXED

### F5 — channel_count_at_analysis to dane z wczytania

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 2 — AnalysisDiagnostics
- **Detail**: `available_channels` ustawiane przy walidacji pliku, nie w pipeline.
- **Fix**: `header_channel_count` z AppState w `collect_bug_report_context`.
- **Decision**: FIXED

### F6 — Brak pozycji Progress dla weryfikacji PII (Phase 4)

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Progress — Phase 4
- **Detail**: Brakujący manual check PII w Progress.
- **Fix**: Dodać `4.5 Body issue bez inicjałów i ścieżek dysku`.
- **Decision**: FIXED

### F7 — exc_value w modalu bez reguł sanityzacji

- **Severity**: 💡 OBSERVATION
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Blind Spots
- **Location**: Phase 4 — UncaughtErrorDialog
- **Detail**: `str(exc)` może zawierać ścieżki w UI modalu.
- **Fix**: Modal pokazuje tylko `exc_type_name` + ogólny komunikat PL.
- **Decision**: FIXED

### F8 — Plan-brief vs Phase 4 (szablon issue)

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Lean Execution
- **Location**: plan-brief Scope vs Phase 4.4
- **Detail**: Brief out-of-scope vs opcjonalna zmiana szablonu w planie.
- **Fix**: Phase 4.4 oznaczone jako poza MVP.
- **Decision**: FIXED
