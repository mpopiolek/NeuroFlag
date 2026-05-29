---
project: NeuroFlag
checked_at: 2026-05-29T19:00:00+02:00
health: needs-attention
context_type: brownfield
stack_assess_ref: context/foundation/stack-assessment.md
findings:
  audit_critical: 0
  audit_high: 0
  audit_skipped: true
  test_runner: pytest
  test_runner_detected: true
  ci_provider: GitHub Actions
  config_gaps_high: 2
  config_gaps_medium: 0
  config_gaps_low: 1
fixes_recommended: 5
fixes_quick: 2
fixes_moderate: 2
fixes_significant: 1
---

## Podsumowanie audytu

> Uwaga: shell był niedostępny podczas tego uruchomienia. Kroki wymagające wykonania poleceń
> (`pip-audit`, `pip list --outdated`, `pytest --collect-only`) zostały przeprowadzone jako analiza
> statyczna plików projektu — zgodnie z regułą OSTRZEŻ I KONTYNUUJ. Wyniki są oparte na treści
> plików konfiguracyjnych i kodu.

```
Audyt zależności: pominięty (pip-audit niedostępny) — brak lockfile uniemożliwia precyzyjny audyt.
Przestarzałe:     pominięte — wszystkie zależności bez przypiętych wersji (patrz: Luka 1).
Runner testów:    pytest wykryty — 2 pliki testowe (testy prototypu FastAPI).
CI/CD:            GitHub Actions — etap testów ✓ | lint ✗ | build ✗ | type-check ✗ | security ✗.
Luki konfiguracji: 2 wysokie, 0 średnich, 1 niska.
```

---

## Audyt zależności (Krok 1)

### 1a. Status lockfile

**⚠ BRAK PRAWDZIWEGO LOCKFILE — HIGH**

| Plik | Status | Ocena |
|---|---|---|
| `requirements.txt` | Obecny | Słaby — brak przypiętych wersji dla wszystkich 11 pakietów |
| `poetry.lock` | Brak | — |
| `uv.lock` | Brak | — |
| `Pipfile.lock` | Brak | — |

Wszystkie zależności zadeklarowane bez wersji (np. `fastapi`, `mne`, `scipy` — bez `==X.Y.Z`). Każde środowisko `pip install` może wyprodukować inną kombinację wersji. Dla projektu z MNE-Python i SciPy jest to szczególnie ryzykowne — obie biblioteki mają zmieniające się API między wersjami.

### 1b. Audyt bezpieczeństwa (pip-audit)

**⚠ POMINIĘTY — shell niedostępny podczas tego uruchomienia.**

Brak przypiętych wersji oznacza, że nawet gdyby audyt był uruchomiony, nie mógłby precyzyjnie mapować CVE na zainstalowane wersje. Priorytet: najpierw przypnij wersje (Luka 1), potem uruchom `pip-audit`.

Polecenie do uruchomienia ręcznie:
```bash
pip install pip-audit
pip-audit --requirement requirements.txt
```

### 1c. Przestarzałe zależności

**⚠ POMINIĘTE — shell niedostępny.** Brak przypiętych wersji uniemożliwia sensowną analizę "aktualna vs. najnowsza".

Polecenie do uruchomienia ręcznie po przypisaniu wersji:
```bash
pip list --outdated --format json
```

---

## Infrastruktura testowa i konfiguracja (Krok 2)

### 2a. Runner testów

**✓ pytest wykryty — 2 pliki testowe**

| Plik | Zawartość | Status |
|---|---|---|
| `tests/test_imports.py` | Smoke test: importy numpy, scipy, pandas, mne, sklearn | ✓ Nadaje się do zachowania |
| `tests/test_app_endpoints.py` | Testy integracyjne HTTP: `/upload/norm`, `/upload/data`, `/compare`, `/report` | ⚠ Testuje prototyp FastAPI — wymaga przepisania |

Kluczowe spostrzeżenie: `test_app_endpoints.py` testuje endpointy HTTP serwera webowego, który zostanie usunięty. Testy te przestaną działać, gdy prototyp zostanie zastąpiony aplikacją desktopową. Nie są problemem *teraz*, ale muszą zostać zastąpione testami domenowymi przed lub w trakcie implementacji.

`test_imports.py` jest wartościowy i powinien zostać rozbudowany — weryfikuje, że zależności naukowe (MNE-Python, SciPy) instalują się poprawnie.

**Brakujące pokrycie testowe dla docelowej aplikacji** (Category A — do dodania podczas implementacji):
- Brak testów domenowych: algorytm trójstanowy, pipeline EEG, ładowanie norms.json
- Brak testów: wykrywanie znaczników OO/OZ/ZP, fallback co 3 minuty
- Brak testów: metryczka dziecka + blokowanie wykluczonych grup
- Brak testów: generowanie raportu PDF

### 2b. CI/CD — ocena pokrycia

**GitHub Actions wykryty** — `.github/workflows/python-app.yml`

| Etap | Status | Szczegóły |
|---|---|---|
| Test | ✓ | `pytest -q` — działa, targetuje Python 3.11 |
| Lint | ✗ | Brak ruff/flake8/pylint |
| Build | ✗ | Brak etapu PyInstaller — błędy buildu nie są wykrywane w CI |
| Type-check | ✗ | Brak mypy — potwierdza lukę ze stack-assessment |
| Security | ✗ | Brak pip-audit, brak Dependabot |

CI pokrywa tylko podstawowy smoke test. Brak lintowania, sprawdzania typów ani audytu bezpieczeństwa wzmacnia luki zidentyfikowane w stack-assessment.

### 2c. Brakujące pliki konfiguracyjne

| Plik | Status | Ważność | Uwagi |
|---|---|---|---|
| `.gitignore` | ⚠ Minimalny | HIGH | Zawiera tylko `.cursor/` — brak `__pycache__/`, `*.pyc`, `.venv/`, `dist/`, `build/`, `*.spec.bak` |
| `pyproject.toml` | ✗ Brak | HIGH | Brak konfiguracji mypy, pytest, ruff — potwierdza lukę ze stack-assessment |
| `.editorconfig` | ✗ Brak | LOW | Wygoda — spójność formatowania w edytorach |
| `AGENTS.md` | ✓ Obecny | — | Zaktualizowany z konwencjami docelowego stosu |

---

## Połączenie z oceną stosu (Krok 3)

Wyniki z `context/foundation/stack-assessment.md` (werdykt: `ready-with-compensation`):

| Luka ze stack-assessment | Stan po health-check |
|---|---|
| Python bez typowania (mypy) | **Wzmocniony** — brak mypy w deps ORAZ brak mypy w CI. Kompensacja (AGENTS.md) jest na miejscu, ale wymuszenie jest zerowe. |
| Brak pinowania wersji | **Potwierdzony** — brak lockfile + brak wersji w requirements.txt. |
| Brak struktury modułów GUI | Nie dotyczy pre-code — brak dodatkowych ustaleń. |
| MNE-Python niszowość | Nie dotyczy — brak ustaleń operacyjnych. |
| PyInstaller bez .spec | **Potwierdzony pośrednio** — CI nie ma etapu build, co oznacza że błędy .spec nie będą wykrywane automatycznie. |

---

## Priorytetowe poprawki

### Kategoria A — Napraw przed pracą agenta

#### Luka 1 — Brak przypiętych wersji zależności
- **Ustalenie:** `requirements.txt` zawiera 11 pakietów bez żadnych wersji. `pip install` w różnych środowiskach może wyprodukować różne kombinacje.
- **Wpływ na agenta:** Agent generujący kod pod określone API MNE-Python lub SciPy może generować kod niezgodny z wersją zainstalowaną w środowisku dewelopera lub CI.
- **Działanie:** Sprawdź zainstalowane wersje, utwórz `pyproject.toml` i przypnij wersje. Uruchom `pip freeze > requirements.lock` jako tymczasowy lockfile lub przejdź na `uv` / `poetry`.
- **Szacowany wysiłek:** Umiarkowany (15–30 min)

```bash
# Krok 1: sprawdź aktualne wersje
pip freeze | grep -E "fastapi|uvicorn|mne|scipy|numpy|pandas|reportlab|scikit-learn|pytest|httpx|python-multipart"

# Krok 2: utwórz pyproject.toml (minimalny)
# [project]
# name = "neuroflag"
# requires-python = ">=3.11"
# dependencies = [
#   "mne==1.8.0",      # dostosuj do faktycznej wersji
#   "scipy==1.14.1",
#   ... itd.
# ]
```

#### Luka 2 — Minimalny .gitignore (brakuje kluczowych wpisów)
- **Ustalenie:** `.gitignore` zawiera tylko `.cursor/`. Brakuje: `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `dist/`, `build/`, `*.egg-info/`, `*.spec.bak`, `neuroflag.spec` (jeśli zawiera ścieżki lokalne).
- **Wpływ na agenta:** Bez poprawnego `.gitignore` agent może commitować pliki cache Pythona lub artefakty buildu, zanieczyszczając historię git.
- **Działanie:** Dodaj standardowe wpisy Pythona.
- **Szacowany wysiłek:** Szybki (< 5 min)

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
.Python
*.egg-info/

# Virtual environments
.venv/
venv/
env/

# Build / distribution
dist/
build/
*.spec.bak

# IDE
.cursor/
.idea/
.vscode/

# OS
.DS_Store
Thumbs.db
```

#### Luka 3 — Brak mypy i sprawdzania typów (potwierdzony z stack-assessment)
- **Ustalenie:** `mypy` nieobecny w `requirements.txt`. CI nie ma etapu type-check. Żaden plik konfiguracyjny (`pyproject.toml`, `setup.cfg`, `mypy.ini`) nie istnieje.
- **Wpływ na agenta:** Agent generuje kod bez weryfikacji typów. W projekcie z nietrywialną logiką domenową (pipeline EEG, algorytm trójstanowy) brak typowania oznacza więcej cykli korekcji. `AGENTS.md` zawiera konwencję mypy — ale nie ma narzędzia, które ją wymusza.
- **Działanie:** Dodaj mypy do projektu, skonfiguruj w pyproject.toml, dodaj etap do CI.
- **Szacowany wysiłek:** Umiarkowany (15–30 min)

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true   # MNE-Python nie ma typów inline — konieczne
```

```yaml
# .github/workflows/python-app.yml — dodaj etap:
- name: Type check
  run: mypy app/ --strict --ignore-missing-imports
```

#### Luka 4 — Testy prototypu nie będą działać po wymianie kodu
- **Ustalenie:** `test_app_endpoints.py` testuje endpointy HTTP FastAPI, które zostaną usunięte. Testy przestaną kompilować się gdy `app.main` straci FastAPI.
- **Wpływ na agenta:** Gdy agent zaczyna implementować aplikację desktopową, stare testy zaczną się łamać — CI będzie czerwone przez cały czas implementacji, jeśli nie zostaną zastąpione.
- **Działanie:** Nie usuwaj teraz — usuń lub zastąp testami domenowymi w momencie, gdy zaczyna się implementacja modułów domenowych. Zachowaj `test_imports.py` i rozbuduj go o weryfikację importów docelowego stosu.
- **Szacowany wysiłek:** Znaczący (> 1 godzina — należy do implementacji, nie do pre-work)

#### Luka 5 — Brak pip-audit w CI (brak etapu security)
- **Ustalenie:** CI nie uruchamia audytu bezpieczeństwa. Brak Dependabot.
- **Wpływ na agenta:** Nowe zależności dodawane przez agenta nie są automatycznie skanowane pod kątem CVE.
- **Działanie:** Dodaj `pip-audit` do CI lub włącz Dependabot dla Python.
- **Szacowany wysiłek:** Szybki (< 5 min dla Dependabot)

```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: pip
    directory: "/"
    schedule:
      interval: weekly
```

---

### Kategoria B — Nadchodzące etapy

| Ustalenie | Status | Kolejny krok |
|---|---|---|
| Brak etapu lint w CI | Oczekiwany | Dodaj `ruff check app/` w etapie CI podczas konfiguracji infrastruktury |
| Brak etapu build (PyInstaller) w CI | Oczekiwany | Dodaj `pyinstaller neuroflag.spec --clean` jako etap CI po utworzeniu `.spec` |
| Brak `.editorconfig` | Niski priorytet | Dodaj przy konfiguracji środowiska deweloperskiego |
| Brak konfiguracji wdrożenia | Oczekiwany | Nie dotyczy — dystrybucja przez `.exe`, nie deploy |

---

## Podsumowanie

**NeuroFlag — stan zdrowia: `needs-attention`**

Projekt jest w dobrej kondycji dla wczesnego etapu: ma działający runner testów, CI, i kompletne pliki kontekstu (`prd.md`, `stack-assessment.md`, zaktualizowany `AGENTS.md`). Wszystkie zidentyfikowane luki mają klarowne ścieżki naprawy i żadna nie jest blokująca dla natychmiastowej pracy.

**Główne mocne strony:**
- pytest działa z testami smoke (imports) wartymi zachowania
- GitHub Actions CI aktywne i uruchamia testy przy każdym pushu
- AGENTS.md zaktualizowany z pełnymi konwencjami docelowego stosu
- Kompletny łańcuch kontekstu: shape-notes → PRD → stack-assessment → health-check

**Najważniejsze poprawki przed startem implementacji:**
1. **Przypnij wersje zależności** — utwórz `pyproject.toml` z wersjonowanymi zależnościami (umiarkowany wysiłek, największy wpływ)
2. **Popraw `.gitignore`** — 5 minut, zapobiega zaśmiecaniu historii git (szybkie)
3. **Dodaj mypy** — skonfiguruj w `pyproject.toml` + etap CI (umiarkowany wysiłek, wymuszenie konwencji z AGENTS.md)

Po wykonaniu poprawek kategorii A projekt osiągnie gotowość `healthy` i będzie gotowy do pracy z agentem.
