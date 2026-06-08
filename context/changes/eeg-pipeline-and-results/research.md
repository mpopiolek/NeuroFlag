---
date: 2026-06-08T20:20:00+02:00
researcher: agent
git_commit: n/a (shell unavailable)
branch: main
repository: NeuroFlag
topic: "S-02 Faza 2 — algorytm klasyfikacji: kontrakty, luki, wzorce"
tags: [research, algorithm, classification, norms, types, ui-wiring]
status: complete
last_updated: 2026-06-08
last_updated_by: agent
---

# Research: S-02 Faza 2 — Algorytm klasyfikacji

**Date**: 2026-06-08T20:20+02:00  
**Researcher**: agent  
**Repository**: NeuroFlag

## Research Question

Jakie dokładnie kontrakty, luki i wzorce trzeba znać przed implementacją S-02 Fazy 2
(algorytm klasyfikacji + rozszerzenie norms.json)?

## Summary

Faza 2 tworzy trzy nowe artefakty (`algorithm.py`, rozszerzony `norms.json`,
rozszerzone `types.py` + `norms.py`) i testy. Luki w istniejącym kodzie są dobrze
zlokalizowane: `NormsConfig` nie ma jeszcze pól `recommendation_rules` /
`category_descriptions`, `AppState` nie ma `norms_config`, a `main.py` nie przekazuje
`_config` do `AppWindow`. Wzorzec testów jest jednorodny (moduł-level helpery, brak
fixtures/parametrize, `pytest.raises` + inspekcja `.code`). Polskie teksty opisów
kategorii **nie są** zdefiniowane w PRD ani planie — implementer musi je uzupełnić.

---

## Detailed Findings

### 1. Kontrakt `algorithm.classify()`

**Sygnatura** (`plan.md:179`):

```python
def classify(
    amplitudes: Sequence[float],
    config: NormsConfig,
    *,
    analyzed_at: datetime | None = None,
) -> AnalysisResult
```

- `amplitudes` — dokładnie 10 floatów w kolejności `config.norms`; inaczej `ValueError`
- `analyzed_at=None` → fallback na `datetime.now()` wewnątrz funkcji
- Zwraca `AnalysisResult` (`types.py:50`) z `cells`, `category`, `description`, `analyzed_at`

**Helper koloru z epsilonem** (`plan.md:58`, epsilon `1e-6`):

| Wynik | Reguła |
|-------|--------|
| `RED` | `a <= mean_z + ε` |
| `GREEN` | `a >= mean_k - ε` |
| `YELLOW` | `mean_z + ε < a < mean_k - ε` |

Semantyka PRD (`prd.md:160:163`): `a ≤ Z` → red, `a ≥ K` → green, `Z < a < K` → yellow.
Epsilon chroni przed błędami float przy wartościach dokładnie na granicy.

**Reguła kategorii** (`prd.md:165:168`, `plan.md:179`, domyślne progi 5/3/4/3):

```
Policz: red_count, green_count (żółte nie liczą)

if red_count >= indication_min_red AND green_count <= indication_max_green:
    → WSKAZANIE  (defaults: ≥5 red i ≤3 green)
elif green_count >= no_indication_min_green AND red_count <= no_indication_max_red:
    → BRAK       (defaults: ≥4 green i ≤3 red)
else:
    → OBSERWACJA
```

Uwaga: „10/10 red → WSKAZANIE" i „10/10 green → BRAK" wynikają naturalnie z powyższych
warunków (nie trzeba dodatkowych `if`), ale można dodać dla czytelności.

**`CellResult` per komórka** (z odpowiadającego `NormEntry`):

```python
CellResult(
    cell_id=norm.norm_id,
    channel=norm.channel,
    task=norm.task,
    band=norm.band,
    color=_color_for(amplitude, norm.mean_z, norm.mean_k),
)
```

**`AnalysisResult.description`** → `config.category_descriptions.<wskazanie|obserwacja|brak>`

---

### 2. Zmiany w `app/domain/types.py`

**Obecny stan** (`types.py:80:86`) — `NormsConfig` ma tylko:
```python
recommendation_threshold: int   # DEPRECATED
```
Brak `recommendation_rules` i `category_descriptions`.

**Co dodać:**

```python
@dataclass(frozen=True)
class RecommendationRules:
    indication_min_red: int       # default 5
    indication_max_green: int     # default 3
    no_indication_min_green: int  # default 4
    no_indication_max_red: int    # default 3

@dataclass(frozen=True)
class CategoryDescriptions:
    wskazanie: str
    obserwacja: str
    brak: str
```

**`NormsConfig`** — dodać dwa pola, zachować stare `recommendation_threshold` jako
opcjonalne lub usunąć (plan preferuje obsługę obu schematów w loaderze, nie w typie):

```python
@dataclass(frozen=True)
class NormsConfig:
    version: int
    power_line_frequency: float
    recommendation_threshold: int   # zostaje do migracji lub usunąć — patrz notes
    band_ranges: dict[str, BandRange]
    norms: tuple[NormEntry, ...]
    recommendation_rules: RecommendationRules   # nowe
    category_descriptions: CategoryDescriptions  # nowe
```

> **Decyzja implementera:** plan mówi „usunąć lub deprecjonować `recommendation_threshold`"
> (`plan.md:142`). Bezpieczniejsze: zachować jako pole z wartością zmapowaną z
> `recommendation_rules` (lub `0` domyślnie) żeby nie łamać istniejących testów
> `test_norms.py` (walidacja `_TOP_LEVEL_KEYS` i `_valid_payload` używają starego klucza).

---

### 3. Zmiany w `app/domain/norms.py`

**Obecny `_TOP_LEVEL_KEYS`** (`norms.py:12:13`):
```python
_TOP_LEVEL_KEYS = frozenset(
    {"version", "power_line_frequency", "recommendation_threshold", "band_ranges", "norms"}
)
```

**Co zmienić:**

1. Dodać parsowanie `recommendation_rules` (walidacja: 4 int ≥ 0)
2. Dodać parsowanie `category_descriptions` (walidacja: 3 niepuste string)
3. **Migracja:** jeśli brak `recommendation_rules` ale jest stary `recommendation_threshold`
   → zmapuj na `RecommendationRules(5, 3, 4, 3)` (opcjonalny deprecation warning w CLI)
4. Zaktualizować `_TOP_LEVEL_KEYS` — dodać nowe klucze; stary klucz oznaczyć jako opcjonalny
5. Zaktualizować `load()` → `NormsConfig(... recommendation_rules=..., category_descriptions=...)`

**Uwaga dla testów:** `test_norms.py` używa `_valid_payload()` z `recommendation_threshold`.
Po migracji loader musi akceptować stary payload (dla backward compat) lub testy wymagają
aktualizacji `_valid_payload()`.

---

### 4. Zmiany w `norms.json`

Dodać do głównego pliku:

```json
"recommendation_rules": {
  "indication_min_red": 5,
  "indication_max_green": 3,
  "no_indication_min_green": 4,
  "no_indication_max_red": 3
},
"category_descriptions": {
  "wskazanie": "...",
  "obserwacja": "...",
  "brak": "..."
}
```

> **LUKA:** Polskie teksty opisów nie są zdefiniowane w PRD ani planie
> (`plan.md:150`: „teksty PL z PRD/marketingu eksperta"). Implementer musi uzupełnić
> placeholder `"..."` — np. krótkie zdania w stylu ekspertyzy pedagogicznej:
> - `wskazanie`: "Wynik wskazuje na potrzebę dalszej diagnozy specjalistycznej."
> - `obserwacja`: "Wynik wymaga uważnej obserwacji i ewentualnej konsultacji."
> - `brak`: "Wynik nie wskazuje na potrzebę dalszej diagnozy w tej chwili."

---

### 5. Luki UI do wiring (Faza 3, ale `algorithm.py` musi je wyprzedzić)

| Luka | Plik | Linia | Co brakuje |
|------|------|-------|------------|
| `_on_analyze` stub | `file_import.py` | 146–148 | `print` zamiast nawigacji do `AnalysisView` |
| `AppState.norms_config` | `app_window.py` | 11–17 | pole nie istnieje |
| `AppState.analysis_result` | `app_window.py` | 11–17 | pole nie istnieje |
| `AppState.cancel_requested` | `app_window.py` | 11–17 | pole nie istnieje |
| `AppWindow.__init__(NormsConfig)` | `app_window.py` | 21 | brak parametru |
| `main.py` gap | `main.py` | 62 | `AppWindow()` bez `_config` |

Faza 2 **nie musi** naprawiać tych luk — to zakres Fazy 3. Algorytm (`algorithm.py`)
jest modułem domenowym, niezależnym od UI.

---

### 6. Wzorce testów (`test_algorithm.py`)

Na podstawie `test_pipeline.py` i `test_channels.py`:

- **Brak fixtures/parametrize** — plain functions z modułowym helperem
- **Helpery:** `_config()` → `NormsConfig` z `RecommendationRules(5, 3, 4, 3)` i
  `CategoryDescriptions(...)`; opcjonalnie `_amplitudes_all_red()`, `_amplitudes_all_green()`
- **`pytest.importorskip("mne")`** — NIE potrzebne w `test_algorithm.py` (czysta logika,
  bez MNE)

**Minimalne przypadki z planu** (`plan.md:185:187`):

```python
def test_all_red_is_wskazanie(): ...         # 10x czerwone → WSKAZANIE
def test_all_green_is_brak(): ...            # 10x zielone → BRAK
def test_mixed_is_obserwacja(): ...          # 5 red + 3 green + 2 yellow → WSKAZANIE lub OBSERWACJA?
def test_boundary_5red_3green_wskazanie(): ... # exactly 5/3 → WSKAZANIE
def test_boundary_4green_3red_brak(): ...    # exactly 4/3 → BRAK
def test_float_boundary_epsilon(): ...       # a == mean_z (float equality) → RED, nie YELLOW
def test_wrong_amplitude_length_raises(): ... # 9 amplitud → ValueError
def test_category_description_comes_from_config(): ... # description == config.category_descriptions.wskazanie
```

---

## Code References

- `app/domain/types.py:80:86` — `NormsConfig` (brak `recommendation_rules`, `category_descriptions`)
- `app/domain/types.py:41:61` — `CellResult`, `AnalysisResult` — gotowe, nie zmieniać
- `app/domain/types.py:14:23` — `CellColor`, `ScreeningCategory` — gotowe
- `app/domain/norms.py:12:13` — `_TOP_LEVEL_KEYS` — wymaga rozszerzenia
- `app/domain/norms.py:118:126` — `load()` return — wymaga nowych pól
- `app/ui/app_window.py:11:17` — `AppState` — brak 3 pól (Faza 3)
- `app/ui/app_window.py:21` — `AppWindow.__init__` — brak `NormsConfig` (Faza 3)
- `app/ui/views/file_import.py:146:148` — stub `_on_analyze` (Faza 3)
- `app/main.py:62` — `AppWindow()` bez `_config` (Faza 3)
- `norms.json:5` — `recommendation_threshold: 3` (stary schemat, wymaga rozszerzenia)
- `tests/unit/test_norms.py:26:38` — `_valid_payload()` — wymaga aktualizacji po migracji
- `tests/unit/test_pipeline.py:58:64` — wzorzec `@patch("_load_raw")` + `load(resolve_norms_path())`
- `tests/unit/test_channels.py:34:41` — wzorzec `pytest.raises(PipelineError)` + `.code`

---

## Architecture Insights

1. **Algorytm jest czysto domenowy** — `algorithm.py` nie zależy od MNE ani UI. Przyjmuje
   `Sequence[float]` + `NormsConfig`, zwraca `AnalysisResult`. Idealne do unit testowania.

2. **Migracja schematu norms.json jest backward-compatible** — loader powinien akceptować
   stary klucz `recommendation_threshold` (mapując go na `RecommendationRules(5, 3, 4, 3)`)
   żeby nie wymagać zmiany wszystkich fixtures testowych.

3. **Epsilon `1e-6`** — potrzebny, bo pipeline zwraca `float(np.mean(np.abs(...)))`.
   Wartości dokładnie na granicy Z lub K są możliwe przy syntetycznych danych testowych.

4. **`show_view` w `app_window.py`** (`app_window.py:34:44`) przyjmuje `**kwargs` —
   Faza 3 może przekazać dodatkowe argumenty do `AnalysisView` bez zmiany `show_view`.

5. **Kolejność ewaluacji kategorii** — WSKAZANIE sprawdzane przed BRAK. Jeśli oba
   warunki byłyby spełnione jednocześnie (np. przy `recommendation_rules` z ekstremalnymi
   progami), WSKAZANIE wygrywa. To decyzja implementera; warto udokumentować.

---

## Historical Context

- `context/archive/2026-06-01-metadata-and-import/plan.md` — S-01 plan; potwierdza, że
  `AppState` celowo minimalistyczny na starcie (tylko `metadata`, `eeg_path`)
- `context/changes/project-foundation/plan.md` — F-01 definiował `NormsConfig` z
  `recommendation_threshold` (teraz migrowane)
- `context/changes/norms-replacement/plan.md` — S-04 Phase 1 zakończone; `resolve_norms_path()`
  i `--validate-norms` działają (potwierdzone manualnie 2026-06-08)

---

## Open Questions

1. **Polskie teksty kategorii** — jakie dokładnie zdania ma wyświetlać aplikacja jako
   opis wynikowy? Wymagają akceptacji eksperta domenowego przed merge.

2. **Kolejność WSKAZANIE vs BRAK przy nakładaniu się progów** — przy niestandardowych
   `recommendation_rules` możliwa sytuacja, gdy oba warunki są spełnione. Preferowana
   semantyka: WSKAZANIE wygrywa (bardziej konserwatywna dla dziecka).

3. **`recommendation_threshold` w `NormsConfig`** — usunąć pole z dataclassy (breaking
   change) czy zostawić jako alias? Zależy od tego, jak bardzo zależy na czystości typów
   vs kompatybilności z istniejącymi testami.
