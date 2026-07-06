---
project: "NeuroFlag"
created: 2026-06-30
updated: 2026-07-06
status: active
---

# Plan Testów: NeuroFlag

## §1 Strategia

### Zasada 1 — Koszt × sygnał

Każdy test dodany przez ten rollout — klasyczny lub AI-natywny — musi odpowiedzieć na jedno pytanie: *jaki jest najtańszy test, który daje realny sygnał dla tego ryzyka?* Nie promuj do e2e dlatego, że „tak jest bezpieczniej"; nie nakładaj modelu wizyjnego na deterministyczny diff, który już wyłapuje regresję. Przekazuj tę zasadę do `/10x-plan` dla każdej fazy rollout.

### Zasada 2 — Obawy użytkownika są dowodem

Ryzyka, przez które zespół już przeszedł, mają taką samą wagę jak linie PRD lub dane hot-spot. Realne obserwacje (np. "pliki pacjentów ze wskazaniami pokazują wyłącznie czerwone") mają wyższy priorytet niż spekulacje.

### Zasada 3 — Sygnał, nie wiedza (zasada graniczna)

Ten plan czyta bazę kodu pod kątem *sygnału* — hot-spot churn, profil bazy testów, marker projektu, język/framework. **Nie** czyta pod kątem *wiedzy* — call graph, schematy, tłumaczenie błędów, który wiersz posiada awarię. Kolumna §2 Source cytuje dowody (linie PRD, odpowiedzi z wywiadu, hot-spot directories); **nigdy** nie asertuje pliku jako „miejsca awarii." To jest domena `/10x-research` uruchamianego per faza rollout.

---

## §2 Mapa ryzyk

### Ryzyka domenowe

| # | Ryzyko (scenariusz awarii) | Wpływ | Prawdopodobieństwo | Źródło (dowody — nie anchory) |
|---|---|---|---|---|
| R1 | Algorytm trójstanowy produkuje błędną kategorię na granicy progów przy realnych wartościach norms.json (np. 5 czerwonych + 4 zielone → WSKAZANIE czy OBSERWACJA?) | HIGH | MEDIUM | Wywiad Q1; `test_algorithm.py` używa mocków mean_z/mean_k zamiast realnych norm; hot-spot dir `app/domain/` |
| R2 | Plik DigiTrack (.EEG) z zerową kalibracją lub uciętym nagłówkiem wczytany bez błędu; pipeline działa na śmieciowych danych, wynik wyłącznie czerwony | HIGH | HIGH | Wywiad Q1/Q2; hot-spot dir `app/domain/` (eeg_file.py ×5, 30d); change eegdigitrack-native-reader (plan-brief.md: "kalibracja = 0 → EEGFileError") |
| R3 | Podmieniony norms.json z nieprawidłowym schematem (brakujące pola, złe typy, < 10 norm) wczytany cicho bez błędu — obliczenia na błędnych normach | HIGH | MEDIUM | Wywiad Q1; hot-spot dir `app/domain/` (norms.py ×7, 30d); S-04 zaimplementowane, ale obawy nadal zgłaszane przez użytkownika |
| R4 | Zbyt agresywne czyszczenie artefaktów usuwa sygnał EEG razem z szumem → amplitudy bliskie zeru → wszystkie komórki czerwone (fałszywe WSKAZANIE) | HIGH | HIGH | Wywiad Q2 — realne pliki pacjentów pokazują wyłącznie czerwone; hot-spot dir `app/domain/` (pipeline.py ×8, 30d) |
| R5 | `detect_task_segments()` nie rozpoznaje aliasów z realnego pliku (opis spoza listy aliasów) → fallback 3×3 min używany cicho → błędne segmenty → błędne amplitudy | HIGH | HIGH | Wywiad Q2/Q4; hot-spot dir `app/domain/` (pipeline.py ×8, 30d); testy pokrywają tylko syntetyczne aliasy |
| R6 | Malformed plik (EDF, .vhdr, DigiTrack z losowymi bajtami lub zerowym nagłówkiem) powoduje nieobsłużony wyjątek zamiast czytelnego komunikatu błędu | MEDIUM | LOW | PRD §US-01 AC: „jeśli plik jest nieobsługiwany lub uszkodzony, użytkownik widzi czytelny komunikat błędu (nie crash)" |

### Wskazówki dotyczące odpowiedzi na ryzyka

| # | Co by udowodniło ochronę | Nie akceptuj cicho | Kontekst potrzebny `/10x-research` | Najtańsza warstwa | Anty-wzorzec do uniknięcia |
|---|---|---|---|---|---|
| R1 | Załadowany realny norms.json + amplitudy ±epsilon od prawdziwych mean_z i mean_k → poprawna kategoria (WSKAZANIE/BRAK/OBSERWACJA) | „Testy z mockami mean_z/mean_k=10.0/20.0 wystarczą" | Dokładne wartości mean_z/mean_k z norms.json, stała `_EPSILON`, reguły `RecommendationRules` z realnego pliku | Unit test z realnym norms.json i boundary amplitudes | Użycie syntetycznych norm zamiast realnych — oracle z mocka, nie z wymagań |
| R2 | Plik z zerową kalibracją, uciętym nagłówkiem lub błędną liczbą kanałów → `EEGFileError` z kodem diagnostycznym | „`_is_digitrack()` zwraca True = plik jest poprawny" | Warianty błędnych plików DigiTrack: zero kalibracja, truncated header, n_ch mismatch; co rzuca `read_raw_digitrack()` | Unit test z crafted binary fixture (złe bajty w nagłówku) | Tylko testy z known-good fixture; brak testu błędnych wariantów |
| R3 | norms.json z brakującymi polami, złymi typami lub < 10 normami → wyjątek `ValueError` / `ValidationError` przy `load()` z user-facing message | „Jeśli plik parsuje się do JSON, schemat jest poprawny" | Schemat walidacji w `norms.py` (`load()`), które pola są wymagane vs. opcjonalne, czy typy są sprawdzane | Parametryzowane unit testy z invalid JSON samples (brakujące pola, zły typ, 9 norm) | Tylko test poprawnego pliku + całkowicie pustego — pomijanie przypadków częściowych |
| R4 | Sygnał syntetyczny o znanych amplitudach (50 µV per pasmo) → `pipeline.run()` → amplitudy wyjściowe w oczekiwanym zakresie (>5 µV, <200 µV) dla każdego z 10 okien | „10 finite values zwrócone = pipeline działa poprawnie" | Próg artifact rejection (µV), konfiguracja ICA lub progowego usuwania artefaktów, jakie amplitudy powinny przeżyć filtrację | Integration test: synthetic EEG → `run()` → `assert min_amplitude > 5.0` per każde z 10 okien | Asercja tylko na `isfinite(v)` — obecny `test_run_returns_ten_finite_amplitudes` to właśnie robi; 0.0001 jest finite |
| R5 | Plik DigiTrack bez czytelnych etykiet → `detect_task_segments()` → fallback z strukturą 3×3 min, NIE `PipelineError` | „Brak match aliasów = PipelineError" — może nie; może cichy fallback | Dokładna gałąź: brak match → `_fallback_segments()` vs `PipelineError`; realny plik `.EEG` jako fixture | Unit test z realną fixture DigiTrack (brak adnotacji tekstowych) + assert na strukturę fallback segmentów | Tylko testy z syntetycznymi `OO`/`OZ`/`ZP` annotacjami |
| R6 | Plik z losowymi bajtami lub złym rozszerzeniem → czytelny `PipelineError`/`EEGFileError` z user-facing message, nie nagi traceback | „`mne.io.read_raw_edf()` samo łapie wszystkie błędy parsowania" | Łańcuch error handling w `_load_raw()`, które wyjątki MNE przepuszcza bez wrap'owania | Unit test z `os.urandom(1024)` zapisanym jako `.edf` | Przechwytywanie tylko `mne` exceptions — pomijanie błędów parsowania binarnego poza MNE |

---

## §3 Fazy rollout

| # | Faza | Cel (co chroni) | Ryzyka | Typy testów | Status | Change folder |
|---|---|---|---|---|---|---|
| 1 | Pokrycie krytycznej ścieżki domenowej | Algorytm trójstanowy i walidacja norms.json nie produkują błędnych wyników przy realnych wartościach i granicach progów | R1, R3 | Unit (boundary + schema validation) | change opened | context/changes/testing-critical-path-domain/ |
| 2 | Fidelity sygnału pipeline | Pipeline nie niszczy sygnału; segment detection działa na realnych plikach bez czytelnych etykiet | R4, R5 | Integration (synthetic EEG + real DigiTrack fixture) | implemented | context/changes/pipeline-signal-fidelity/ |
| 3 | Hardening obsługi błędnych danych wejściowych | Malformed i corrupted pliki produkują user-facing errors, nie nieobsłużone wyjątki | R2, R6 | Unit + integration (crafted bad files) | not started | — |

---

## §4 Stack i narzędzia

**Stack testowy:**
- Język: Python 3.11 (CI), lokalnie 3.12+
- Test runner: pytest 8.3.4 (skonfigurowany, `testpaths = ["tests"]`, `addopts = "-q"`)
- Typing: mypy 1.13.0 `--strict` (uruchamiane przed commitem per `AGENTS.md`)
- Linter: ruff ≥0.4.0
- Importowanie MNE: `mne = pytest.importorskip("mne")` — wzorzec ten musi być zachowany we wszystkich nowych testach
- Fixtures dostępne: `tests/fixtures/sample_digitrack.eeg` (~4.4 MB, 8 min @ 250 Hz, anonimizowany nagłówek)

**Profil bazy testów:** pytest skonfigurowany; `tests/unit/` + `tests/integration/test_pipeline_fidelity.py` (R4/R5). Brak testów warstwy UI.

**Stack grounding tools (current session):**
- Docs: none — brak Context7 / framework docs MCP w bieżącej sesji; checked: 2026-06-30
- Search: none — brak Exa.ai / web search MCP w bieżącej sesji; checked: 2026-06-30
- Runtime/browser: cursor-ide-browser — dostępny, nie używany (brak warstwy webowej); checked: 2026-06-30
- Provider/platform: none — brak GitHub/Cloudflare/Supabase MCP; checked: 2026-06-30

**Ograniczenia:**
- Faza 3 może się zacząć po ukończeniu `eegdigitrack-native-reader` (zmiana `eeg_file.py` w toku)
- Faza 2 wymaga fixture `tests/fixtures/sample_digitrack.eeg` — już dostępna

---

## §6 Cookbook (wypełniany per faza rollout)

### Faza 1 — Pokrycie krytycznej ścieżki domenowej

TBD — patrz §3 Faza 1. Wzorzec docelowy: boundary test algorytmu trójstanowego załadowanego z realnego norms.json (nie mock) + parametryzowane testy schema validation dla `load()` z invalid JSON samples.

### Faza 2 — Fidelity sygnału pipeline

Zaimplementowane w `context/changes/pipeline-signal-fidelity/` — `tests/integration/test_pipeline_fidelity.py`:

- **R4:** syntetyczny multi-band 50 µV → `run()` → każda amplituda w `(5, 200)` µV; segment >200 µV → `PipelineError(artifact_rejection)`
- **R5:** `sample_digitrack.eeg` (≥8 min) → `detect_task_segments()` fallback 3×3 min; `run()` → 10 skończonych amplitud (>1 µV)
- **Poprawka produkcyjna:** segment ZP <16 s przy wczesnym `"Artefakt"` przedłużany do +3 min (`pipeline.py`)

### Faza 3 — Hardening obsługi błędnych danych wejściowych

TBD — patrz §3 Faza 3. Wzorzec docelowy: crafted bad binary file → `EEGFileError`/`PipelineError` z user-facing message; `os.urandom(1024)` jako `.edf` → czytelny błąd zamiast traceback.

---

## §7 Rejestr negatywnej przestrzeni

Obszary świadomie wykluczone z budżetu testów (wywiad Q5 + PRD §Non-Goals):

| Obszar | Uzasadnienie |
|---|---|
| UI / widgety CustomTkinter (snapshot testy) | Widgety renderowane na ekranie to wystarczający dowód poprawności; CTk nie ma stabilnego API do snapshot testów |
| PDF — precyzja pikselowa (marginesy, wyrównanie, czcionki) | Przesunięcie marginesu o 2px nie wpływa na wynik przesiewowy; ReportLab API jest stabilne |
| Wewnętrzne detale filtrów MNE (notch, bandpass, ICA) | MNE-Python testuje własne algorytmy; NeuroFlag testuje tylko poprawność sygnału wyjściowego po całym pipeline |
| Historyczne trendy, porównania badań w czasie | PRD §Non-Goals; brak tej funkcji w MVP |
| Opcjonalne hasło startowe (FR-009) | Parked w roadmap (`low-complexity` goal); walidacja UI bez szyfrowania plików — iluzja bezpieczeństwa |
