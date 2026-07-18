# Natywny czytnik EEGDigiTrack (Elmiko) — Plan Brief

> Full plan: `context/changes/eegdigitrack-native-reader/plan.md`
> Research: `context/changes/eegdigitrack-native-reader/research.md`

## What & Why

Użytkownicy NeuroFlag posiadają pliki `.EEG` z aparatów Elmiko DigiTrack (EEG-1042),
których aplikacja nie potrafi wczytać. Format został w pełni zdekodowany
przez reverse engineering — wystarczy napisać czytnik bez dokumentacji producenta.

## Starting Point

`SUPPORTED_EXTENSIONS = {".edf", ".vhdr"}`. `_is_digitrack()` i poprawiony komunikat
błędu już istnieją. Brakuje właściwego czytnika i integracji z pipeline.

## Desired End State

Użytkownik wybiera plik `.EEG` z dialogu, widzi „✓ Plik wczytany poprawnie" i
przeprowadza pełną analizę. Segmentacja 3×3 min (fallback) używana automatycznie,
bo binarny format znaczników DigiTrack nie zawiera czytelnych etykiet OO/OZ/ZP.

## Key Decisions Made

| Decision | Choice | Why (1 zdanie) | Source |
|---|---|---|---|
| Liczba kanałów | Dynamicznie z nagłówka | Odporność na inne modele Elmiko | Plan |
| Kalibracja = 0 | EEGFileError | Zerowa kalibracja = dane zerowe bez ostrzeżenia | Plan |
| Anonimizacja PII | Jawne zerowanie `raw.info["subject_info"]` | Spójność z zachowaniem dla .edf | Plan |
| Fixture testowa | Fragment realnego pliku (anonimizowany nagłówek) | Testy rzeczywistego formatu binarnego | Plan |
| Markery zadań | Stub → fallback 3×3 min | Binar. strefa markerów bez etykiet tekstowych | Research |

## Scope

**In scope:**
- `read_raw_digitrack()` w `eeg_file.py` (parser binarny, dynamiczny n_ch)
- Gałąź `.eeg` w `pipeline._load_raw()`
- Jawne zerowanie PII przy `anonymize_header=True`
- Stub `_digitrack_annotations()` (hook na przyszłość)
- Filtr dialogu `*.eeg *.EEG` w `file_import.py`
- 7 testów jednostkowych + fixture ~137 KB

**Out of scope:**
- Dekodowanie etykiet markerów z binarnej strefy (wymaga spec. od Elmiko)
- Warianty 32-kanałowe (EEG-1040)
- Eksport DigiTrack→EDF w aplikacji

## Architecture / Approach

`read_raw_digitrack(path)` czyta plik binarnie, skanuje rekordy kanałów (64B/kanał od `0x0480`),
konstruuje `mne.io.RawArray(data_v, info)` — to standardowy typ MNE, dalej pipeline
działa bez zmian. Marker fallback 3×3 min przejmuje segmentację automatycznie
(brak adnotacji = brak match w `_match_task()` = `_fallback_segments()`).

```
.EEG plik
  └─ read_raw_digitrack()   ← nowe, w eeg_file.py
       └─ mne.io.RawArray   ← standard MNE
            └─ pipeline.run()  ← bez zmian
                 └─ detect_task_segments() → fallback 3×3 min
```

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Core reader | `read_raw_digitrack()` + walidacja | Inny `n_ch` w innych modelach Elmiko |
| 2. Pipeline | Integracja + PII clearing + marker stub | `raw.anonymize()` na RawArray — zachowanie do weryfikacji |
| 3. UI | Dialog filtruje `.eeg` | Trywialna — brak ryzyka |
| 4. Testy | 7 testów + fixture | CI może nie mieć MNE (skipif) |

**Prerequisites:** format zdekodowany (research.md gotowe), realny plik `.EEG` dostępny
lokalnie do generowania fixture.
**Estimated effort:** ~1 dzień implementacji, 0.5 dnia testów.

## Open Risks & Assumptions

- **n_ch != 19**: inne modele Elmiko mogą mieć inną liczbę kanałów; skanowanie
  dynamiczne powinno obsłużyć to poprawnie, ale nie jest przetestowane na innych plikach.
- **Strefa markerów**: brak dekodowania oznacza zawsze fallback 3×3 min dla DigiTrack —
  użytkownik musi zapewnić nagranie ≥8 min z protokołem OO/OZ/ZP w tej kolejności.
- **Format wersji**: sygnatura `EEGDigiTrack_EEG-1042_X` — inne wersje firmware mogą
  mieć inną strukturę nagłówka.

## Success Criteria (Summary)

- Plik `.EEG` (Elmiko EEG-1042) wczytywany bez błędu, analiza przebiega do końca
- Fixture < 200 KB z wyzerowanym PII w repozytorium
- `pytest tests/unit/ -q` + `mypy app/ --strict` przechodzą na CI
