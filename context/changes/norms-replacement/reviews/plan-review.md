<!-- PLAN-REVIEW-REPORT -->
# Plan Review: S-04 — Wymiana bazy norm

- **Plan**: `context/changes/norms-replacement/plan.md`
- **Mode**: Deep
- **Date**: 2026-06-01
- **Verdict**: SOUND (after triage fixes)
- **Findings**: 1 critical, 3 warnings, 2 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | FAIL |
| Lean Execution | WARNING |
| Architectural Fitness | PASS |
| Blind Spots | WARNING |
| Plan Completeness | WARNING |

## Grounding

Grounding: 5/5 paths ✓ (`app/main.py`, `app/domain/norms.py`, `tests/unit/test_norms.py`, `norms.json`, `neuroflag.spec`), 3/3 symbols ✓ (`NormsLoadError`, `_TOP_LEVEL_KEYS`, `--smoke-test`), brief↔plan ✓. New files to create (`test_main_cli.py`, `norms.json.template`, `docs/README-norms.md`) correctly absent pre-implementation.

## Findings

### F1 — Podmiana norms.json obok .exe nie zadziała

- **Severity**: ❌ CRITICAL
- **Impact**: 🔬 HIGH — architectural stakes; think carefully before deciding
- **Dimension**: End-State Alignment
- **Location**: Current State Analysis; Phase 2 README; „What We're NOT Doing"
- **Detail**: Plan zakłada, że administrator podmienia `dist/neuroflag/norms.json` obok `neuroflag.exe` (`distribution.md:25`, `distribution.md:82`, plan Phase 2). Tymczasem `resolve_norms_path()` (`app/domain/norms.py:39-41`) w trybie PyInstaller zwraca `Path(sys._MEIPASS) / "norms.json"` — w PyInstaller 6 onedir to `dist/neuroflag/_internal/norms.json`, nie katalog obok `.exe`. Plik obok `.exe` jest ignorowany; podmiana zgodnie z dokumentacją nie zmieni norm używanych przez aplikację. Cały cel FR-008/S-04 jest zagrożony mimo poprawnej walidacji i dialogu błędu.
- **Fix A ⭐ Recommended**: Rozszerzyć S-04 o fazę (lub wpis w Phase 1) modyfikującą `resolve_norms_path()`: gdy `getattr(sys, "frozen", False)` — preferuj `Path(sys.executable).parent / "norms.json"` jeśli plik istnieje; fallback na `_MEIPASS/norms.json`. Dodać test w `test_norms.py` z mockiem `sys.frozen`/`sys.executable`. Zaktualizować `neuroflag.spec` lub krok CI build tak, by domyślny `norms.json` lądował obok `.exe` (np. post-build copy). Usunąć z „What We're NOT Doing" wpis o braku zmian w `norms.py`.
  - Strength: Zgodne z `distribution.md`, PRD FR-008 i Desired End State S-04; podmiana bez rebuildu działa naprawdę.
  - Tradeoff: Dotyka loadera z F-01; wymaga testu PyInstaller path + ewentualnie kroku build.
  - Confidence: HIGH — kod i dokumentacja dystrybucji są sprzeczne; `_MEIPASS`-only to znany antywzorzec dla plików nadpisywalnych.
  - Blind spot: Dokładna lokalizacja `datas` w PyInstaller 6 warto potwierdzić jednym buildem lokalnym.
- **Fix B**: Udokumentować podmianę w `_internal/norms.json`
  - Strength: Zero zmian w kodzie.
  - Tradeoff: Sprzeczne z `distribution.md`, ukryte dla administratora, ryzyko uszkodzenia bundla przy edycji `_internal/`.
  - Confidence: LOW — odrzuca wymaganie produktowe.
  - Blind spot: Brak.
- **Decision**: FIXED via Fix A — exe-dir-first `resolve_norms_path()`; formularz UI → osobny slice po S-01

### F2 — Artefakty docs nie trafią do dystrybucji

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Blind Spots
- **Location**: Phase 2; Desired End State #3–4
- **Detail**: Plan tworzy `norms.json.template` i `docs/README-norms.md` w repozytorium, ale nie wspomina `neuroflag.spec:64-66` (`datas`). Bez bundlingu placówka dostaje tylko `.exe` + `_internal/` — szablon i instrukcja nie będą obok aplikacji, mimo że error dialog (`plan.md:137`) odsyła do `norms.json.template`.
- **Fix**: Dodać do Phase 2 wpis w `neuroflag.spec` `datas`: `(norms.json.template, ".")` i `(docs/README-norms.md, "docs")`; zaktualizować `distribution.md` o te pliki w artefakcie. Dodać do Progress automated check: pliki istnieją w `dist/neuroflag/` po buildzie.
  - Strength: Administrator ma template i README tam, gdzie pracuje — zgodne z error dialog i FR-008.
  - Tradeoff: Wymaga rebuildu `.exe` i aktualizacji smoke-test checklist.
  - Confidence: HIGH — obecny spec bundluje tylko `norms.json`.
  - Blind spot: Rozmiar dist/ — marginalny.
- **Decision**: FIXED — dodano bundling w `neuroflag.spec` Phase 2

### F3 — Sprzeczność: „norms.py bez zmian" vs podmiana użytkownika

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Lean Execution
- **Location**: What We're NOT Doing; Implementation Approach
- **Detail**: Plan trzy razy stwierdza, że `norms.py` nie wymaga zmian, podczas gdy bez poprawki `resolve_norms_path()` podmiana norm jest iluzoryczna (F1). Implementer traktujący „What We're NOT Doing" dosłownie dostarczy dialog i CLI, ale nie spełni FR-008.
- **Fix**: Usunąć „Zmian w norms.py" z out-of-scope; dodać Phase 1 (lub podfazę) z intentem „exe-dir-first path resolution" w `app/domain/norms.py` + test jednostkowy.
- **Decision**: FIXED — Phase 1 rozszerzona o `resolve_norms_path()`

### F4 — `_comment` w `band_ranges` może złamać walidację

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 2 — norms.json.template Contract
- **Detail**: Plan mówi o `"_comment"` „przy każdym polu band_ranges". `_parse_band_ranges()` (`norms.py:48-53`) iteruje **wszystkie** klucze w `band_ranges` — klucz `"_comment"` jako string (nie obiekt z `l_freq`/`h_freq`) rzuci `NormsLoadError`. Bezpieczne są tylko: `_comment` na root OR `_comment` **wewnątrz** obiektów pasma (np. `Delta._comment`), nie jako sibling `Delta`/`Theta`.
- **Fix**: W Contract Phase 2 doprecyzować: `_comment` dozwolony wyłącznie na root i wewnątrz każdego wpisu pasma (`Delta`, `Theta`, …); **zakaz** `_comment` jako bezpośredniego klucza w `band_ranges`. Dodać przykład JSON w planie.
- **Decision**: FIXED — Contract Phase 2 doprecyzowany

### F5 — `mypy app/ --strict` w Desired End State bez Progress item

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Desired End State #5; Progress Phase 1
- **Detail**: Desired End State obiecuje `mypy app/ --strict`, Progress Phase 1 sprawdza tylko `mypy app/main.py`. Po S-04 (bez nowych modułów poza testami) regresja mało prawdopodobna, ale promise gap istnieje.
- **Fix**: Dodać Progress item `1.x mypy app/ --strict — 0 błędów` lub zawęzić Desired End State do `mypy app/main.py`.
- **Decision**: FIXED — Progress 1.1 `mypy app/ --strict`

### F6 — Dialog błędu GUI bez testu automatycznego

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 1 Manual Verification
- **Detail**: `_show_norms_error()` woła `tkinter.Tk()` — nie da się łatwo przetestować w headless CI. Plan polega na manual verification; akceptowalne dla MVP, ale regresja (np. import przed withdraw) nie zostanie złapana.
- **Fix**: Opcjonalnie wyekstrahować logikę do funkcji testowalnej bez GUI (`_format_norms_error_message`) + test jednostkowy treści komunikatu; messagebox zostaje manual.
- **Decision**: FIXED — `format_norms_error_message()` + `test_main_messages.py`
