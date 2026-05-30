# Project Foundation — Plan Brief

> Full plan: `context/changes/project-foundation/plan.md`

## What & Why

F-01 buduje fundament aplikacji desktopowej NeuroFlag: usuwa prototyp FastAPI, tworzy typy domenowe będące kontraktem całego projektu, loader norm z walidacją schematu i obsługą PyInstaller, oraz stub wejścia CTk z obsługą `--smoke-test`. Bez stabilnych typów domenowych i loadera norm żaden kolejny moduł (UI, pipeline EEG, PDF) nie może ruszyć z implementacją.

## Starting Point

`pyproject.toml` z przypiętymi zależnościami i `norms.json` z 10 normami są już gotowe. `app/main.py` to prototyp FastAPI (~120 linii, bez typów, bez logiki domenowej). Brak `app/domain/`, brak `app/ui/`. Testy są powiązane z FastAPI i importują prod-nieobecne zależności (pandas, sklearn).

## Desired End State

`app/domain/types.py` zawiera kompletne, `frozen=True` dataclassy (`PatientMetadata`, `CellResult`, `AnalysisResult`, `NormsConfig`) i Enum-y (`ExclusionDiagnosis`, `CellColor`, `ScreeningCategory`). `app/domain/norms.py` wczytuje `norms.json` i rzuca `NormsLoadError` dla każdego naruszenia schematu. `app/main.py` to czysty stub CTk z `--smoke-test`. CI (mypy --strict, ruff, pytest) przechodzi w całości.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) |
| --- | --- | --- |
| Kształt `AnalysisResult` | 10 `CellResult` + `category` + `description` + `analyzed_at` | Zamknięty kontrakt od razu — S-02 wypełnia, UI i PDF zużywają bez dodatkowego mapowania. |
| Walidacja norm | `NormsLoadError` (własny wyjątek) łapany przez `main.py` | S-01 może złapać ten sam wyjątek i wyświetlić MessageBox zamiast crashu. |
| `PatientMetadata.exclusions` | `frozenset[ExclusionDiagnosis]` + `is_excluded()` | Rozszerzalny bez zmiany sygnatury (v2.0 dodaje nowe wartości Enum). |
| `app/main.py` stub | CTk z `--smoke-test` + `norms.load()` | `--smoke-test` musi działać w CI (Windows build); CTk inicjalizowany tu = S-01 dopisuje widoki. |
| Zakres testów | Typy + norms.py + wszystkie ścieżki `NormsLoadError` | Walidacja jest kontraktem S-04 (podmiana norm) — testy błędów chronią ten kontrakt od razu. |
| Stare testy | `test_app_endpoints.py` usunięty; `test_imports.py` → `test_deps.py` (prod deps tylko) | Zachowujemy dymny import MNE/NumPy/SciPy bez fastapi/pandas/sklearn. |
| Ścieżka `norms.json` | `resolve_norms_path()` z `sys._MEIPASS` fallback | Windows CI build (`neuroflag.exe --smoke-test`) działa od razu po F-01. |

## Scope

**In scope:**
- `app/domain/__init__.py` + `app/domain/types.py` (typy domenowe)
- `app/domain/norms.py` (loader + `NormsLoadError` + `resolve_norms_path()`)
- `app/main.py` — zastąpienie FastAPI stubem CTk + `--smoke-test`
- `tests/unit/test_deps.py`, `tests/unit/test_types.py`, `tests/unit/test_norms.py`
- Usunięcie `tests/test_app_endpoints.py` i `tests/test_imports.py`

**Out of scope:**
- Żadne widoki UI (`app/ui/`) — S-01
- Pipeline EEG, algorytm trójstanowy — S-02
- Raport PDF — S-03
- Podmiana norm przez UI — S-04
- Modyfikacje `norms.json`, `pyproject.toml`, `neuroflag.spec`, CI

## Architecture / Approach

Nowy kod w `app/domain/` (typy, loader) zgodnie z architekturą AGENTS.md. Kolejność: `types.py` (kontrakt) → `norms.py` (korzysta z typów) → `main.py` (korzysta z obu). `frozen=True` dataclassy zapobiegają mutacji między warstwami. `NormsLoadError` to jedyny publiczny wyjątek domenowy z F-01; reszta modułów łapie go na granicy UI.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| --- | --- | --- |
| 1. Typy domenowe | Stabilny kontrakt: `PatientMetadata`, `CellResult`, `AnalysisResult`, `NormsConfig` | Zmiana sygnatury po starcie S-01/S-02 = fala poprawek |
| 2. Loader norm | `norms.load()` + `NormsLoadError` + PyInstaller path resolution | `sys._MEIPASS` fallback musi działać zarówno w dev jak i w `.exe` |
| 3. Desktop stub | `app/main.py` bez FastAPI, `--smoke-test` działa, CTk placeholder | CTk nie może być inicjalizowany przed sprawdzeniem `--smoke-test` (headless CI) |
| 4. Testy i porządki | `pytest -q` + `mypy --strict` + `ruff` — wszystkie green; stare testy usunięte | Brak `tests/unit/__init__.py` może złamać discovery pytest |

**Prerequisites:** `pyproject.toml` z przypiętymi deps (gotowe), `norms.json` (gotowy), `neuroflag.spec` (gotowy)
**Estimated effort:** ~1 sesja, 4 fazy sekwencyjne

## Open Risks & Assumptions

- `customtkinter.CTk()` w `--smoke-test` na headless Ubuntu CI może wymagać Xvfb lub mock — obsłużone przez wyjście PRZED `ctk.CTk()` w stub
- `mypy --strict` może ujawnić błędy w istniejącym `app/main.py` przy analizie całego katalogu; stary main.py jest zastępowany więc ryzyko zerowe po fazie 3
- Zakresy pasm (Beta1: 15–18 Hz, Beta2: 18–25 Hz) są potwierdzone przez eksperta domenowego (2026-05-30) — `norms.json` już je zawiera

## Success Criteria (Summary)

- `pytest -q` + `mypy app/ --strict` + `ruff check app/` — wszystkie green na Ubuntu CI
- `python app/main.py --smoke-test` → exit code 0 (weryfikuje ładowanie norm + stub wejścia)
- `from app.domain.types import PatientMetadata, AnalysisResult, NormsConfig` działa bez błędu
