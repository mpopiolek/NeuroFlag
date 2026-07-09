# Kalibracja offline pipeline vs Mitsar — Implementation Plan

## Overview

Zbudować **pętlę kalibracji offline**, która zbliża profil 10 amplitud NeuroFlag do centroidów skali Mitsar (CSV N=82), bez mapowania ID od eksperta i bez kontaktu z ekspertem. Kotwice EDF: `ADHD_EEG.edf` i `depresja_EEG.edf`. `ok_EEG.edf` pomijamy (flat-line C3/O1). Po wyborze zwycięzcy — podpięcie do produkcyjnego `pipeline.run()` w osobnej fazie końcowej.

**Branch roboczy:** `experiment/pipeline-amplitude-calibration` (docs zsynchronizowane z `coursor/dev-env-setup-2f65`).

## Current State Analysis

### Co już istnieje

- **Research i strategia offline:** `research.md`, `offline-calibration-plan.md`, `handoff.md` — pełna analiza rozjazdu skali (~4–7× za nisko), mapowanie 10 kolumn CSV, centroidy kategorii z klasyfikacji Mitsar.
- **WIP na branchu experiment:** `app/domain/amplitude.py` (5 metod time-domain), `amplitude_method` w `NormsConfig` / `norms.py` / template — **ładowane, ale nieużywane**.
- **Pipeline produkcyjny:** `app/domain/pipeline.py:315-387` — hardcoded `_mean_abs_after_artifact_rejection` (1 s okna, 200 µV pp **po** filtrze pasma); alias ZP `"ZADANIE POZNA"` już w kodzie (`6178904`).
- **Skrypty eksperymentalne:** `scripts/compare_amplitude_methods.py` (ustawia `amplitude_method`, ale `run()` ignoruje), `scripts/diagnose_patient_files.py` (whole-segment reject — rozjazd z pipeline).
- **Dane eksperta (poza repo):** `D:\CVGOSI\NF dane\analiza eeg\wyniki_indywidualne.csv`, pliki EDF w `D:\CVGOSI\NF dane\Testowe\`.

### Kluczowe luki

| Luka | Wpływ |
|------|-------|
| Brak loadera CSV + centroidów | Nie da się shadow validation |
| Brak metryki Welch/PSD | Główna hipoteza research nie testowalna |
| Brak harness offline z parametrami artefaktów | Nie da się 2-pass sweep |
| `compare_amplitude_methods.py` nie działa | Fałszywe wrażenie sweepu |
| `depresja_EEG.edf` → `artifact_rejection` | Blokuje drugą kotwicę EDF (segmentacja OK po aliasie) |

### Key Discoveries

- Klasyfikacja Mitsar na 82 wierszach CSV: mediana `amp/mean_z` ≈ **0.63** (Wskazanie) vs **1.38** (Brak) — `offline-calibration-plan.md`.
- Obecny pipeline ADHD: `NF/mean_z` ≈ **0.13–0.35** — za nisko nawet względem profilu patologicznego w skali eksperta.
- Globalny mnożnik skali **nie rozdziela** ok vs ADHD — wymagana zmiana metryki/czyszczenia, nie gain.
- `compute_band_amplitude()` nie ma odrzucania artefaktów; pipeline ma 3 semantyki „mean abs” (reject-then-mean vs epoch-mean vs full-segment mean) — implementer musi je rozdzielić w harness.

## Desired End State

1. Skrypt `scripts/calibrate_against_expert_csv.py` generuje raport: dla każdego wariantu (metoda × parametry artefaktów) odległość profilu ADHD/depresja od centroidu „Wskazanie” w przestrzeni `amp/mean_z` (10 wymiarów).
2. Wybrany wariant minimalizuje odległość od centroidu „Wskazanie” na kotwicach EDF (ADHD + depresja). Rozkład kategorii 82 profili CSV weryfikowany **jednorazowo w fazie 1** (sanity check loadera) — nie jako filtr per-wariant w sweepie.
3. Produkcyjny `pipeline.run()` używa zwycięskiej konfiguracji (metoda + parametry artefaktów); `norms.json` domyślny bez zmian progów — tylko metoda/pipeline.
4. Testy jednostkowe + integracyjne pokrywają CSV loader, centroidy, Welch/PSD, harness; mypy strict na nowym kodzie.
5. `ok_EEG.edf` **nie** jest kryterium akceptacji sweepu (pominięty zgodnie z decyzją planu).

### Weryfikacja końcowa (manualna)

- Uruchomienie kalibracji na maszynie z dostępem do `D:\CVGOSI\NF dane\` — raport wskazuje wariant z najniższą odległością od centroidu Wskazanie dla ADHD i depresja.
- `python -m pytest -q` + `mypy app/ --strict` zielone.
- Po fazie 4: `probe_pipeline.py` na ADHD/depresja daje sensowne amplitudy (~10–30 µV dla Thety, nie ~2–5 µV).

## What We're NOT Doing

- Mapowanie ID CSV → pliki EDF (brak danych od eksperta).
- Walidacja / optymalizacja względem `ok_EEG.edf` (flat-line C3/O1).
- Zmiana progów `mean_z` / `mean_k` w `norms.json` ani reguł RAG w `algorithm.py`.
- Pełne odtworzenie ICA eksperta — tylko heurystyczne 2-pass czyszczenie okien.
- Zmiana readera DigiTrack / `Kuczyński.EEG` (legacy, poza zestawem walidacyjnym).
- UI do wyboru metody amplitudy — tylko `norms.json` / config wewnętrzny.
- Commit/push danych eksperta (CSV/EDF) do repo.

## Implementation Approach

**Strategia offline-first:** fazy 1–3 budują moduł kalibracji i harness **obok** produkcyjnego pipeline; faza 4 przenosi zwycięzcę do `pipeline.py`. Dzięki temu sweep nie rykuje regresją GUI.

**Target funkcji celu:** odległość euklidesowa (lub średnia różnica bezwzględna) profilu `ratio[i] = amp[i] / mean_z[i]` od centroidu kategorii „Wskazanie” wyliczonego z 82 wierszy CSV. **Sanity check (faza 1):** rozkład kategorii po klasyfikacji 82 profili CSV nie jest degenerowany (np. 100% jednej kategorii) — wykonywany raz przy starcie, nie w grid sweep.

**Harness vs produkcja:** `app/domain/signal_amplitude.py` (współdzielona logika amplitudy) + `app/domain/calibration/` (CSV, sweep). Harness importuje `pipeline.detect_task_segments` i publiczny loader (nie `_load_raw` bezpośrednio — preferuj wywołanie przez cienki wrapper w `pipeline` lub reuse `run()` segmentacji). **Pipeline importuje tylko `signal_amplitude`**, nie `calibration` — brak cyklu modułów.

## Critical Implementation Details

- **Kolejność operacji w harness:** Pass 1 (broadband pp na oknach 1 s) → filtr notch + pasma → Pass 2 (pp na przefiltrowanym) → `compute_band_amplitude`. Odwrotna kolejność da inne wyniki niż workflow eksperta.
- **CSV Mitsar:** separator kolumn `;` lub `,`, **przecinek dziesiętny** w wartościach — parser musi normalizować do `float` przed obliczeniami.
- **Welch/PSD:** amplituda = `sqrt(mean(PSD w paśmie))` w µV — spójne z „mocą bezwzględną w paśmie” eksperta; okno Welch dopasować do długości segmentu (min. kilka okien 1–2 s).
- **depresja_EEG.edf:** po aliasie ZP segmentacja działa; błąd to `artifact_rejection` na OZ/O1 — sweep progów (100–300 µV) i min. czystego segmentu (30–90 s) jest **konieczny**, nie fix segmentacji.

## Phase 1: Fundament kalibracji (CSV + centroidy)

### Overview

Loader danych Mitsar, mapowanie 10 kolumn, baseline centroidów kategorii i metryka odległości profilu — fundament pod shadow validation.

### Changes Required:

#### 1. Moduł domenowy kalibracji

**File**: `app/domain/calibration/__init__.py`, `app/domain/calibration/csv_oracle.py`

**Intent**: Udostępnić typy i funkcje do wczytania `wyniki_indywidualne.csv`, mapowania 10 kolumn na `NormEntry.id`, obliczenia profili `amp/mean_z` i centroidów per kategoria algorytmu NeuroFlag.

**Contract**:
- `CELL_CSV_COLUMNS: tuple[tuple[int, str], ...]` — 10 par `(norm_id, nazwa_kolumny_csv)` zgodnie z `offline-calibration-plan.md`.
- `ExpertCsvRow` dataclass: `row_id: str`, `grupa: str`, `amplitudes: tuple[float, ...]` (10 wartości µV).
- `load_expert_csv(path: Path) -> tuple[ExpertCsvRow, ...]`
- `profile_ratios(amplitudes: tuple[float, ...], config: NormsConfig) -> tuple[float, ...]` — 10 stosunków do `mean_z`.
- `classify_csv_row(amplitudes, config) -> ScreeningCategory` — delegacja do `classify().category`.
- `compute_category_centroids(rows, config) -> dict[ResultCategory, tuple[float, ...]]`
- `profile_distance(a: tuple[float, ...], b: tuple[float, ...]) -> float`

#### 2. Konfiguracja ścieżki danych

**File**: `app/domain/calibration/paths.py` (opcjonalnie) lub stałe w skrypcie z override CLI

**Intent**: Domyślna ścieżka CSV i EDF przez argumenty CLI / zmienne środowiskowe; hardcode Windows jako default z możliwością `--csv-path` / `--edf-dir`.

**Contract**: `DEFAULT_EXPERT_CSV`, `DEFAULT_EDF_DIR` — nie commitować kopii CSV do repo.

#### 3. Testy jednostkowe

**File**: `tests/unit/test_calibration_csv.py`

**Intent**: Fixture minimalnego CSV (3–5 wierszy, przecinek dziesiętny), weryfikacja mapowania kolumn, centroidów i `profile_distance`.

**Contract**: Testy bez zewnętrznego pliku eksperta — inline fixture w `tests/fixtures/` (anonimowe wartości, nie prawdziwe dane pacjentów).

### Success Criteria:

#### Automated Verification:

- Unit tests pass: `python -m pytest tests/unit/test_calibration_csv.py -q`
- Type checking passes: `mypy app/domain/calibration/ --strict`
- Full suite green: `python -m pytest -q`

#### Manual Verification:

- Na maszynie z CSV: jednorazowy smoke `python -c "..."` ładuje 82 wiersze, drukuje 3 centroidy (Wskazanie/Brak/Obserwacja — mediana profilu Wskazanie ≈ 0.63 ± tolerancja) **oraz** rozkład kategorii (sanity check: nie degenerowany, oczekiwane ~60/6/16)

**Implementation Note**: Po tej fazie i zielonych testach — potwierdzenie manualne centroidów przed fazą 2.

---

## Phase 2: Harness offline + Welch/PSD

### Overview

Odizolowany harness obliczeń amplitudy z parametrami (metoda, 2-pass artefakty, progi) oraz nowa metoda widmowa — bez zmian w produkcyjnym `run()`.

### Changes Required:

#### 1. Metoda Welch/PSD

**File**: `app/domain/amplitude.py`

**Intent**: Dodać `AmplitudeMethod.WELCH_BAND_POWER = "welch_band_power"` — redukcja przez moc widmową w paśmie już przefiltrowanym sygnału.

**Contract**: `compute_band_amplitude(data_uv, sfreq, method, *, band: BandRange | None = None)` — parametr `band` **wymagany** dla `welch_band_power` (integracja PSD w `[l_freq, h_freq]`), ignorowany dla metod time-domain. Aktualizacja `parse_amplitude_method`, `_VALID_METHODS`, testów w `test_amplitude.py`. Harness/signal_amplitude przekazuje `config.band_ranges[norm.band]`.

#### 2. Harness artefaktów i amplitudy

**File**: `app/domain/signal_amplitude.py`, `app/domain/calibration/harness.py`

**Intent**: Logika obliczeń amplitudy (2-pass artefakty + redukcja metodą) w **`signal_amplitude.py`** — współdzielona przez harness offline i (w fazie 4) pipeline. `calibration/harness.py` to cienka warstwa: segmentacja + pętla po normach + wywołanie `signal_amplitude`.

**Contract**:
```python
@dataclass(frozen=True)
class SignalAmplitudeParams:
    amplitude_method: AmplitudeMethod
    reject_broadband_uv: float      # Pass 1, przed filtrem; 0 = wyłączony
    reject_filtered_uv: float       # Pass 2, po filtrze (obecne 200)
    epoch_seconds: float = 1.0
    min_clean_seconds: float = 30.0

LEGACY_PIPELINE_PARAMS = SignalAmplitudeParams(
    amplitude_method=AmplitudeMethod.MEAN_ABS,
    reject_broadband_uv=0.0,
    reject_filtered_uv=200.0,
    min_clean_seconds=0.0,
)

def compute_cell_amplitude(
    raw: mne.io.BaseRaw,
    norm: NormEntry,
    segments: dict[str, tuple[float, float]],
    config: NormsConfig,
    params: SignalAmplitudeParams,
) -> float: ...
```
- Pass 1: na sygnale broadband (po notch, przed bandpass) — odrzucanie okien pp > próg.
- Pass 2: na sygnale po bandpass — ta sama logika okien co `_mean_abs_after_artifact_rejection`.
- Po odrzuceniu: `compute_band_amplitude(clean_uv, sfreq, params.amplitude_method, band=...)`.
- `calibration/harness.py`: `compute_amplitudes(path, config, params)` → ładuje raw, `detect_task_segments`, pętla `compute_cell_amplitude`.

#### 3. Naprawa compare script

**File**: `scripts/compare_amplitude_methods.py`

**Intent**: Używać `compute_amplitudes()` z harness zamiast `run_pipeline()`; usunąć mylący docstring o działaniu przez `norms.json` w aplikacji.

**Contract**: CLI `--params` opcjonalnie; domyślnie lista metod × domyślne `CalibrationParams`. `ok_EEG.edf` i `Kuczyński.EEG` oznaczone jako pominięte / informacyjne w output (nie w scoringu).

#### 4. Testy harness

**File**: `tests/unit/test_calibration_harness.py`

**Intent**: Syntetyczny sygnał sinusoidalny — weryfikacja że Welch > mean_abs dla tego samego pasma; Pass 1 usuwa szpilki broadband.

**Contract**: Bez plików EDF w repo; opcjonalnie `@pytest.mark.integration` z `pytest.importorskip` gdy brak pliku ADHD na dysku.

### Success Criteria:

#### Automated Verification:

- Unit tests: `python -m pytest tests/unit/test_amplitude.py tests/unit/test_calibration_harness.py -q`
- mypy strict na `app/domain/amplitude.py` i `app/domain/calibration/`
- `compare_amplitude_methods.py` kończy bez crash na dostępnych plikach (exit 0)

#### Manual Verification:

- Harness na `ADHD_EEG.edf` z `welch_band_power` daje wyższe `NF/mean_z` niż `mean_abs` (kierunek zgodny z hipotezą)
- `depresja_EEG.edf` przechodzi przez harness przy co najmniej jednej kombinacji progów (nie tylko `artifact_rejection`)

**Implementation Note**: Manualne potwierdzenie depresja + Welch przed fazą 3.

---

## Phase 3: Sweep + wybór wariantu

### Overview

Skrypt grid search, raport CSV/stdout, wybór zwycięzcy wg odległości od centroidu „Wskazanie” + regresja rozkładu 82 profili.

### Changes Required:

#### 1. Skrypt kalibracji

**File**: `scripts/calibrate_against_expert_csv.py`

**Intent**: Główne narzędzie offline — sweep i ranking wariantów.

**Contract**:
- Grid (konfigurowalny, sensowne defaulty):
  - `AmplitudeMethod` — wszystkie w tym `welch_band_power`
  - `reject_broadband_uv`: 0, 100, 150, 200, 300
  - `reject_filtered_uv`: 100, 150, 200, 300
  - `min_clean_seconds`: 30, 60, 90
- Dla każdego wariantu:
  1. **EDF anchors:** profile ADHD + depresja przez harness → `profile_distance` do centroidu Wskazanie.
- Ranking: minimalna średnia odległość (ADHD + depresja) / 2; tie-break: mniejsza wariancja profilu, prostszy wariant (mniej agresywne progi).
- **Uwaga:** CSV (82 wiersze) służy wyłącznie do wyliczenia centroidów w fazie 1 — sweep **nie** modyfikuje amplitud CSV; brak per-wariant „regresji CSV”.
- Output: `reports/calibration_<timestamp>.md` lub stdout + opcjonalnie JSON w `scripts/output/`.
- **Wykluczone z scoringu:** `ok_EEG.edf`, `Kuczyński.EEG`.

#### 2. Dokumentacja wyniku

**File**: `context/changes/pipeline-expert-alignment/calibration-result.md` (generowany ręcznie po sweepie lub szablon w skrypcie)

**Intent**: Zapis wybranego wariantu, metryk odległości, uzasadnienie — input do fazy 4.

**Contract**: Sekcje: Winning Params, ADHD profile, depresja profile, distance to centroid, known limitations.

#### 3. Test smoke skryptu

**File**: `tests/unit/test_calibrate_script.py`

**Intent**: Mock harness + mini CSV — weryfikacja że grid produkuje ranking i nie crashuje.

**Contract**: `--max-combinations 2` flag do szybkiego testu CI.

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/test_calibrate_script.py -q`
- `python scripts/calibrate_against_expert_csv.py --max-combinations 4` (smoke) exit 0

#### Manual Verification:

- Pełny sweep lokalnie (z dostępem do danych) — raport wskazuje wariant z `NF/mean_z` bliżej ~0.6 niż ~0.2 dla Thety ADHD
- depresja w top-N wariantów (nie wyłącznie artifact_rejection)
- Akceptacja wyniku przez użytkownika przed fazą 4

**Implementation Note**: **Stop gate** — bez akceptacji raportu nie przechodzić do fazy 4.

---

## Phase 4: Integracja produkcyjna

### Overview

Przeniesienie zwycięskiej konfiguracji do `pipeline.run()`, testy regresji, aktualizacja dokumentacji i domyślnego `amplitude_method` w template (nie w produkcyjnym `norms.json` bez decyzji admina).

### Changes Required:

#### 1. Refaktor pipeline

**File**: `app/domain/pipeline.py`

**Intent**: Zastąpić inline `_mean_abs_after_artifact_rejection` wywołaniem `app/domain/signal_amplitude.py`. `config.amplitude_method` steruje redukcją.

**Contract**:
- `_amplitude_for_norm` deleguje do `signal_amplitude.compute_cell_amplitude(...)` — **nie** do `calibration.harness`.
- **Produkcyjne defaulty** = zwycięzca z `calibration-result.md` (nowy standard aplikacji).
- **`LegacyPipelineParams`** (mean_abs, reject_broadband=0, reject_filtered=200, min_clean_seconds=0) — wyłącznie do testów regresji wstecznej na fixture'ach syntetycznych (± tolerancja numeryczna).

#### 2. Normy template

**File**: `norms.json.template`

**Intent**: Udokumentować zwycięską `amplitude_method` i ewentualne nowe pola (`reject_broadband_uv`, `min_clean_seconds`) jeśli wchodzą do `NormsConfig`.

**Contract**: Pola opcjonalne z defaultami = zwycięzca; walidacja w `norms.py`.

#### 3. Testy integracyjne

**File**: `tests/integration/test_pipeline_fidelity.py`, `tests/unit/test_pipeline.py`

**Intent**: Test że zmiana metody zmienia wynik `run()`; syntetyka 15/25/35 µV w pasmach — łańcuch norms + classify.

**Contract**: `@pytest.mark.integration` dla EDF gdy dostępne; core w syntetyce.

#### 4. Dokumentacja segmentacji

**File**: `docs/EEG-segmentacja.md`

**Intent**: Dodać alias `ZADANIE POZNA` / `zadanie pozna` do listy ZP.

**Contract**: Jedna linia w tabeli aliasów.

#### 5. Status change

**File**: `context/changes/pipeline-expert-alignment/change.md`

**Intent**: `status: implemented` po merge; link do `calibration-result.md` i `plan.md`.

### Success Criteria:

#### Automated Verification:

- `python -m pytest -q`
- `mypy app/ --strict`
- `python -m app.main --validate-norms norms.json`

#### Manual Verification:

- `python tests/fixtures/probe_pipeline.py` na ADHD/depresja — amplitudy w skali norm (~10–30 µV Theta); profil `amp/mean_z` bliżej centroidu „Wskazanie” niż baseline (~0.2); kategoria RAG **informacyjna** (nie gate akceptacji — zgodnie z decyzją planowania: priorytet = skala/profil Mitsar)
- Brak regresji na istniejących testach jednostkowych pipeline

**Implementation Note**: Manualna weryfikacja na EDF przed zamknięciem change.

---

## Testing Strategy

### Unit Tests

- CSV parser: przecinek dziesiętny, 10 kolumn, błędne nagłówki
- Centroidy: znane mini-CSV → oczekiwane mediany profili
- `welch_band_power`: sinus w paśmie Theta → wyższa amplituda niż noise
- Harness: Pass 1 usuwa okno ze szpilkiem; min_clean_seconds odrzuca segment
- Pipeline po integracji: `amplitude_method` w config zmienia output

### Integration Tests

- Pełny łańcuch: syntetyczny Raw → `run()` → `classify()` → kategoria
- Opcjonalnie EDF ADHD/depresja gdy pliki obecne (skip w CI)

### Manual Testing Steps

1. Faza 1: load CSV → wydruk centroidów (Wskazanie ≈ 0.63)
2. Faza 2: harness ADHD — porównaj mean_abs vs welch
3. Faza 3: pełny sweep → review raportu
4. Faza 4: probe_pipeline ADHD/depresja → RAG i skala µV

## Performance Considerations

- Pełny grid (~5 metod × 5 × 4 × 3 ≈ 300 kombinacji) × 2 EDF ≈ 600 runów — akceptowalne offline (minuty). Flaga `--max-combinations` i `--methods` do ograniczenia.
- Welch wolniejszy od mean_abs — OK dla skryptu offline; w produkcji jeden wariant na analizę (~10 komórek × 3 segmenty).

## Migration Notes

- Produkcyjny `norms.json` u klientów: **bez automatycznej zmiany** pól kalibracji — admin aktualizuje ręcznie po weryfikacji klinicznej. **Kod aplikacji** po fazie 4 używa zwycięskich defaultów nawet bez nowych pól w norms (breaking change behawioralny — amplitudy i kolory mogą się zmienić).
- Testy regresji wstecznej używają `LegacyPipelineParams`, nie produkcyjnych defaultów.
- Branch `experiment/pipeline-amplitude-calibration` → PR do głównej linii dev po fazie 4.
- Docs z `coursor/dev-env-setup-2f65` już zsynchronizowane w folderze change.
- **Commity fazowe** (reguła z `lessons.md`): stage wyłącznie touched-set bieżącej zmiany + `plan.md` — bez `git add -A`; nie commitować `_tmp_*.txt`, `history.db`, innych change folderów.

## References

- Strategia offline: `context/changes/pipeline-expert-alignment/offline-calibration-plan.md`
- Research: `context/changes/pipeline-expert-alignment/research.md`
- Handoff: `context/changes/pipeline-expert-alignment/handoff.md`
- Pipeline amplitude: `app/domain/pipeline.py:315-387`
- WIP amplitude methods: `app/domain/amplitude.py`
- Ekspert CSV: `D:\CVGOSI\NF dane\analiza eeg\wyniki_indywidualne.csv`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands.

### Phase 1: Fundament kalibracji (CSV + centroidy)

#### Automated

- [x] 1.1 Unit tests pass: `python -m pytest tests/unit/test_calibration_csv.py -q` — ce6d68d
- [x] 1.2 Type checking passes: `mypy app/domain/calibration/ --strict` — ce6d68d
- [x] 1.3 Full suite green: `python -m pytest -q` — ce6d68d

#### Manual

- [x] 1.4 Smoke load 82 CSV rows and print centroids (Wskazanie ≈ 0.63) — ce6d68d

### Phase 2: Harness offline + Welch/PSD

#### Automated

- [x] 2.1 Unit tests: `python -m pytest tests/unit/test_amplitude.py tests/unit/test_calibration_harness.py -q` — 934efc7
- [x] 2.2 mypy strict on amplitude + calibration modules — 934efc7
- [x] 2.3 `compare_amplitude_methods.py` exits 0 on available files — 934efc7

#### Manual

- [x] 2.4 Harness ADHD: welch_band_power yields higher NF/mean_z than mean_abs — 934efc7
- [x] 2.5 depresja_EEG passes harness with at least one threshold combo — 934efc7

### Phase 3: Sweep + wybór wariantu

#### Automated

- [x] 3.1 `python -m pytest tests/unit/test_calibrate_script.py -q`
- [x] 3.2 Smoke: `calibrate_against_expert_csv.py --max-combinations 4` exit 0

#### Manual

- [x] 3.3 Full local sweep report — top variant NF/mean_z ~0.6 for Theta ADHD
- [x] 3.4 User accepts calibration report before Phase 4

### Phase 4: Integracja produkcyjna

#### Automated

- [ ] 4.1 `python -m pytest -q`
- [ ] 4.2 `mypy app/ --strict`
- [ ] 4.3 `python -m app.main --validate-norms norms.json`

#### Manual

- [ ] 4.4 probe_pipeline ADHD/depresja — amplitudes in norm scale, profile near Wskazanie centroid (RAG category informational only)
- [ ] 4.5 No regression on existing pipeline unit tests
