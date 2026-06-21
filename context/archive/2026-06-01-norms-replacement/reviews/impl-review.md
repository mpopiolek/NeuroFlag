<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: S-04 Wymiana bazy norm

- **Plan**: context/changes/norms-replacement/plan.md
- **Scope**: Full plan (Phase 1–2 of 2)
- **Date**: 2026-06-21
- **Verdict**: NEEDS ATTENTION
- **Findings**: 1 critical  5 warnings  4 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | WARNING |
| Scope Discipline | PASS |
| Safety & Quality | FAIL |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | WARNING |

## Findings

### F-01 — docs/README-norms.md: stale schema teaches recommendation_threshold

- **Severity**: ❌ CRITICAL
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Safety & Quality / Plan Adherence
- **Location**: docs/README-norms.md:28, 70
- **Detail**: Tabela schematu i instrukcja edycji dokumentowały stare pole `recommendation_threshold` (single int). Administrator podmieniający normy wg tej instrukcji stworzyłby plik w legacy-formacie — który zostałby zaakceptowany przez migration fallback, ale cicho zignorowałby jego wartość i użył domyślnych progów (5/3/4/3). Nowy schemat używa `recommendation_rules` (obiekt z 4 progami). Pola `category_descriptions` i `observation_checklist` nie były udokumentowane w tabeli schematu.
- **Fix**: Zastąp wiersz `recommendation_threshold` opisem obiektu `recommendation_rules` (4 podpola). Dodaj wiersze dla `category_descriptions` i `observation_checklist`. Zaktualizuj instrukcję edycji w punkcie 2.
- **Decision**: FIXED

### F-02 — app/main.py:51 — unguarded float() na argumencie CLI

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/main.py:51
- **Detail**: `float(arg.split("=", 1)[1])` bez try/except. Flaga QA-only, ale crash przed GUI daje raw traceback zamiast komunikatu po polsku.
- **Fix**: Owiń try/except ValueError; złą wartość zignoruj lub wypisz na stderr.
- **Decision**: FIXED

### F-03 — app/main.py:65 — sys.argv zamiast argv przy --smoke-test

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/main.py:65
- **Detail**: Wszystkie flagi sprawdzane przez `argv = sys.argv[1:]`, tylko `--smoke-test` przez `sys.argv`. Działa, bo script path != "--smoke-test", ale niespójne i podatne na regresję przy refaktorze.
- **Fix**: Zmień `sys.argv` → `argv` na linii 65.
- **Decision**: FIXED

### F-04 — tests/unit/test_main_cli.py — legacy schema w happy-path fixture

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: tests/unit/test_main_cli.py:14–36
- **Detail**: `_valid_payload()` używa `recommendation_threshold` (legacy), podczas gdy `test_norms.py` używa `recommendation_rules`. Testuje ścieżkę migracji zamiast nowego schematu. Usunięcie migration fallback zrobi z tego false negative.
- **Fix**: Zaktualizuj `_valid_payload()` do `recommendation_rules` jak w test_norms.py.
- **Decision**: FIXED

### F-05 — tests/unit/test_main_cli.py — brak timeout w subprocess.run()

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: tests/unit/test_main_cli.py:43, 66
- **Detail**: Brak `timeout=` w obu `subprocess.run()`. Nieoczekiwana inicjalizacja GUI zawiesiłaby cały suite bez informacji o przyczynie.
- **Fix**: Dodaj `timeout=30` do obu wywołań.
- **Decision**: FIXED

### F-06 — app/domain/norms.py — Any bez wymaganego komentarza (AGENTS.md)

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/domain/norms.py:141, 158, 175, 201, 237
- **Detail**: 5 prywatnych funkcji ma `raw: Any` bez inline komentarza uzasadniającego (AGENTS.md wymaga uzasadnienia). `# type: ignore` na liniach 112/119 ma kod błędu ale nie opis.
- **Fix**: Dodaj `# Any: raw JSON value before structural validation` przy każdym `raw: Any`.
- **Decision**: FIXED

### F-07 — app/main.py:20–27 — root.destroy() nie w finally

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/main.py:20–27
- **Detail**: Jeśli `showerror()` rzuci wyjątek, `root.destroy()` nie jest wołane — minor resource leak.
- **Fix**: Owiń w try/finally: root.destroy().
- **Decision**: FIXED

### F-08 — norms.json.template — brak sekcji observation_checklist

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: norms.json.template
- **Detail**: Template nie pokazuje jak skonfigurować `observation_checklist`, mimo że norms.py go obsługuje.
- **Fix**: Dodaj przykładowy blok `observation_checklist` lub `_comment` z informacją o opcjonalności.
- **Decision**: FIXED

### F-09 — tests/unit/test_main_messages.py — brak edge-case coverage

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: tests/unit/test_main_messages.py
- **Detail**: Brak testu z NormsLoadError zawierającym znaki specjalne (%, \n, {}).
- **Fix**: Dodaj test z exception message zawierającym znaki specjalne.
- **Decision**: FIXED

### F-10 — app/domain/norms.py — _comment na poziomie band_ranges daje mylący błąd

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: app/domain/norms.py:141–155
- **Detail**: `_comment` jako bezpośredni klucz w band_ranges (nie wewnątrz obiektu pasma) zostanie potraktowany jako nazwa pasma i da mylący błąd. Template poprawnie tego unika, ale latentna pułapka.
- **Fix**: Dodaj notatkę w template że `_comment` na poziomie band_ranges nie jest obsługiwany.
- **Decision**: FIXED
