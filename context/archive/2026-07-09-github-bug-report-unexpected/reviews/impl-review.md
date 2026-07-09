<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Zgłaszanie błędów nieoczekiwanych

- **Plan**: context/changes/github-bug-report-unexpected/plan.md
- **Scope**: Full plan (Phases 1–4)
- **Date**: 2026-07-09
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical, 5 warnings, 3 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | WARNING |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | PASS |
| Success Criteria | WARNING |

## Findings

### F1 — Podpowiedź używa font_body zamiast font_small

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: app/ui/views/file_import.py:281-287
- **Detail**: Plan Phase 3 wymaga `font_small` + `COLOR_TEXT_SECONDARY` dla podpowiedzi pod statusem. Implementacja używa `w.body_label(..., secondary=True)`, co mapuje na `font_body()` — wizualnie bliżej body niż small caption.
- **Fix**: Zamień na `ctk.CTkLabel(..., font=t.font_small(), text_color=t.COLOR_TEXT_SECONDARY)` lub dodaj parametr `small=True` do `body_label`.
- **Decision**: FIXED

### F2 — Flaga --debug-crash-gui poza planem

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Scope Discipline
- **Location**: app/main.py, app/ui/app_window.py, tests/unit/test_main_cli.py
- **Detail**: Dodano `--debug-crash-gui` i test parsera — nie ma tego w planie ani w „What We're NOT Doing”. Użyteczne do QA punktu 4.4, ale rozszerza powierzchnię CLI.
- **Fix A ⭐ Recommended**: Dopisz krótką notę w plan.md (Phase 4 Manual lub addendum) opisującą flagę QA.
  - Strength: Zachowuje helper; synchronizuje plan z kodem.
  - Tradeoff: Plan lekko się poszerza.
  - Confidence: HIGH — flaga jest izolowana i domyślnie wyłączona.
  - Blind spot: Brak wpisu w AGENTS.md / README dla deweloperów.
- **Fix B**: Usuń flagę po zakończeniu manual QA.
  - Strength: Ścisła zgodność ze scope planu.
  - Tradeoff: Trudniejsze powtarzalne testowanie modala.
  - Confidence: MED — user już prosił o flagę.
  - Blind spot: Nie wiadomo, czy QA będzie powtarzane przed release.
- **Decision**: FIXED (Fix A — nota w plan.md Phase 4 Manual)

### F3 — Moduł exception_hooks.py poza planem

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: app/ui/exception_hooks.py
- **Detail**: Plan dopuszczał hooki w `main.py` lub `app_window.py`; logika wydzielona do osobnego modułu. Zachowanie zgodne z kontraktem; to reorganizacja, nie nowa funkcja.
- **Fix**: Zaakceptować jako poprawę struktury — opcjonalnie jedna linia w plan Phase 4 „Changes Required” odnotowująca `exception_hooks.py`.
- **Decision**: FIXED (zaakceptowano + ścieżka w plan Phase 4)

### F4 — Brak logowania tracebacku przy nieobsłużonym wyjątku GUI

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: app/ui/exception_hooks.py:34-42
- **Detail**: `gui_excepthook` pokazuje modal użytkownikowi, ale nie loguje wyjątku na `stderr`. Deweloper/support nie ma śladu w konsoli przy polu bug report bez tracebacku (zgodnie z planem w UI).
- **Fix**: Wywołaj `traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)` przed `_schedule_uncaught_dialog`, zachowując modal bez tracebacku w issue body.
  - Strength: Zgodne z planem „bez tracebacku w body”; ułatwia debug lokalny.
  - Tradeoff: Minimalny — jedna linia import + wywołanie.
  - Confidence: HIGH — standardowy wzorzec.
  - Blind spot: W buildzie .exe użytkownik końcowy i tak nie widzi stderr.
- **Decision**: FIXED

### F5 — Brak testów jednostkowych dla hooków GUI

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Success Criteria
- **Location**: app/ui/exception_hooks.py (brak tests/unit/test_exception_hooks.py)
- **Detail**: Plan wymaga testów bug_report i info_content; hooki globalne są krytyczne dla Phase 4, ale nie mają testów (KeyboardInterrupt passthrough, `after(0, …)` scheduling).
- **Fix**: Dodaj `tests/unit/test_exception_hooks.py` z mockiem `AppWindow.after` i asercją ignorowania KeyboardInterrupt / schedule dialogu dla RuntimeError.
  - Strength: Chroni regresję ścieżki 4.4.
  - Tradeoff: ~40–60 linii testu.
  - Confidence: HIGH.
  - Blind spot: Pełny modal CTk nadal wymaga manual QA.
- **Decision**: FIXED (tests/unit/test_exception_hooks.py)

### F6 — Redundantny typ wyjątku w komunikacie i diagnostyce

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/ui/views/analysis.py:141-145
- **Detail**: `user_message_pl` zawiera `type(exc).__name__`, a body issue dodatkowo pole „Typ wyjątku” z `last_exception_type_name` — duplikat w GitHub body.
- **Fix**: Użyj stałego komunikatu PL bez nazwy klasy w `user_message_pl`; typ tylko w `exception_type_name`.
- **Decision**: FIXED

### F7 — segment_mode z poprzedniej analizy przy manual report

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/ui/bug_report.py:77-84
- **Detail**: Informacje → Zgłoś błąd (`manual=True`) nadal pokazuje `last_analysis_diagnostics.segment_mode` z wcześniejszej sesji — nie PII, ale może mylić.
- **Fix**: Dla `manual=True` bez aktywnej analizy ustaw `segment_mode="unknown"` w `collect_bug_report_context`.
- **Decision**: FIXED (+ test manual segment_mode)

### F8 — Wszystkie kroki manualne w Progress nadal [ ]

- **Severity**: 💡 OBSERVATION
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Success Criteria
- **Location**: context/changes/github-bug-report-unexpected/plan.md Progress
- **Detail**: 1.3, 2.3, 3.3, 4.3–4.5 pozostają niezaznaczone; brak SHA przy commitach fazowych (implementacja nie przeszła jeszcze phase-end commit ritual). Automated: wszystkie [x] — pytest + mypy PASS (2026-07-09).
- **Fix**: Dokończ manual QA (w tym `--debug-crash-gui` dla 4.4), potem phase commits i SHA write-back.
- **Decision**: PENDING — wymaga manual QA użytkownika przed phase commits
