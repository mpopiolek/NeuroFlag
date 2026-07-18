<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Redesign UI — Wariant B

- **Plan**: context/changes/ui-redesign-brand-layout/plan.md
- **Scope**: Phases 1–5 of 5 (full plan)
- **Date**: 2026-07-09
- **Commits**: a43fd54 … a749822 (ui-redesign phases + epilogue fixes)
- **Verdict**: NEEDS ATTENTION (post-triage: 8 fixed)
- **Findings**: 1 critical, 6 warnings, 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | WARNING |
| Scope Discipline | WARNING |
| Safety & Quality | FAIL |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

## Automated Verification

| Command | Result |
|---------|--------|
| `python -m pytest tests/unit/test_navigation.py tests/unit/test_theme.py -q` | PASS (4/4) |
| `python -m mypy app/ --strict` | PASS (36 files) |
| `python -m pytest -q` | PASS (full suite) |

## Findings

### F1 — Analiza nie jest anulowana przy zamknięciu overlay

- **Severity**: ❌ CRITICAL
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: app/ui/app_window.py:260-263
- **Detail**: `_dismiss_analysis_overlay()` niszczy widget, ale nie woła `cancel_event.set()`. Nawigacja (Historia, Informacje, `show_view`) zamyka overlay bez zatrzymania wątku `AnalysisRunner`. `start_analysis_overlay()` blokuje tylko gdy `_analysis_overlay is not None` — po dismiss można uruchomić drugą analizę równolegle z pierwszą.
- **Fix**: W `_dismiss_analysis_overlay()` ustaw `app_state.cancel_event.set()` i opcjonalnie trzymaj referencję do aktywnego runnera; blokuj `start_analysis_overlay()` dopóki wątek się nie zakończy. Wzorzec anulowania już istnieje w `analysis_overlay.py:74-76`.
- **Decision**: FIXED — cancel_event w _dismiss_analysis_overlay + analysis_in_progress blokuje równoległy start

- **Severity**: ⚠️ WARNING
- **Impact**: 🔬 HIGH — architectural stakes; think carefully before deciding
- **Dimension**: Plan Adherence
- **Location**: app/ui/views/results_grid.py:71-115
- **Detail**: Plan Phase 4 wymaga `two_column_body(left_weight=2, right_weight=3)` — kategoria po lewej, siatka po prawej. Implementacja używa pionowego stosu: karta podsumowania `row=0`, siatka `row=1` na pełną szerokość. Styl kart (pasek kategorii, dynamiczna siatka) jest zgodny; layout nie.
- **Fix A ⭐ Recommended**: Przebudować na `two_column_body(left_weight=2, right_weight=3)` zgodnie z planem
  - Strength: Pełna zgodność z mockupem Wariantu B i kontraktem Phase 4.
  - Tradeoff: Większy diff; wymaga testu manualnego na wąskim oknie.
  - Confidence: HIGH — helper `two_column_body` już istnieje i jest używany w innych widokach.
  - Blind spot: Zachowanie stacku przy <900 px na ekranie wyników nie było testowane w tym układzie.
- **Fix B**: Udokumentować w planie addendum jako świadomą zmianę UX (pionowy dashboard)
  - Strength: Brak pracy implementacyjnej.
  - Tradeoff: Rozjazd z mockupem i kontraktem Phase 4.
  - Confidence: MEDIUM — wymaga akceptacji produktowej.
  - Blind spot: Użytkownicy oczekujący layoutu z researchu.
- **Decision**: FIXED via Fix B — addendum Phase 4 w plan.md

### F3 — InfoView zamiast modala Informacje (poza planem)

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Scope Discipline
- **Location**: app/ui/views/info_view.py, app/ui/app_window.py:139-149
- **Detail**: Plan Phase 4 przewidywał odświeżenie `info_dialog.py` (lekkie karty w modalu). Commit `90136fa` dodał pełnoekranowy `InfoView` z `preserve_stepper=True` i wspólnym wzorcem powrotu jak Historia. `InfoView` nie jest w `VIEW_STEP`.
- **Fix A ⭐ Recommended**: Dodać addendum do plan.md opisujące InfoView jako docelowy wzorzec (spójny z Historią)
  - Strength: Zachowuje lepsze UX; aktualizuje źródło prawdy przed kolejnymi review.
  - Tradeoff: Plan rozszerza zakres po epilogu.
  - Confidence: HIGH — wzorzec `return_view` + `preserve_stepper` jest spójny.
  - Blind spot: Brak.
- **Fix B**: Przywrócić modal `InfoDialog` z nowymi kartami
  - Strength: Ścisła zgodność z planem Phase 4.
  - Tradeoff: Regresja UX wprowadzona w `90136fa`.
  - Confidence: LOW — użytkownik świadomie zmienił na widok główny.
  - Blind spot: Intencja autora commitu.
- **Decision**: FIXED via Fix A — addendum Phase 2 w plan.md

### F4 — Historia bez preserve_stepper skacze stepper na krok 4

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/ui/app_window.py:161, app/ui/navigation.py:18
- **Detail**: `open_info()` przekazuje `preserve_stepper=True`; `open_history()` nie. `VIEW_STEP[HistoryView]=4` — otwarcie historii z kroku 1–2 fałszywie oznacza wizard jako ukończony.
- **Fix**: Dodać `preserve_stepper=True` w `open_history()` — analogicznie do `open_info()`.
- **Decision**: FIXED — preserve_stepper=True w open_history()

### F5 — eeg_path zerowany przed zakończeniem walidacji

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: app/ui/views/file_import.py:265-266
- **Detail**: Wybór nowego pliku natychmiast czyści `eeg_path` i `recording_date`. Przy błędzie walidacji lub nawigacji w trakcie tracony jest poprzednio zatwierdzony plik bez rollbacku.
- **Fix**: Trzymać poprzedni `eeg_path` do momentu sukcesu `_on_result`; commitować nową ścieżkę dopiero po walidacji.
- **Decision**: FIXED — brak wczesnego czyszczenia eeg_path; rollback UI przy błędzie

### F6 — Blokada walidacji pliku bez feedbacku

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/ui/views/file_import.py:249-251
- **Detail**: Gdy `_validating=True`, kolejne kliknięcia pickera są ignorowane bez komunikatu. Przy wolnych plikach EDF użytkownik nie może anulować ani wybrać innego pliku.
- **Fix**: Wyłączyć przycisk wyboru pliku i pokazać status „Wczytywanie…” albo dodać token generacji w `_on_result` ignorujący nieaktualne wyniki.
- **Decision**: FIXED — disabled picker + status „Wczytywanie pliku…”

### F7 — Mapowanie kanałów bez walidacji duplikatów

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/ui/components/channel_mapping_dialog.py:132-141
- **Detail**: `_submit()` akceptuje przypisanie tego samego kanału fizycznego do C3 i O1. Błąd ujawnia się dopiero w pipeline jako nieczytelny komunikat.
- **Fix**: W `_submit()` / `_refresh_continue_button()` odrzucić duplikaty z polskim komunikatem inline.
- **Decision**: FIXED — walidacja unikalności kanałów w _submit()

### F8 — Cichy błąd zapisu historii

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality
- **Location**: app/ui/views/analysis.py:64-65
- **Detail**: `persist_analysis_result()` łapie wyjątki SQLite i tylko `print` do stderr. Użytkownik widzi wyniki bez informacji, że badanie nie trafiło do historii.
- **Fix**: `messagebox.showwarning` po polsku przy błędzie zapisu; nadal nawigować do wyników (analiza się udała).
- **Decision**: FIXED — messagebox.showwarning przy błędzie zapisu

### F9 — Zduplikowany helper _back_label_for

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/ui/views/history.py:35-52, app/ui/views/info_view.py:16-32
- **Detail**: Dwa niemal identyczne `_back_label_for()` — wersja w `history.py` zawiera `InfoView`, w `info_view.py` nie. Ryzyko rozjazdu etykiet stopki.
- **Fix**: Wyciągnąć jeden helper do `app/ui/navigation.py` i importować w obu widokach.
- **Decision**: FIXED — back_label_for() w navigation.py
