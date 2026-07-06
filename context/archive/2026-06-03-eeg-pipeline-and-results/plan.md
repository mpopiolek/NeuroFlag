# Pipeline EEG i wyniki — Implementation Plan

## Overview

Implementacja slice S-02 (roadmap): pipeline MNE przetwarzający wczytany plik EEG do 10 wewnętrznych wartości amplitudy, algorytm klasyfikacji trójstanowej względem norm, oraz widoki GUI (postęp analizy → siatka wyników). Zakłada ukończone S-01 (`AppState.metadata`, `AppState.eeg_path`, walidacja nagłówka) i F-01 (typy, `norms.json`). PDF (S-03) i pełna dokumentacja podmiany norm (S-04) są poza tym planem.

## Current State Analysis

**Istnieje:**
- `app/domain/types.py` — `CellResult`, `AnalysisResult`, `NormsConfig`, `CellColor`, `ScreeningCategory`
- `app/domain/norms.py` — loader 10 norm, `band_ranges`, `recommendation_threshold`
- `app/domain/eeg_file.py` — walidacja nagłówka `.edf` / BrainVision
- `app/ui/views/file_import.py` — stub `_on_analyze` (linie 146–148)
- `norms.json` — macierz 10 norm z PRD

**Brakuje:**
- `pipeline.py`, `algorithm.py`, moduł aliasów kanałów
- Widoki `analysis.py`, `results_grid.py`, komponenty RAG
- `NormsConfig` w stanie aplikacji; wynik analizy w `AppState`
- Testów pipeline/algorithm

### Key Discoveries:

- `main.py:55-64` ładuje normy, ale nie przekazuje `NormsConfig` do `AppWindow` — S-02 musi to podpiąć
- Roadmap identyfikuje S-02 jako najwyższe ryzyko techniczne (`context/foundation/roadmap.md:97`)
- W repo brak pliku `.edf`; testy muszą używać syntetycznego `mne.io.Raw`
- PRD wymaga niewidocznych µV w UI — wyjątki i panel „Szczegóły” nie mogą logować tablic ani surowych wartości

## Desired End State

Po zakończeniu wszystkich faz (w tym Fazy 4):

1. Pedagog z ważną metryką i plikiem EEG klika „Analizuj” na `FileImportView`.
2. `AnalysisView` pokazuje postęp; „Anuluj” ustawia flagę cooperative — pipeline kończy się `AnalysisCancelledError` bez crashu.
3. Po sukcesie `ResultsGridView` renderuje 10 komórek (czerwony/żółty/zielony), nagłówek kategorii i opis z `category_descriptions` w norms.
4. Przy błędzie: komunikat PL, powrót do importu z zachowanym plikiem; opcjonalnie zwinięty „Szczegóły” (typ błędu, bez µV).
5. `python -m pytest -q` i `mypy app/ --strict` przechodzą.

**Weryfikacja manualna:** plik testowy od operatora (poza repo); czas ≤10 min; brak µV w oknie i w szczegółach błędu.

## What We're NOT Doing

- Generowanie i zapis PDF (S-03)
- Raport jakości artefaktów / procent odrzuconych epok (v2.0)
- Pełna dokumentacja `recommendation_rules` i szablonu norms w S-04 (tylko minimalna walidacja w loaderze S-02)
- ICA i pakiet `autoreject` jako zależność
- Picker kanałów w Fazach 1–3 (dopiero Faza 4)
- Ponowna walidacja wykluczeń klinicznych na imporcie (S-01 — opcjonalnie wzmocnienie w Fazie 3, nie blocker)

## Implementation Approach

Kolejność: **domena (pipeline → algorithm → norms schema) → UI (postęp → wyniki) → picker**. Pipeline zwraca wewnętrzną strukturę pośrednią (np. `PipelineMetrics` z 10 floatami w µV) używaną wyłącznie przez `algorithm` — UI widzi tylko `AnalysisResult`. Wszystka praca MNE poza wątkiem UI (ten sam wzorzec co `file_import.py`). Anulowanie: `AppState.cancel_requested` sprawdzane między krokami `pipeline.run()`.

## Critical Implementation Details

**Odrzucanie epok (MVP):** Po wycięciu segmentów OO/OZ/ZP utwórz `mne.Epochs` (np. 1 s okna lub cały segment jako pojedyncza epoka — wybór implementera: preferuj jedną epokę = cały segment zadania, żeby `mean(abs)` było reprezentatywne). Zastosuj `epochs.drop_bad(reject=dict(eeg=…))` z progami w µV (stałe rozsądne domyślne, np. 200 µV peak-to-peak, lub stała w module pipeline) — to realizuje intencję „autoreject” bez dodatkowej zależności.

**Tolerancja float przy kolorach:** Porównania do `mean_z` / `mean_k` przez helper z epsilonem (np. `1e-6`) zachowują semantykę PRD: czerwony `a <= z`, zielony `a >= k`, żółty między.

**Migracja norms:** Zastąp top-level `recommendation_threshold` blokiem `recommendation_rules` (4 inty). Loader: jeśli jest stary klucz, zmapuj na domyślne 5/3/4/3 i emituj deprecation w komunikacie walidacji CLI (opcjonalnie) — lub wymagaj nowego schematu z czytelnym `NormsLoadError` (decyzja implementera: **preferuj obsługę obu** przez jedną migrację w `norms.py` przy load).

---

## Phase 1: Pipeline sygnału i aliasy kanałów

### Overview

Dostarcza `pipeline.run()` od ścieżki pliku do 10 wartości amplitudy (µV, wewnętrznie), z segmentacją zadań, filtrem notch, filtrem pasmowym per komórka i odrzuceniem złych epok. Moduł `channels.py` standaryzuje nazwy i wymaga C3/O1 po mapowaniu aliasów.

### Changes Required:

#### 1. Aliasy i walidacja kanałów

**File**: `app/domain/channels.py`

**Intent**: Standaryzacja nazw kanałów (regex/słownik: `EEG C3`, `C3-REF`, `C3-A1` → `C3`; analogicznie O1) oraz jawna lista brakujących kanałów po normalizacji.

**Contract**: `normalize_channel_names(raw: mne.io.BaseRaw) -> None` (in-place rename); `require_channels(raw, names: tuple[str, ...]) -> None` rzuca `PipelineError` z listą dostępnych kanałów w komunikacie (nazwy tylko, bez danych sygnału).

#### 2. Wyjątki pipeline

**File**: `app/domain/pipeline.py` (początek pliku) lub `app/domain/errors.py`

**Intent**: Jednolity typ błędu domenowego dla UI.

**Contract**: `PipelineError(Exception)` z polami `code: str`, `user_message_pl: str`; `AnalysisCancelledError(PipelineError)` gdy `cancel_check()` zwróci True.

#### 3. Segmentacja OO/OZ/ZP

**File**: `app/domain/pipeline.py`

**Intent**: Wykryj trzy warunki z adnotacji w kolejności OO→OZ→ZP (aliasy PL/EN). **Fallback:** brak rozpoznanych znaczników + nagranie ≥ 8 min → 3×3 min od początku. **Błąd:** częściowe znaczniki lub nagranie &lt; 8 min. Szczegóły: `docs/EEG-segmentacja.md`.

**Contract**: `detect_task_segments(raw) -> dict[str, tuple[float, float]]` klucze `OO`|`OZ`|`ZP`, wartości `(t_start, t_end)` w sekundach; przy braku 3 znaczników lub nagraniu &lt; 8 min — `PipelineError`.

#### 4. Obliczenie 10 amplitud

**File**: `app/domain/pipeline.py`

**Intent**: Dla każdego `NormEntry` z config: wytnij segment zadania i kanał, notch (`power_line_frequency`), filtr pasma z `band_ranges`, odrzuć złe epoki, `mean(abs(data_uv))`.

**Contract**: `run(path: Path, config: NormsConfig, *, cancel_check: Callable[[], bool] = lambda: False) -> tuple[float, ...]` — dokładnie 10 floatów w kolejności `config.norms` po `norm_id`; `preload=True` przy `read_raw_*`; `get_data(units="uV")`.

#### 5. Testy syntetyczne pipeline

**File**: `tests/unit/test_channels.py`, `tests/unit/test_pipeline.py`

**Intent**: Krótki syntetyczny `Raw` (np. 600 s, sfreq 250, kanały C3/O1 + EOG) z adnotacjami OO/OZ/ZP; assert `len(result)==10` i brak NaN.

**Contract**: Bez plików binarnych w repo; mock tylko jeśli konieczny dla izolacji notch.

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/test_channels.py tests/unit/test_pipeline.py -q`
- `mypy app/domain/pipeline.py app/domain/channels.py --strict`

#### Manual Verification:

- Uruchom `run()` z REPL na lokalnym pliku `.edf` (jeśli dostępny) — zwraca 10 liczb w rozsądnym czasie
- Sprawdź, że plik bez C3/O1 po aliasach kończy się `PipelineError` z czytelnym PL

**Implementation Note**: Po przejściu automated i manual Phase 1 — pauza przed Fazą 2.

---

## Phase 2: Algorytm klasyfikacji i rozszerzenie norms.json

### Overview

`algorithm.py` mapuje 10 amplitud na kolory i kategorię. Rozszerza schemat `norms.json` o `recommendation_rules` i `category_descriptions`; aktualizuje typy i loader.

### Changes Required:

#### 1. Typy konfiguracji

**File**: `app/domain/types.py`

**Intent**: Reprezentacja reguł progowych i opisów kategorii.

**Contract**: `@dataclass(frozen=True) RecommendationRules` z polami `indication_min_red`, `indication_max_green`, `no_indication_min_green`, `no_indication_max_red`; `@dataclass(frozen=True) CategoryDescriptions` z `wskazanie`, `obserwacja`, `brak` (str); `NormsConfig` rozszerzone o te pola (usunąć lub deprecjonować samo `recommendation_threshold`).

#### 2. Loader norms

**File**: `app/domain/norms.py`

**Intent**: Parsowanie nowych bloków JSON; migracja ze starego `recommendation_threshold` jeśli obecny.

**Contract**: Walidacja: wszystkie 4 progi są int ≥0; `category_descriptions` — 3 niepuste stringi; domyślne wartości 5,3,4,3 i teksty PL z PRD/marketingu eksperta.

> **Intentional deviation**: `recommendation_rules` jest **obowiązkowy** (lub migrowalna przez `recommendation_threshold`) — brak obu kluczy rzuca `NormsLoadError` zamiast cichego fallbacku. Decyzja celowa: klucz reguł jest za ważny semantycznie by ignorować jego brak; `category_descriptions` zachowuje cichy fallback bo to tylko copy. Produkcja nienaruszona (norms.json zawiera blok).

#### 3. norms.json

**File**: `norms.json`

**Intent**: Dostarczyć `recommendation_rules` i `category_descriptions` w pliku domyślnym.

**Contract**: Przykładowa struktura:
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

#### 4. Algorytm kolorów i kategorii

**File**: `app/domain/algorithm.py`

**Intent**: Zbuduj `AnalysisResult` zgodny z PRD i decyzjami planowania.

**Contract**: `classify(amplitudes: Sequence[float], config: NormsConfig, *, analyzed_at: datetime | None = None) -> AnalysisResult`; kolor komórki i helper z epsilonem; kategoria: jeśli wszystkie komórki red → `WSKAZANIE`; wszystkie green → `BRAK`; w przeciwnym razie liczniki vs `recommendation_rules`; opis z `category_descriptions` dla wybranej kategorii; 10× `CellResult` z polami z `NormEntry`.

#### 5. Testy algorithm + norms

**File**: `tests/unit/test_algorithm.py`, rozszerzenie `tests/unit/test_norms.py`

**Intent**: Tabele przypadków: 10/10 red, 5 red + 3 green, granice Z/K z float, błędny JSON rules.

**Contract**: Pokrycie wszystkich trzech kategorii i `ValueError` dla złej długości wejścia.

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/test_algorithm.py tests/unit/test_norms.py -q`
- `mypy app/domain/algorithm.py app/domain/types.py app/domain/norms.py --strict`
- `python app/main.py --smoke-test` (exit 0 po aktualizacji norms.json)

#### Manual Verification:

- `python app/main.py --validate-norms norms.json` — OK po zmianie schematu

**Implementation Note**: Pauza po Fazie 2 przed UI.

---

## Phase 3: UI — analiza, anulowanie, siatka wyników

### Overview

Podpięcie pipeline w tle, widok postępu z anulowaniem, widok wyników RAG, przekazanie `NormsConfig` do aplikacji.

### Changes Required:

#### 1. Stan aplikacji

**File**: `app/ui/app_window.py`, `app/main.py`

**Intent**: Udostępnić config norm i wynik analizy; flaga anulowania.

**Contract**: `AppState` pola: `norms_config: NormsConfig`, `analysis_result: AnalysisResult | None`, `cancel_requested: bool`; `AppWindow.__init__(norms_config: NormsConfig)`; `main.py` przekazuje `_config` do `AppWindow`.

#### 2. Widok postępu

**File**: `app/ui/views/analysis.py`

**Intent**: Ekran „Trwa analiza…” z paskiem lub spinnerem CTk i przyciskiem „Anuluj”; wątek wywołuje `pipeline.run` + `algorithm.classify`.

**Contract**: Wzorzec `threading` + `after(0, …)` jak `file_import.py`; sukces → `show_view(ResultsGridView)`; błąd → komunikat + `show_view(FileImportView)`; anulowanie → komunikat „Anulowano”.

#### 3. Siatka wyników

**File**: `app/ui/views/results_grid.py`, `app/ui/components/rag_cell.py` (lub inline w widoku)

**Intent**: 10 komórek w układzie 2×5 lub 5×2 z etykietami kanał/zadanie/pasmo (bez µV); nagłówek `ScreeningCategory`; opis z wyniku.

**Contract**: Kolory tła/mapowanie `CellColor` → hex zgodne z PRD (#CC0000 / żółty / #00AA00 — wartości dopracować z ekspertem); przycisk „← Nowe badanie” → `MetadataFormView` z czyszczeniem stanu analizy.

#### 4. Podpięcie Analizuj

**File**: `app/ui/views/file_import.py`

**Intent**: Zastąpić stub nawigacją do `AnalysisView`.

**Contract**: `_on_analyze` → `show_view(AnalysisView)` gdy `ready_for_analysis()`; usunąć `print` stub.

#### 5. Błędy — panel szczegółów

**File**: `app/ui/views/analysis.py` (lub wspólny helper `app/ui/messages.py`)

**Intent**: Zwinięty `CTkFrame` „Szczegóły” z `code` i krótkim PL; nigdy traceback ani liczby amplitud.

**Contract**: `format_pipeline_error(exc: PipelineError) -> str` — jedna linia dla pedagoga.

#### 6. Testy UI (ograniczone)

**File**: `tests/unit/test_algorithm.py` (wystarczy z Fazy 2); opcjonalnie `tests/unit/test_analysis_messages.py` dla formatterów bez CTk headless

**Intent**: Logika komunikatów bez uruchamiania okna.

**Contract**: Jeśli brak CTk w CI — testuj tylko funkcje czyste.

### Success Criteria:

#### Automated Verification:

- `python -m pytest -q`
- `mypy app/ --strict`
- `ruff check app/`

#### Manual Verification:

- Flow: metryka → import → Analizuj → postęp → siatka; brak µV w UI i w Szczegółach
- Anuluj w trakcie — powrót bez crashu
- Plik bez segmentów / zły kanał — komunikat PL i powrót do importu
- Czas analizy na sample file ≤10 min

**Implementation Note**: Pauza po Fazie 3 przed pickerem (Faza 4).

---

## Phase 4: Picker mapowania kanałów (podfaza)

### Overview

Ręczne mapowanie brakujących C3/O1 z listy kanałów pliku przed uruchomieniem pipeline — realizacja decyzji użytkownika z planowania (po działającym pipeline z aliasami).

### Changes Required:

#### 1. Stan mapowania

**File**: `app/ui/app_window.py`, `app/domain/types.py` (opcjonalnie `ChannelMapping`)

**Intent**: Przechować wybór użytkownika na czas sesji.

**Contract**: `AppState.channel_overrides: dict[str, str]` np. `{"C3": "EEG 4"}`; pipeline przyjmuje opcjonalne overrides przed `require_channels`.

#### 2. Dialog przed analizą

**File**: `app/ui/views/channel_mapping.py` lub modal w `file_import.py`

**Intent**: Gdy po aliasach nadal brak C3 lub O1 — pokaż CTkOptionMenu per brakujący kanał; „Kontynuuj” / „Anuluj”.

**Contract**: Wywołanie z `FileImportView` po walidacji nagłówka (lekkie odczytanie listy kanałów bez pełnego preload) lub na wejściu do `AnalysisView`; mapowanie stosowane w `pipeline.run`.

#### 3. Wczesne ostrzeżenie (opcjonalne)

**File**: `app/domain/eeg_file.py` lub `channels.py`

**Intent**: Przy imporcie: jeśli nagłówek bez aliasów dla C3/O1 — status żółty „Brak C3/O1 — wybór kanału przy analizie”.

**Contract**: Nie blokuje importu; informuje przed kliknięciem Analizuj.

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/test_channels.py -q` (scenariusz overrides)
- `mypy app/ --strict`

#### Manual Verification:

- Plik z kanałem `EEG 4` zamiast C3 — użytkownik mapuje i dostaje wynik
- Anuluj w dialogu — powrót do importu bez uruchamiania pipeline

---

## Testing Strategy

### Unit Tests:

- `test_algorithm.py` — wszystkie kategorie, granice Z/K, reguły 5/3/4/3
- `test_pipeline.py` — syntetyczny Raw, cancel flag, brak kanału
- `test_channels.py` — aliasy, overrides
- `test_norms.py` — nowy JSON, migracja threshold

### Integration Tests:

- Brak w repo pliku `.edf` — integracja manualna; opcjonalnie `tests/integration/` w przyszłości z gitignored sample

### Manual Testing Steps:

1. Pełny flow na pliku z poprawnymi znacznikami OO/OZ/ZP (kolejność, ≥ 8 min)
2. Plik bez znaczników zadań (≥ 8 min) — fallback 3×3 min
3. Plik ze częściowymi znacznikami — komunikat błędu
4. Anulowanie w połowie analizy (`--debug-slow-analysis=3`)
5. Plik z dziwnymi nazwami kanałów — Faza 4 picker
6. Potwierdź brak µV w UI i w Szczegółach błędu

Mapowanie plików: `tests/fixtures/MANUAL-QA.md`, reguły: `docs/EEG-segmentacja.md`.

## Performance Considerations

- `preload=True` — pamięć vs czas; dla typowego badania przesiewowego akceptowalne w PRD (≤10 min)
- Unikaj wielokrotnego `raw.copy()` — jedna kopia po notch, filtry pasmowe na kopiach per komórka jeśli konieczne
- Anulowanie między komórkami norm (pętla 10) — responsywne UI

## Migration Notes

- Zaktualizuj `norms.json` i test fixtures w `test_norms.py` / `test_main_cli.py`
- S-04 później rozszerzy dokumentację i `--validate-norms` o pełny opis `recommendation_rules`
- Komunikat dla użytkowników ze starym `recommendation_threshold`: loader mapuje lub zwraca błąd z instrukcją migracji

## References

- PRD: `context/foundation/prd.md` (pipeline, algorytm, FR-002–004)
- Roadmap S-02: `context/foundation/roadmap.md`
- S-01 plan (archiwum): `context/archive/2026-06-01-metadata-and-import/plan.md`
- AGENTS.md — idiomy MNE
- Typy: `app/domain/types.py`
- Stub Analizuj: `app/ui/views/file_import.py:146-148`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: Pipeline sygnału i aliasy kanałów

#### Automated

- [x] 1.1 `python -m pytest tests/unit/test_channels.py tests/unit/test_pipeline.py -q`
- [x] 1.2 `mypy app/domain/pipeline.py app/domain/channels.py --strict`

#### Manual

- [x] 1.3 Pipeline na lokalnym `.edf` zwraca 10 wartości bez NaN w rozsądnym czasie — manual QA 2026-06-11
- [x] 1.4 Plik bez C3/O1 po aliasach — czytelny `PipelineError` po polsku — manual QA 2026-06-11

### Phase 2: Algorytm klasyfikacji i rozszerzenie norms.json

#### Automated

- [x] 2.1 `python -m pytest tests/unit/test_algorithm.py tests/unit/test_norms.py -q`
- [x] 2.2 `mypy app/domain/algorithm.py app/domain/types.py app/domain/norms.py --strict`
- [x] 2.3 `python app/main.py --smoke-test`

#### Manual

- [x] 2.4 `python app/main.py --validate-norms norms.json` zwraca OK

### Phase 3: UI — analiza, anulowanie, siatka wyników

#### Automated

- [x] 3.1 `python -m pytest -q` — 9457060
- [x] 3.2 `mypy app/ --strict` — 9457060
- [x] 3.3 `ruff check app/` — 9457060

#### Manual

- [x] 3.4 Flow metryka → import → Analizuj → wyniki bez µV w UI — manual QA 2026-06-11
- [x] 3.5 Anuluj i błąd pipeline — komunikat PL, powrót do importu, Szczegóły bez µV — manual QA 2026-06-11
- [x] 3.6 Czas analizy sample file ≤10 min — manual QA 2026-06-11

### Phase 4: Picker mapowania kanałów

#### Automated

- [x] 4.1 `python -m pytest tests/unit/test_channels.py -q` (overrides) — f551884
- [x] 4.2 `mypy app/ --strict` — f551884

#### Manual

- [x] 4.3 Mapowanie obcego kanału na C3/O1 — analiza kończy się sukcesem — f551884
- [x] 4.4 Anuluj w dialogu mapowania — brak uruchomienia pipeline — f551884
