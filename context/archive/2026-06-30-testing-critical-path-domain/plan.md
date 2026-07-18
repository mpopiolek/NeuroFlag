# Testing Critical Path Domain — Implementation Plan

## Overview

Faza 1 planu testowego NeuroFlag: pokrycie krytycznej ścieżki domenowej.

Dwa ryzyka z `context/foundation/test-plan.md`:
- **R1** — Algorytm trójstanowy produkuje błędną kategorię na granicy progów przy realnych wartościach `norms.json` (istniejące testy używają syntetycznych `mean_z=10.0`/`mean_k=20.0`)
- **R3** — Podmieniony `norms.json` z nieprawidłowym schematem wczytany cicho bez błędu (istniejące testy pokrywają happy path i kilka error cases, ale nie wszystkie warianty błędów wybrane przez zespół)

## Current State Analysis

Istniejąca baza testów (`tests/unit/`) zawiera 113 testów wyłącznie jednostkowych — brak `tests/integration/`, brak `tests/conftest.py`.

`test_algorithm.py` (22 testy) używa syntetycznych norm `mean_z=10.0`/`mean_k=20.0`. Jedyny test z realnym `norms.json` to `test_classify_with_real_norms_config` — testuje wyłącznie `amplitude=0.0 → WSKAZANIE`, co nie chroni przed regresją przy amplitudach bliskich prawdziwym progom.

`test_norms.py` (18 testów) pokrywa częściowo R3:
- `test_missing_norms_key` → brakujący klucz `norms`
- `test_missing_power_line_frequency` → brakujący `power_line_frequency`
- `test_too_few_norms` → dokładnie 9 norm
- `test_norm_entry_missing_mean_z` → brakujące pole `mean_z`

Niepokryte luki R3: `{}` (pusty JSON), `power_line_frequency: "napis"` (zły typ), brakujące klucze `band_ranges` i `version`, `l_freq > h_freq`, `mean_z ≥ mean_k`.

## Desired End State

Po ukończeniu tego planu:
1. `test_algorithm_real_norms.py` posiada parametryzowane testy `_cell_color()` z realnymi wartościami wszystkich 10 norm z `norms.json` (±2ε od `mean_z` i `mean_k`), plus testy zbiorcze `classify()` na granicy WSKAZANIE i BRAK.
2. `tests/conftest.py` udostępnia `real_norms_config` jako pytest fixture dostępną dla bieżących i przyszłych plików testowych.
3. `test_norms_validation.py` posiada parametryzowane testy wszystkich 6 nieobsłużonych wariantów błędów R3, w tym jeden test który motywuje dodanie walidacji `l_freq < h_freq` do `_parse_band_ranges`.
4. `python -m pytest -q` przechodzi bez błędów; `mypy app/ --strict` przechodzi.

### Key Discoveries:

- `_cell_color()` używa `_EPSILON = 1e-6` przy porównaniach granicznych (`algorithm.py:14`) — testy ±2ε są ściśle powiązane z tą stałą
- `_REQUIRED_TOP_LEVEL_KEYS = frozenset({"version", "power_line_frequency", "band_ranges", "norms"})` (`norms.py:94`) — nie wszystkie 4 klucze mają własny test odrzucenia
- `_parse_band_ranges` (`norms.py:141–155`) tworzy `BandRange` bez sprawdzenia `l_freq < h_freq` — brama ta nie istnieje w kodzie produkcyjnym; test wykryje tę lukę
- Walidacja `mean_z < mean_k` istnieje w `load()` (`norms.py:288–291`) — test dla tej ścieżki jest możliwy bez zmian produkcyjnych
- `_parse_norm_entry` (`norms.py:158–172`) sprawdza każdy klucz z `_NORM_ENTRY_KEYS` — brakujące pola inne niż `mean_z` (np. `mean_k`, `band`, `channel`) nie mają własnych testów

## What We're NOT Doing

- Brak zmian w kodzie produkcyjnym poza ewentualnym dodaniem walidacji `l_freq < h_freq` do `_parse_band_ranges` (wymagane do zdania testu Phase 2)
- Brak testów integracyjnych (Faza 2 test-planu)
- Brak testów DigiTrack, pipeline, fidelity sygnału (Faza 2)
- Nie powielamy istniejących testów: `test_missing_norms_key`, `test_missing_power_line_frequency`, `test_too_few_norms`, `test_norm_entry_missing_mean_z`
- Brak testów UI, PDF, CLI

## Implementation Approach

1. **Najpierw `conftest.py`** — fixture `real_norms_config` zbudowana raz w scope session; wszystkie późniejsze testy z realnymi normami z niej korzystają, bez duplikowania wywołania `load()`.
2. **R1 (Phase 1): parametryzacja po normie** — `@pytest.mark.parametrize("norm", _REAL_CONFIG.norms)` z modułowo załadowaną konfiguracją. Testy `_cell_color()` bezpośrednio, nie przez `classify()`, by mieć precyzyjny sygnał per norma. Testy `classify()` weryfikują end-to-end na granicy kategorii.
3. **R3 (Phase 2): parametryzacja po wariancie błędu** — `@pytest.mark.parametrize("payload, expected_match", [...])` w nowym pliku. Jeden wariant (`l_freq > h_freq`) wymaga najpierw poprawki w `_parse_band_ranges`, by test zdał.

## Critical Implementation Details

- **Walidacja `l_freq < h_freq` nie istnieje** — test z `{"Delta": {"l_freq": 4.0, "h_freq": 0.5}}` pod bieżącym kodem nie rzuci `NormsLoadError` — będzie testował zachowanie, które chcemy dodać. Implementer musi dodać w `_parse_band_ranges` (`norms.py:151` przed budową `BandRange`): `if l_freq >= h_freq: raise NormsLoadError(f"band_ranges['{name}']: l_freq ({l_freq}) must be less than h_freq ({h_freq})")`. Test Phase 2 piszemy z oczekiwaniem `pytest.raises(NormsLoadError)`.

- **`_EPSILON` z `algorithm.py`** jest importowalny jako publiczny (`from app.domain.algorithm import _EPSILON`) — konwencja istniejąca w `test_algorithm.py:7`. Testy w nowym pliku powinny importować go z tego samego miejsca, nie definiować lokalnie.

---

## Phase 1: Shared Fixture + R1 Boundary Tests

### Overview

Tworzy `tests/conftest.py` z session-scoped fixture `real_norms_config` oraz `tests/unit/test_algorithm_real_norms.py` z parametryzowanymi testami granicznymi `_cell_color()` i testami zbiorczymi `classify()` — wszystkie używają realnych wartości z `norms.json`.

### Changes Required:

#### 1. Shared pytest fixture

**File**: `tests/conftest.py`

**Intent**: Udostępnić `NormsConfig` załadowany z pliku `norms.json` projektu jako pytest fixture o zasięgu session — do użycia we wszystkich plikach testowych bez powtarzania wywołania `load()`.

**Contract**: Fixture `real_norms_config() -> NormsConfig`, scope=`"session"`. Ładuje przez `load(resolve_norms_path())`. Importuje `load`, `resolve_norms_path` z `app.domain.norms` i `NormsConfig` z `app.domain.types`.

#### 2. Testy graniczne algorytmu z realnymi normami

**File**: `tests/unit/test_algorithm_real_norms.py`

**Intent**: Zweryfikować, że `_cell_color()` produkuje poprawny kolor przy amplitudach dokładnie na granicach progów z realnego `norms.json` — chroni przed regresją gdyby progi norm uległy zmianie lub logika epsilon się przesunęła.

**Contract**:
- Import na poziomie modułu: `_REAL_CONFIG = load(resolve_norms_path())` (dla `@pytest.mark.parametrize`)
- Cztery funkcje testowe parametryzowane przez `@pytest.mark.parametrize("norm", _REAL_CONFIG.norms)` z `ids=[f"norm{n.norm_id}_{n.channel}_{n.task}_{n.band}" for n in _REAL_CONFIG.norms]`:
  - `test_cell_color_below_z_boundary_real_norms(norm)` — `amplitude = norm.mean_z - 2 * _EPSILON` → `CellColor.RED`
  - `test_cell_color_above_z_boundary_real_norms(norm)` — `amplitude = norm.mean_z + 2 * _EPSILON` → `CellColor.YELLOW`
  - `test_cell_color_below_k_boundary_real_norms(norm)` — `amplitude = norm.mean_k - 2 * _EPSILON` → `CellColor.YELLOW`
  - `test_cell_color_above_k_boundary_real_norms(norm)` — `amplitude = norm.mean_k + 2 * _EPSILON` → `CellColor.GREEN`
- Dwie funkcje testowe zbiorcze używające fixture `real_norms_config`:
  - `test_classify_all_below_mean_z_is_wskazanie(real_norms_config)` — amplitudy `[n.mean_z - 2*_EPSILON for n in cfg.norms]` → `ScreeningCategory.WSKAZANIE`
  - `test_classify_all_above_mean_k_is_brak(real_norms_config)` — amplitudy `[n.mean_k + 2*_EPSILON for n in cfg.norms]` → `ScreeningCategory.BRAK`

### Success Criteria:

#### Automated Verification:

- Testy przechodzą: `python -m pytest tests/unit/test_algorithm_real_norms.py -v`
- Brak błędów mypy: `mypy app/ --strict`
- Brak błędów ruff: `ruff check tests/unit/test_algorithm_real_norms.py tests/conftest.py`
- Pełna suite przechodzi: `python -m pytest -q`

#### Manual Verification:

- Nazwy testów w raporcie pytest zawierają czytelne identyfikatory norm (np. `norm1_C3_OZ_Theta`) — nie tylko indeksy numeryczne
- Żaden istniejący test w `test_algorithm.py` nie jest zduplikowany przez nowe testy

**Implementation Note**: Po ukończeniu tej fazy i przejściu automated verification, poczekaj na ręczne potwierdzenie przed przejściem do Fazy 2. Bloki fazy używają zwykłych punktorów — odpowiadające im `- [ ]` checkboxy żyją w sekcji `## Progress` na dole planu.

---

## Phase 2: R3 Validation Gap Tests

### Overview

Tworzy `tests/unit/test_norms_validation.py` z parametryzowanymi testami walidacji schematu `norms.load()` dla 6 wariantów błędów nieobsłużonych przez istniejące `test_norms.py`. Jeden wariant (`l_freq > h_freq`) wymaga uprzedniego dodania walidacji do `_parse_band_ranges` w `norms.py`.

### Changes Required:

#### 1. Walidacja `l_freq < h_freq` w `_parse_band_ranges`

**File**: `app/domain/norms.py`

**Intent**: Dodać sprawdzenie, że `l_freq < h_freq` w każdym paśmie — bez tej walidacji nieprawidłowy zakres pasma przechodzi cicho do MNE, produkując błędne amplitudy bez komunikatu błędu.

**Contract**: Wewnątrz pętli `_parse_band_ranges`, po obliczeniu obu wartości float, przed tworzeniem `BandRange`: jeśli `l_freq >= h_freq`, rzuć `NormsLoadError(f"band_ranges['{name}']: l_freq ({l_freq}) must be less than h_freq ({h_freq})")`. Wstawiać po liniach 152–153 (wywołania `_as_float`), przed linią 154 (`result[name] = BandRange(...)`).

#### 2. Parametryzowane testy walidacji schematu

**File**: `tests/unit/test_norms_validation.py`

**Intent**: Udokumentować i egzekwować każdy z wybranych wariantów błędów R3 jako osobny, nazwany przypadek testowy — tak, żeby regresja w walidacji schematu była widoczna z nazwy testu, nie z traceback.

**Contract**:
Plik zawiera helper `_write(tmp_path, payload) -> Path` (tożsamy z tym w `test_norms.py` — można skopiować) i `_valid_payload() -> dict` (minimalnie poprawny payload — taki sam jak w `test_norms.py`).

Parametryzowana funkcja: `test_load_invalid_variant(tmp_path, payload_mutator, expected_match)`:
- `@pytest.mark.parametrize` z listą `(id, mutator_fn, match_str)` dla 6 wariantów:

| id | Mutacja | match (regex) |
|----|---------|---------------|
| `empty_json` | `payload = {}` | `"missing required key"` |
| `wrong_type_power_line_frequency` | `payload["power_line_frequency"] = "pięćdziesiąt"` | `"must be a number"` |
| `missing_band_ranges` | `del payload["band_ranges"]` | `"band_ranges"` |
| `missing_version` | `del payload["version"]` | `"version"` |
| `invalid_band_range_l_freq_gt_h_freq` | `payload["band_ranges"]["Delta"] = {"l_freq": 4.0, "h_freq": 0.5}` | `"l_freq"` |
| `mean_z_gte_mean_k` | `payload["norms"][0]["mean_z"] = payload["norms"][0]["mean_k"]` | `"mean_z"` |

Każdy wariant: `p = _write(tmp_path, mutated_payload); with pytest.raises(NormsLoadError, match=expected_match): load(p)`.

### Success Criteria:

#### Automated Verification:

- Testy R3 przechodzą: `python -m pytest tests/unit/test_norms_validation.py -v`
- Brak błędów mypy z nowym kodem: `mypy app/domain/norms.py --strict`
- Brak błędów ruff: `ruff check tests/unit/test_norms_validation.py app/domain/norms.py`
- Pełna suite przechodzi: `python -m pytest -q`

#### Manual Verification:

- Raport pytest -v pokazuje 6 czytelnych nazw wariantów (nie `test_load_invalid_variant[0]` ale `test_load_invalid_variant[empty_json]`)
- Istniejące testy w `test_norms.py` nadal przechodzą — brak regresji

**Implementation Note**: Po ukończeniu tej fazy i przejściu automated verification, poczekaj na ręczne potwierdzenie przed uznaniem Fazy 1 za ukończoną.

---

## Testing Strategy

### Unit Tests:

- `_cell_color()` bezpośrednio z 40 kombinacjami (10 norm × 4 graniczne punkty) — precyzyjny sygnał per norma
- `classify()` end-to-end z amplitudami na granicy WSKAZANIE i BRAK — weryfikacja pełnej ścieżki
- `norms.load()` z 6 wariantami niepoprawnych JSON — weryfikacja walidacji schematu

### Integration Tests:

- Brak w Fazie 1 (Faza 2 test-planu)

### Manual Testing Steps:

1. Uruchom `python -m pytest -v tests/unit/test_algorithm_real_norms.py` — sprawdź że nazwy parametrów zawierają identyfikatory norm (np. `norm1_C3_OZ_Theta`)
2. Uruchom `python -m pytest -v tests/unit/test_norms_validation.py` — sprawdź czytelne nazwy wariantów
3. Uruchom `python -m pytest -q` — sprawdź zero nowych failures

## Performance Considerations

Fixture `real_norms_config` z scope=`session` ładuje `norms.json` raz na całą sesję pytest — brak narzutu IO per test. Testy `_cell_color()` są czysto numeryczne — bez importu MNE, bardzo szybkie.

## References

- Research: `context/changes/testing-critical-path-domain/research.md`
- Test plan — Faza 1: `context/foundation/test-plan.md:56`
- Walidacja `_parse_band_ranges`: `app/domain/norms.py:141–155`
- Walidacja `mean_z < mean_k`: `app/domain/norms.py:288–291`
- `_EPSILON` boundary constant: `app/domain/algorithm.py:14`
- Istniejące testy algorytmu: `tests/unit/test_algorithm.py`
- Istniejące testy norm: `tests/unit/test_norms.py`

## Progress

> Konwencja: `- [ ]` oczekuje, `- [x]` zrobione. Dopisz ` — <commit sha>` gdy krok ląduje. Nie zmieniaj tytułów kroków. Zob. `references/progress-format.md`.

### Phase 1: Shared Fixture + R1 Boundary Tests

#### Automated

- [x] 1.1 Testy graniczne przechodzą: `python -m pytest tests/unit/test_algorithm_real_norms.py -v` — 6618e55
- [x] 1.2 Brak błędów mypy: `mypy app/ --strict` — 6618e55
- [x] 1.3 Brak błędów ruff: `ruff check tests/unit/test_algorithm_real_norms.py tests/conftest.py` — 6618e55
- [x] 1.4 Pełna suite przechodzi: `python -m pytest -q` — 6618e55

#### Manual

- [x] 1.5 Nazwy testów zawierają czytelne identyfikatory norm (np. `norm1_C3_OZ_Theta`) — 6618e55
- [x] 1.6 Brak duplikacji istniejących testów z `test_algorithm.py` — 6618e55

### Phase 2: R3 Validation Gap Tests

#### Automated

- [x] 2.1 Testy R3 przechodzą: `python -m pytest tests/unit/test_norms_validation.py -v` — 8bc070f
- [x] 2.2 Brak błędów mypy z nowym kodem: `mypy app/domain/norms.py --strict` — 8bc070f
- [x] 2.3 Brak błędów ruff: `ruff check tests/unit/test_norms_validation.py app/domain/norms.py` — 8bc070f
- [x] 2.4 Pełna suite przechodzi: `python -m pytest -q` — 8bc070f

#### Manual

- [x] 2.5 Raport pytest -v pokazuje 6 czytelnych nazw wariantów (np. `[empty_json]`, `[wrong_type_power_line_frequency]`) — 8bc070f
- [x] 2.6 Istniejące testy w `test_norms.py` nadal przechodzą bez regresji — 8bc070f
