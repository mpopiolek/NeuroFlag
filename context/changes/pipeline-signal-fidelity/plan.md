# Pipeline Signal Fidelity — Implementation Plan

## Overview

Faza 2 planu testowego NeuroFlag (`context/foundation/test-plan.md` §3): testy fidelity sygnału w pipeline EEG oraz poprawki produkcyjne ujawnione przez te testy.

Dwa ryzyka:
- **R4** — Pipeline nie niszczy sygnału; obecny `test_run_returns_ten_finite_amplitudes` akceptuje dowolną skończoną wartość (w tym ~0 µV)
- **R5** — Segment detection na realnym DigiTrack bez tekstowych znaczników; fallback 3×3 min musi działać bez `PipelineError`, a `run()` musi zwracać 10 skończonych amplitud

Decyzje z sesji planowania: testy w `tests/integration/`, rozszerzona `sample_digitrack.eeg` (≥8 min), asercje R4 dokładnie `(5.0, 200.0) µV`, test bramy 200 µV, `run()` smoke na fixture DigiTrack z poprawką kalibracji jeśli potrzeba, poprawki pipeline gdy test je ujawnią.

## Current State Analysis

`tests/unit/test_pipeline.py` (17 testów) pokrywa segmentację syntetycznie — w tym fallback 3×3 min na `RawArray` bez adnotacji — ale **nie** ładuje pliku DigiTrack. `test_run_returns_ten_finite_amplitudes` mockuje `_load_raw` i asertuje wyłącznie `len == 10` oraz `isfinite` (`tests/unit/test_pipeline.py:217–223`).

`tests/fixtures/sample_digitrack.eeg` ma **2500 próbek** (10 s @ 250 Hz) — za krótki na `detect_task_segments()` wymagające ≥480 s (`app/domain/pipeline.py:27–28`). Używany tylko w `test_eeg_file.py` (reader, nie pipeline).

Brak katalogu `tests/integration/`. Research (`context/archive/2026-06-30-testing-critical-path-domain/research.md`) wskazuje trzy realne przyczyny all-red poza „agresywnym czyszczeniem”:
1. DC offset / flat-line → post-filter ~0 µV (jakość nagrania)
2. Segment ZP skrócony przez wczesny marker `"Artefakt"` (6.5 s) → filtr MNE niestabilny
3. DigiTrack: amplitudy 5–15× za niskie vs normy — możliwa błędna kalibracja w `read_raw_digitrack()`

Brama artefaktów to jedynie `drop_bad(reject={"eeg": 200e-6})` (`pipeline.py:30, 337`) — odrzucenie zawsze rzuca `PipelineError("artifact_rejection")`, nie produkuje cicho niskich amplitud.

## Desired End State

Po ukończeniu planu:
1. `tests/integration/test_pipeline_fidelity.py` zawiera testy R4 (zachowanie amplitudy na syntetyku 50 µV) i R5 (fallback DigiTrack + smoke `run()`).
2. `tests/fixtures/sample_digitrack.eeg` ma ≥480 s nagrania (≥120 000 bloków @ 250 Hz), commitowana w repo.
3. Test bramy 200 µV potwierdza widoczny błąd przy amplitudzie >200 µV p-p.
4. Poprawki w `pipeline.py` i/lub `eeg_file.py` zamykają regresje ujawnione testami (min. kalibracja DigiTrack jeśli smoke `run()` zwraca nieskończone lub zerowe wartości; ewentualnie minimalna długość segmentu ZP przy wczesnym `"Artefakt"`).
5. `python -m pytest -q` i `mypy app/ --strict` przechodzą.

### Key Discoveries:

- `_REJECT_EEG_VOLTS = 200e-6` — jedyny próg artefaktów; brak ICA/autoreject (MVP locked w S-02)
- `detect_task_segments()` → fallback gdy **zero** rozpoznanych markerów; partial markers → `missing_task_segments` (`pipeline.py:236–248`)
- DigiTrack zawsze trafia w fallback (stub `_digitrack_annotations()` → `None`) — to **oczekiwane**, nie błąd
- Fixture syntetyczny używa 50 µV sinus @ 6 Hz — poniżej progu 200 µV, nadaje się jako oracle R4
- `real_norms_config` fixture już istnieje w `tests/conftest.py`

## What We're NOT Doing

- Brak testów wewnętrznych filtrów MNE (notch, FIR vs IIR) — `test-plan.md` §7
- Brak UI, ostrzeżenia użytkownika przy fallback 3×3 min (poza scope — wybrano `tests_plus_fixes`, nie `tests_plus_ui`)
- Brak Fazy 3 test-planu (R2/R6 malformed files) — osobny change
- Brak dekodowania binarnych markerów DigiTrack (`_digitrack_annotations` stub)
- Brak zmiany progu 200 µV bez klinicznej decyzji
- Brak commitowania surowych plików pacjentów — tylko anonimizowana fixture

## Implementation Approach

1. **Najpierw fixture** — bez ≥8 min DigiTrack nie da się testować R5 na realnym formacie.
2. **Potem testy R4** — najtańszy sygnał dla ryzyka „pipeline niszczy amplitudę”; reuse helpera `_synthetic_raw_with_annotations()` (wyekstrahować do współdzielonego modułu testowego lub skopiować minimalnie).
3. **Testy R5 + smoke run()** — na rozszerzonej fixture; jeśli amplitudy za niskie, naprawić kalibrację w `read_raw_digitrack()` w tej samej fazie.
4. **Poprawki segmentacji** — jeśli test ZP/`"Artefakt"` ujawni skrócony segment poniżej progu filtra, naprawić logikę końca segmentu w `_segments_from_annotations` / `_annotation_segment_end`.

## Critical Implementation Details

- **Regeneracja fixture wymaga lokalnego źródła** — `generate_digitrack_fixture.py` czyta `D:/CVGOSI/NF dane/Testowe/Kuczyński.EEG`. CI polega na **commitowanej** rozszerzonej fixture; skrypt aktualizuje `TARGET_BLOCKS` (min. `120_000` dla 8 min), implementer regeneruje ręcznie przed commitem.
- **Rozmiar pliku** — 8 min × 19 kanałów × 2 B ≈ 1.8 MB danych + nagłówek; akceptowalne dla repo (skrypt ostrzega przy >200 KB dla starego 10 s wycinka).
- **IIR vs FIR** — segmenty fallback mają 180 s (>4096 próbek @ 250 Hz) → ścieżka FIR; test ZP skrócony do <16 s wymaga osobnego unit testu tylko jeśli poprawka segmentacji go wymusi.

---

## Phase 1: Extended DigiTrack Fixture + Integration Scaffold

### Overview

Rozszerza `sample_digitrack.eeg` do ≥8 min i tworzy szkielet `tests/integration/test_pipeline_fidelity.py` z markerami pytest oraz wspólnymi helperami.

### Changes Required:

#### 1. Generator fixture — dłuższe nagranie

**File**: `tests/fixtures/generate_digitrack_fixture.py`

**Intent**: Umożliwić wygenerowanie commitowanej fixture DigiTrack wystarczająco długiej na `_require_recording_duration()` i fallback 3×3 min.

**Contract**: `TARGET_BLOCKS` ≥ `120_000` (480 s @ 250 Hz). Zaktualizować docstring (linie 6–9) z nowym rozmiarem (~1–2 MB). Zachować anonimizację PII i logikę `n_ch_data`.

#### 2. Commit rozszerzonej fixture

**File**: `tests/fixtures/sample_digitrack.eeg`

**Intent**: Dostarczyć realny binarny plik DigiTrack do CI bez zależności od lokalnej ścieżki pacjenta.

**Contract**: Plik binarny ≥480 s po `read_raw_digitrack()`; PII wyzerowane. Regeneracja: `python tests/fixtures/generate_digitrack_fixture.py` (manualnie, poza CI).

#### 3. Aktualizacja testów readera

**File**: `tests/unit/test_eeg_file.py`

**Intent**: Dopasować asercje shape/duration do nowej długości fixture (obecnie `(19, 2500)`).

**Contract**: Testy `test_read_raw_digitrack_data_shape` i powiązane — oczekiwany `n_times` ≥ `120_000` (lub dokładna wartość z nowej fixture).

#### 4. Szkielet integration

**File**: `tests/integration/test_pipeline_fidelity.py`

**Intent**: Nowy moduł testów fidelity z `pytest.importorskip("mne")`, importem `real_norms_config`, stałą ścieżką do fixture (`Path(__file__).resolve().parents[1] / "fixtures" / "sample_digitrack.eeg"`), `@pytest.mark.skipif(not FIXTURE.exists())`.

**Contract**: Plik importowalny przez pytest; na końcu Phase 1 może zawierać placeholder `test_fixture_duration_at_least_eight_minutes` asertujący `raw.times[-1] >= 480.0` po `read_raw_digitrack(FIXTURE)`.

#### 5. `.gitignore` / dokumentacja fixture

**File**: `tests/fixtures/generate_digitrack_fixture.py` (docstring), ewentualnie komentarz w `MANUAL-QA.md` jeśli wspomina 10 s

**Intent**: Usunąć mylące odniesienia do 10 s / 137 KB jako docelowej długości R5.

**Contract**: Docstring opisuje ≥8 min i procedurę regeneracji.

### Success Criteria:

#### Automated Verification:

- Reader tests: `python -m pytest tests/unit/test_eeg_file.py -v -k digitrack`
- Integration scaffold: `python -m pytest tests/integration/test_pipeline_fidelity.py -v`
- Typy: `mypy app/ --strict`
- Pełna suite: `python -m pytest -q`

#### Manual Verification:

- `sample_digitrack.eeg` istnieje w repo i `read_raw_digitrack()` zwraca ≥480 s
- Rozmiar pliku rozsądny (<5 MB) — nie commitować pełnego 22-min nagrania bez potrzeby

**Implementation Note**: Po automated verification poczekaj na potwierdzenie, że fixture została wygenerowana i commitowana, zanim przejdziesz do Phase 2.

---

## Phase 2: R4 — Amplitude Preservation + Artifact Gate

### Overview

Testy integracyjne potwierdzające, że pipeline na czystym syntetycznym sygnale 50 µV zwraca amplitudy w oczekiwanym zakresie, oraz że segment >200 µV p-p kończy się `artifact_rejection`, nie cichymi zerami.

### Changes Required:

#### 1. Współdzielony helper syntetycznego Raw (opcjonalny extract)

**File**: `tests/integration/test_pipeline_fidelity.py` (lub `tests/helpers/synthetic_eeg.py` jeśli extract zmniejszy duplikację)

**Intent**: Dostarczyć `RawArray` 600 s, C3/O1, adnotacje OO/OZ/ZP @ 0/180/360 s, sinus 50 µV @ częstotliwości pokrywającej pasma (min. 6 Hz dla Theta) — ten sam kontrakt co `_synthetic_raw_with_annotations()` w `test_pipeline.py`.

**Contract**: Helper zwraca `mne.io.BaseRaw` gotowy do `@patch("app.domain.pipeline._load_raw")` lub bezpośredniego wywołania `_amplitude_for_norm` / `run()`.

#### 2. Test granic amplitudy po `run()`

**File**: `tests/integration/test_pipeline_fidelity.py`

**Intent**: Zamienić anty-wzorzec `isfinite`-only na oracle z `test-plan.md` R4: każda z 10 amplitud w `(5.0, 200.0) µV`.

**Contract**: `test_run_preserves_amplitude_bounds_on_clean_synthetic` — patch `_load_raw`, `run(Path("synthetic.edf"), real_norms_config)`, asercje: `len == 10`, `all(5.0 < v < 200.0 for v in result)`.

#### 3. Test bramy 200 µV

**File**: `tests/integration/test_pipeline_fidelity.py`

**Intent**: Udowodnić, że odrzucenie artefaktu jest widoczne (R4 reframing — gate nie produkuje all-red cicho).

**Contract**: `test_run_raises_artifact_rejection_when_segment_exceeds_200_uv` — syntetyczny Raw z amplitudą >200 µV p-p w jednym segmencie (np. 300 µV sinus) → `pytest.raises(PipelineError)` z `exc_info.value.code == "artifact_rejection"`.

#### 4. Wzmocnienie istniejącego unit testu (opcjonalnie, minimalny diff)

**File**: `tests/unit/test_pipeline.py`

**Intent**: Oznaczyć `test_run_returns_ten_finite_amplitudes` jako słaby smoke lub dodać komentarz odnoszący do integration test — **bez** duplikowania pełnych boundów w unit (single source: integration).

**Contract**: Komentarz `# fidelity bounds: see tests/integration/test_pipeline_fidelity.py` — bez zmiany asercji unit (unikamy podwójnej konserwacji).

### Success Criteria:

#### Automated Verification:

- R4 tests: `python -m pytest tests/integration/test_pipeline_fidelity.py -v -k "amplitude_bounds or artifact_rejection"`
- Pełna suite: `python -m pytest -q`
- Mypy: `mypy app/ --strict`

#### Manual Verification:

- Przy failu boundów — sprawdzić czy problem to filtr MNE vs jednostki; nie obniżać progów bez uzasadnienia

**Implementation Note**: Po automated verification poczekaj na ręczne potwierdzenie przed Phase 3.

---

## Phase 3: R5 — DigiTrack Fallback + run() Smoke

### Overview

Testy na rozszerzonej `sample_digitrack.eeg`: poprawna struktura fallback 3×3 min oraz smoke `run()` zwracający 10 skończonych amplitud.

### Changes Required:

#### 1. Test struktury fallback na fixture DigiTrack

**File**: `tests/integration/test_pipeline_fidelity.py`

**Intent**: R5 — plik bez rozpoznanych markerów zadań używa fallback, nie `PipelineError`.

**Contract**: `test_digitrack_detect_task_segments_uses_fallback_3x3` — `raw = read_raw_digitrack(FIXTURE)`, `normalize_channel_names` + pick C3/O1 jeśli wymagane przed segmentacją (lub pełna ścieżka jak w `run()`), `segments = detect_task_segments(raw)`, asercje: klucze OO/OZ/ZP, `OO == (0.0, 180.0)`, `OZ == (180.0, 360.0)`, `ZP[0] == 360.0`, `ZP[1]` ≈ min(540, total) z tolerancją 0.01 s.

#### 2. Smoke `run()` na fixture

**File**: `tests/integration/test_pipeline_fidelity.py`

**Intent**: End-to-end load DigiTrack → 10 amplitud skończonych (bez wymagania boundów 5–200 µV na realnym pliku — kalibracja może wymagać poprawki w Phase 4).

**Contract**: `test_digitrack_run_returns_ten_finite_amplitudes` — `run(FIXTURE, real_norms_config)`, `len == 10`, `all(np.isfinite(v) for v in result)`.

#### 3. Test: brak markerów → nie `missing_task_segments`

**File**: `tests/integration/test_pipeline_fidelity.py`

**Intent**: Dokumentuje decyzję produktową — zero markerów to fallback, nie błąd.

**Contract**: `test_digitrack_has_no_task_annotations` — po load, `_collect_task_markers(raw)` (import prywatny dozwolony w teście integracyjnym lub assert przez publiczne API fallback) potwierdza pustą listę markerów zadań.

### Success Criteria:

#### Automated Verification:

- R5 tests: `python -m pytest tests/integration/test_pipeline_fidelity.py -v -k digitrack`
- Pełna suite: `python -m pytest -q`

#### Manual Verification:

- Jeśli `run()` zwraca wartości bliskie 0 — przejść do Phase 4 (kalibracja), nie osłabiać asercji smoke

**Implementation Note**: Po automated verification poczekaj na potwierdzenie przed Phase 4.

---

## Phase 4: Production Fixes Driven by Tests

### Overview

Naprawia regresje ujawnione przez Phase 2–3. Zakres konkretny zależy od wyników testów — poniżej obowiązkowe kandydaty z research.

### Changes Required:

#### 1. Kalibracja DigiTrack (jeśli smoke/run lub bound test fail)

**File**: `app/domain/eeg_file.py` — `read_raw_digitrack()`

**Intent**: Amplitudy z DigiTrack muszą być w skali µV zgodnej z normami — research wykazał 5–10 µV broadband vs oczekiwane 50–150 µV.

**Contract**: Po poprawce, `test_digitrack_run_returns_ten_finite_amplitudes` przechodzi; opcjonalnie rozszerzyć smoke o `any(v > 1.0 for v in result)` jeśli kalibracja potwierdzona. Nie zmieniać API publicznego readera poza skalą danych zwracanych w `RawArray`.

#### 2. Minimalna długość segmentu ZP przy wczesnym markerze `"Artefakt"` (jeśli dodany test ujawni regresję)

**File**: `app/domain/pipeline.py` — `_annotation_segment_end()` / `_segments_from_annotations()`

**Intent**: Segment ZP skrócony do kilku sekund przez `"Artefakt"` tuż po starcie ZP powoduje niestabilny filtr i post-µV ≈ 0 mimo poprawnego sygnału (przypadek `260116_000791_EEGok.edf` w research).

**Contract**: Gdy następna adnotacja po ZP jest na liście markerów kończących (`"Artefakt"`, `"Czynność podstawowa"`) i odległość < `_MIN_ANNOTATION_DURATION_S` lub < próg filtra (~16 s), stosować `_DEFAULT_SEGMENT_SECONDS` (180 s) lub koniec nagrania — zgodnie z `docs/EEG-segmentacja.md`. Dodać unit test w `test_pipeline.py` odwzorowujący scenariusz EDF: OO/OZ/ZP @ ~157/306/459 s, `"Artefakt"` @ 465.6 s → ZP trwa ≥ min(180 s, do końca nagrania minus onset) lub inna uzgodniona reguła dokumentowana w teście.

#### 3. Aktualizacja `test-plan.md` cookbook Faza 2

**File**: `context/foundation/test-plan.md` §6 (Faza 2)

**Intent**: Zamienić TBD na odnośnik do tego change po implementacji.

**Contract**: Wiersz status Faza 2 → `implemented`; cookbook wskazuje `tests/integration/test_pipeline_fidelity.py`.

### Success Criteria:

#### Automated Verification:

- Wszystkie testy integration: `python -m pytest tests/integration/ -v`
- Unit pipeline (w tym nowy test ZP/Artefakt jeśli dodany): `python -m pytest tests/unit/test_pipeline.py -v`
- Mypy: `mypy app/ --strict`
- Pełna suite: `python -m pytest -q`

#### Manual Verification:

- Uruchomić `python tests/fixtures/probe_pipeline.py` (jeśli dostępne lokalnie) na rozszerzonej fixture — wynik nie jest wyłącznie 10× RED z powodu zerowych amplitud po filtracji
- Potwierdzić, że poprawki nie łamią istniejących testów segmentacji (OO/OZ/ZP z adnotacjami)

**Implementation Note**: Phase 4 kończy change — po automated + manual verification zaktualizuj `change.md` status na `implemented`.

---

## Testing Strategy

### Unit Tests:

- Istniejące testy segmentacji w `test_pipeline.py` — bez regresji
- Nowy test ZP/`"Artefakt"` (Phase 4) — scenariusz z research EDF
- `test_eeg_file.py` — zaktualizowane wymiary fixture

### Integration Tests:

- R4: bound 5–200 µV + artifact_rejection
- R5: DigiTrack fallback structure + run() smoke

### Manual Testing Steps:

1. Regeneruj fixture lokalnie jeśli brakuje w working copy
2. `python -m pytest tests/integration/test_pipeline_fidelity.py -v`
3. Opcjonalnie: probe na fixture DigiTrack — kategoria ≠ wyłącznie WSKAZANIE z powodu zer

## Performance Considerations

Integration testy ładują MNE i filtrują 10 pasm — wolniejsze niż unit, ale akceptowalne (<30 s łącznie). Fixture ~2 MB zwiększa rozmiar repo jednorazowo. Session fixture `real_norms_config` ładuje norms raz.

## Migration Notes

Brak migracji danych użytkownika. Istniejący `sample_digitrack.eeg` w forkach wymaga pull nowej wersji; testy readera zaktualizowane do nowego `n_times`.

## References

- Test plan Faza 2: `context/foundation/test-plan.md:57, 92–94`
- Research R4/R5: `context/archive/2026-06-30-testing-critical-path-domain/research.md`
- MVP pipeline: `context/archive/2026-06-03-eeg-pipeline-and-results/plan.md`
- Segmentacja: `docs/EEG-segmentacja.md`
- Pipeline: `app/domain/pipeline.py`
- DigiTrack reader: `app/domain/eeg_file.py`
- Istniejące testy: `tests/unit/test_pipeline.py:217–223`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: Extended DigiTrack Fixture + Integration Scaffold

#### Automated

- [x] 1.1 Reader tests: `python -m pytest tests/unit/test_eeg_file.py -v -k digitrack` — 2db6eb7
- [x] 1.2 Integration scaffold: `python -m pytest tests/integration/test_pipeline_fidelity.py -v` — 2db6eb7
- [x] 1.3 Typy: `mypy app/ --strict` — 2db6eb7
- [x] 1.4 Pełna suite: `python -m pytest -q` — 2db6eb7

#### Manual

- [x] 1.5 `sample_digitrack.eeg` w repo — `read_raw_digitrack()` ≥480 s; rozmiar <5 MB — 2db6eb7

### Phase 2: R4 — Amplitude Preservation + Artifact Gate

#### Automated

- [x] 2.1 R4 tests: `python -m pytest tests/integration/test_pipeline_fidelity.py -v -k "amplitude_bounds or artifact_rejection"` — 63a826b
- [x] 2.2 Pełna suite: `python -m pytest -q` — 63a826b
- [x] 2.3 Mypy: `mypy app/ --strict` — 63a826b

#### Manual

- [x] 2.4 Przy failu boundów — diagnoza filtr/jednostki bez obniżania progów — 63a826b

### Phase 3: R5 — DigiTrack Fallback + run() Smoke

#### Automated

- [x] 3.1 R5 tests: `python -m pytest tests/integration/test_pipeline_fidelity.py -v -k digitrack`
- [x] 3.2 Pełna suite: `python -m pytest -q`

#### Manual

- [x] 3.3 Wartości bliskie 0 → Phase 4 kalibracja, nie osłabianie smoke

### Phase 4: Production Fixes Driven by Tests

#### Automated

- [ ] 4.1 Wszystkie testy integration: `python -m pytest tests/integration/ -v`
- [ ] 4.2 Unit pipeline: `python -m pytest tests/unit/test_pipeline.py -v`
- [ ] 4.3 Mypy: `mypy app/ --strict`
- [ ] 4.4 Pełna suite: `python -m pytest -q`

#### Manual

- [ ] 4.5 Probe/fixture — brak wyłącznie zer po filtracji; segmentacja adnotacji nietknięta
