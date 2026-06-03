<!-- PLAN-REVIEW-REPORT -->
# Plan Review: S-04 — Wymiana bazy norm

- **Plan**: `context/changes/norms-replacement/plan.md`
- **Mode**: Deep (post-implementation refresh)
- **Date**: 2026-06-03
- **Verdict**: SOUND (after triage fixes 2026-06-03)
- **Findings**: 0 critical, 2 warnings, 3 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | PASS |
| Lean Execution | PASS |
| Architectural Fitness | PASS |
| Blind Spots | PASS |
| Plan Completeness | PASS |

## Grounding

Grounding: 7/7 paths ✓ (`app/main.py`, `app/domain/norms.py`, `tests/unit/test_norms.py`, `norms.json`, `neuroflag.spec`, `norms.json.template`, `docs/README-norms.md`), 3/3 symbols ✓ (`NormsLoadError`, `resolve_norms_path`, `--validate-norms`), brief↔plan ✓. Implementacja Phase 1–2 w kodzie jest zgodna z planem po triage z 2026-06-01.

## Findings

### F1 — Progress 2.3 bez enforcement w CI

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Blind Spots
- **Location**: Phase 2 Automated Verification (2.3); `.github/workflows/python-app.yml`
- **Detail**: Plan wymaga, by po buildzie PyInstaller istniały `dist/neuroflag/norms.json.template` i `dist/neuroflag/docs/README-norms.md`. CI buduje `.exe` (job `build`, linie 82–84) i uruchamia tylko `--smoke-test` (86–88), bez sprawdzenia obecności artefaktów docs. Regresja w `neuroflag.spec` (np. usunięcie wpisu z `datas`) nie zostanie złapana automatycznie; implementer musi ręcznie domknąć 2.3.
- **Fix**: Dodać krok CI po `pyinstaller`: `Test-Path dist\neuroflag\norms.json.template` oraz `Test-Path dist\neuroflag\docs\README-norms.md` (fail build jeśli brak). Opcjonalnie dopisać ten krok do planu Phase 2 jako „CI contract”.
  - Strength: Zamknięcie luki między planem a pipeline; zgodne z triage F2 z poprzedniego review.
  - Tradeoff: Build Windows musi przejść na gałęzi z aktualnym spec — już i tak jest gate na `main`.
  - Confidence: HIGH — workflow czytany linia po linii; brak assertów na dist.
  - Blind spot: Dokładna ścieżka w PyInstaller 6 onedir — patrz F2.
- **Decision**: FIXED — dodano krok CI `Verify and publish dist docs beside .exe` w `.github/workflows/python-app.yml` + wpis CI contract w planie Phase 2

- **Severity**: ⚠️ WARNING
- **Impact**: 🔬 HIGH — architectural stakes; think carefully before deciding
- **Dimension**: Blind Spots
- **Location**: Phase 2 bundling; `distribution.md`; error dialog (`norms.json.template`)
- **Detail**: Plan, README i `format_norms_error_message()` zakładają, że `norms.json.template` leży obok `neuroflag.exe`. `neuroflag.spec` bundluje template z dest `"."`, ale PyInstaller 6 onedir często umieszcza `datas` w `_internal/` (obok bibliotek), nie w root folderze dystrybucji. `resolve_norms_path()` ma exe-dir-first dla `norms.json` (podmiana działa), lecz template/README mogą być niewidoczne dla administratora tam, gdzie wskazuje instrukcja. Progress 2.3 jest `[ ]` — luka nie jest jeszcze zamknięta jednym buildem.
- **Fix A ⭐ Recommended**: Po buildzie zweryfikować faktyczne ścieżki w `dist/neuroflag/`; jeśli template ląduje w `_internal/`, dodać post-build copy (PowerShell w CI) do root obok `.exe` ALBO zaktualizować `docs/README-norms.md` i komunikat błędu do realnej ścieżki. Dopisać w planie Phase 2 jawny krok weryfikacji layoutu.
  - Strength: Dokumentacja i artefakty zgodne z rzeczywistością dystrybucji; administrator znajdzie pliki.
  - Tradeoff: Post-build copy = dodatkowy krok w CI/spec; aktualizacja docs = mniej wygodna podmiana.
  - Confidence: MED — zachowanie PyInstaller 6 wymaga potwierdzenia jednym lokalnym/CI buildem (2.3).
  - Blind spot: Wersja PyInstaller w `[dev]` extras nie była w tej sesji uruchomiona lokalnie.
- **Fix B**: Zaakceptować lokalizację w `_internal/` i wskazać w README pełną ścieżkę `_internal/norms.json.template`
  - Strength: Zero zmian w buildzie.
  - Tradeoff: Sprzeczne z obecnym `distribution.md` i komunikatem error dialog; gorsze UX dla administratora.
  - Confidence: LOW — odrzuca intencję produktową FR-008.
  - Blind spot: Brak.
- **Decision**: FIXED via Fix A — CI kopiuje z `_internal/` do root obok `.exe` gdy trzeba; plan Phase 2 uzupełniony

### F3 — „Current State Analysis” opisuje stan sprzed implementacji

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Current State Analysis; Key Discoveries (linie 29–41 planu)
- **Detail**: Sekcja nadal opisuje `resolve_norms_path()` jako `_MEIPASS`-only i `sys.exit()` jako jedyny gap — to było prawdą przed S-04, ale Phase 1 już to adresuje, a kod jest zaimplementowany. Może mylić czytelników planu i agenta przy `/10x-archive`.
- **Fix**: Dodać nagłówek „Stan przed implementacją S-04 (historyczny)” lub zaktualizować bullet na „było: _MEIPASS-only; Phase 1: exe-dir-first”.
- **Decision**: FIXED — nagłówek historyczny w plan.md Current State Analysis

### F4 — Brak testu end-to-end `load()` z exe-dir vs `_MEIPASS`

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 1 test path resolution
- **Detail**: Testy mockują `resolve_norms_path()` w izolacji; brak testu, że `load()` wczytuje **inną treść** z pliku obok `.exe` niż z bundla `_MEIPASS` gdy oba istnieją. Regresja w `load()` (ignorowanie `resolve_norms_path()`) nie zostałaby złapana.
- **Fix**: Opcjonalny test integracyjny: dwa różne JSON-y w exe-dir vs meipass, `load()` bez `path=` zwraca wartość z exe-dir.
- **Decision**: FIXED — `test_load_prefers_exe_dir_norms_when_frozen` w `test_norms.py`

### F5 — Dialog GUI nadal tylko manual (akceptowane)

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Blind Spots
- **Location**: Phase 1 Manual Verification
- **Detail**: `_show_norms_error()` woła `tkinter.Tk()` — bez testu automatycznego (plan świadomie polega na manual + `format_norms_error_message()` w `test_main_messages.py`). Zgodne z triage F6 z 2026-06-01.
- **Fix**: Brak wymaganej zmiany planu; utrzymać w manual checklist przy archiwizacji.
- **Decision**: ACCEPTED — manual wystarczy dla MVP

| Plan item | Status w kodzie |
|-----------|-----------------|
| exe-dir-first `resolve_norms_path()` | ✅ `norms.py:39-46` + 2 testy |
| `--validate-norms` CLI | ✅ `main.py:47-52` + 4 testy subprocess |
| `format_norms_error_message()` | ✅ + `test_main_messages.py` |
| `norms.json.template` + README | ✅ pliki istnieją, `--validate-norms template` OK |
| `neuroflag.spec` datas | ✅ wpisy dodane |
| Progress manual 1.8–1.10, 2.5–2.6 | ⏳ oczekuje potwierdzenia użytkownika |
| Progress 2.3 PyInstaller dist | ⏳ niezweryfikowane (brak PyInstaller lokalnie / brak assertu CI) |

## Triage z poprzedniego review (2026-06-01)

Wszystkie F1–F6 z pierwszego review oznaczone FIXED w planie — implementacja potwierdza poprawki (path resolution, bundling w spec, `_comment` contract, testy CLI/messages).
