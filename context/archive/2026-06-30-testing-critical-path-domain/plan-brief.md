# Testing Critical Path Domain — Plan Brief

> Pełny plan: `context/changes/testing-critical-path-domain/plan.md`
> Research: `context/changes/testing-critical-path-domain/research.md`

## What & Why

Faza 1 planu testowego NeuroFlag: zamknięcie dwóch wysokich ryzyk domenowych. R1 — istniejące testy algorytmu trójstanowego używają syntetycznych progów (`mean_z=10.0`), więc regresja przy prawdziwych wartościach (np. `mean_z=30.35 µV` dla C3/OZ/Theta) jest niewidoczna. R3 — walidacja schematu `norms.json` ma kilka niepokrytych wariantów błędów, w tym jeden gdzie sama produkcja nie rzuca błędu (`l_freq > h_freq` w zakresie pasma).

## Starting Point

113 testów jednostkowych w `tests/unit/`, brak `tests/conftest.py`, brak `tests/integration/`. `test_algorithm.py` testuje `_cell_color()` wyłącznie z mockami; jedyny test z realnym `norms.json` sprawdza tylko `amplitude=0.0`. `test_norms.py` pokrywa kilka error paths, ale nie wszystkie warianty błędów schematu.

## Desired End State

Po ukończeniu: 3 nowe pliki testowe (`tests/conftest.py`, `tests/unit/test_algorithm_real_norms.py`, `tests/unit/test_norms_validation.py`) dodają 48 nowych przypadków testowych. Regresja w logice granicy progów per normę jest natychmiast widoczna z nazwy testu (np. `norm7_O1_OZ_Theta`). Każdy z 6 wybranych wariantów błędnego `norms.json` ma własny named test. `python -m pytest -q` przechodzi bez błędów.

## Key Decisions Made

| Decyzja | Wybór | Uzasadnienie (1 zdanie) | Źródło |
|---|---|---|---|
| Granulacja testów granicznych R1 | ±2ε od realnych progów per norma | Precyzyjny sygnał: wiadomo która norma pada przy regresji | Plan |
| Gdzie testy algorytmu | Nowy plik `test_algorithm_real_norms.py` | Czytelny podział syntetyczne/realne normy | Plan |
| Fixture `real_norms_config` | `tests/conftest.py` (session scope) | Jeden load() na całą sesję, dostępna dla przyszłych faz | Plan |
| Testy walidacji R3 | Nowy plik `test_norms_validation.py` | Izolowany plik error paths vs happy paths w `test_norms.py` | Plan |
| Warianty błędów R3 | 6 niepokrytych: `{}`, wrong type, brak `band_ranges`, brak `version`, `l_freq>h_freq`, `mean_z≥mean_k` | Pokrywają luki względem istniejących 18 testów w `test_norms.py` | Plan |
| Walidacja `l_freq < h_freq` | Dodać do `_parse_band_ranges` | Brama nie istnieje w produkcji — test zmotywuje poprawkę | Research / Plan |

## Scope

**W zakresie:**
- `tests/conftest.py` — fixture `real_norms_config`
- `tests/unit/test_algorithm_real_norms.py` — 40 testów granicznych `_cell_color()` + 2 zbiorcze `classify()`
- `tests/unit/test_norms_validation.py` — 6 parametryzowanych wariantów błędów `norms.load()`
- Poprawka produkcyjna w `app/domain/norms.py` (dodanie walidacji `l_freq < h_freq`)

**Poza zakresem:**
- Testy integracyjne (Faza 2 test-planu: fidelity sygnału pipeline)
- DigiTrack, pipeline, fallback segmentów (Faza 2)
- Testy UI, PDF, CLI
- Powielanie istniejących testów: `test_missing_norms_key`, `test_too_few_norms`, `test_norm_entry_missing_mean_z` i pozostałe 18 w `test_norms.py`

## Architecture / Approach

Wyłącznie testy jednostkowe — brak MNE, brak IO poza `norms.json`. `conftest.py` ładuje `norms.json` raz (scope=session). `test_algorithm_real_norms.py` używa modułowego `_REAL_CONFIG = load(...)` dla `@pytest.mark.parametrize` i fixture session dla testów `classify()`. `test_norms_validation.py` wykorzystuje `tmp_path` fixture pytest do zapisu mutowanych payloadów; waliduje każdy wariant jako `pytest.raises(NormsLoadError, match=...)`.

## Phases at a Glance

| Faza | Co dostarcza | Kluczowe ryzyko |
|---|---|---|
| 1. Shared Fixture + R1 Boundary Tests | `conftest.py` + `test_algorithm_real_norms.py` — 42 testy graniczne algorytmu z realnymi normami | Testy powinny być szybkie (brak MNE) — weryfikować po napisaniu |
| 2. R3 Validation Gap Tests | `test_norms_validation.py` + poprawka `l_freq < h_freq` w `_parse_band_ranges` | Test `invalid_band_range` nie przejdzie bez poprawki produkcyjnej |

**Wymagania wstępne:** `norms.json` w root projektu (istnieje), pytest skonfigurowany (`testpaths = ["tests"]`), `app.domain.algorithm._EPSILON` importowalny (potwierdzone).
**Szacowany nakład:** ~1 sesja, 3 nowe pliki (~150 linii kodu testowego łącznie) + ~4 linie poprawki produkcyjnej.

## Open Risks & Assumptions

- Jeśli `_EPSILON` zmieni wartość w kodzie produkcyjnym, testy ±2ε automatycznie dostosują się — ale warto zadbać by testowy import był z `app.domain.algorithm`, nie lokalna definicja
- `l_freq > h_freq` test wymaga poprawki w `norms.py` przed zdaniem — jeśli implementer uruchomi suite bez tej poprawki, Phase 2 będzie wykazywać 1 failure (spodziewane, udokumentowane w planie)
- Fixture session scope zakłada niezmienność `norms.json` podczas sesji pytest — safe dla lokalnych uruchomień i CI

## Success Criteria (Summary)

- `python -m pytest -q` przechodzi z zerowymi failures po obu fazach
- Raport `-v` zawiera czytelne identyfikatory parametrów (np. `norm1_C3_OZ_Theta`, `[empty_json]`)
- `mypy app/ --strict` przechodzi bez nowych błędów
