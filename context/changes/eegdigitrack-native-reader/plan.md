# Natywny czytnik EEGDigiTrack (Elmiko) — Plan implementacji

## Overview

Dodanie obsługi plików `.EEG` w formacie EEGDigiTrack (Elmiko Medical) do NeuroFlag.
Użytkownik będzie mógł wczytać plik `.EEG` bezpośrednio — bez eksportu do EDF przez
oprogramowanie DigiTrack. Czytnik oparty na reverse engineeringu formatu binarnego
(patrz `context/changes/eegdigitrack-native-reader/research.md`).

## Current State Analysis

- `app/domain/eeg_file.py` — `SUPPORTED_EXTENSIONS = {".edf", ".vhdr"}`, `_is_digitrack()`
  i poprawiony komunikat błędu już istnieją (commit z sesji 2026-06-26).
  Brakuje: `read_raw_digitrack()`, gałęzi w `validate_eeg_header()` i `get_channel_names()`.
- `app/domain/pipeline.py:259–264` — `_load_raw()` rozgałęzia tylko na `.edf`/`.vhdr`.
- `app/ui/views/file_import.py:106` — dialog filtruje tylko `*.edf *.vhdr`.
- `tests/unit/test_eeg_file.py` — brak testów dla DigiTrack; wzorzec mock-MNE gotowy.
- Brak fixture z plikiem `.EEG` w folderze `tests/`.

### Key Discoveries (z research.md):

- Format binarny zdekodowany bez spec: nagłówek ~42 KB, dane od
  `file_size − total_blocks × n_ch × 2`, int16 LE, interleaved.
- n_ch odczytywany przez skanowanie rekordów 64-bajtowych od `0x0480` — zatrzymaj się
  przy pierwszej nazwie kanału pustej lub równej `"Default"`.
- Kalibracja: float32 LE w rekordzie kanału na offset +0x18 (typowo 0.179266 µV/LSB).
- Strefa markerów (`0x09C0` → data_start, ~40 KB) nie zawiera czytelnych etykiet
  tekstowych (brak "OO"/"OZ"/"ZP") — pipeline zawsze trafi do fallback 3×3 min.
- PII w nagłówku DigiTrack nie jest kopiowane do `mne.io.RawArray.info` — ale
  `subject_info` w `info` musi być jawnie zerowany dla spójności z `.edf`.

## Desired End State

Użytkownik może kliknąć „Wczytaj plik", wybrać plik `.EEG` (DigiTrack, Elmiko),
zobaczyć „✓ Plik wczytany poprawnie" i przeprowadzić pełną analizę.
Segmentacja fallback 3×3 min używana automatycznie (brak czytelnych znaczników zadań).
Wszystkie testy przechodzą na CI Windows.

## What We're NOT Doing

- Dekodowanie etykiet markerów z binarnej strefy — odłożone do czasu uzyskania
  specyfikacji od Elmiko lub nagrania z potwierdzonymi znacznikami.
- Obsługa wariantów 32-kanałowych (`EEG-1040`) — nieznany offset `n_ch` w nagłówku.
- Eksport/konwersja DigiTrack→EDF w aplikacji.
- Zmiana układu normalizacji kanałów (DigiTrack używa T7/T8 zamiast T3/T4 — istniejące
  `normalize_channel_names()` obsłuży to przez tablicę aliasów).

## Implementation Approach

Cztery fazy: (1) czysta funkcja `read_raw_digitrack()` i powiązane pomocniki
w `eeg_file.py`; (2) integracja w `pipeline.py` + stub dekodera markerów +
jawne zerowanie PII; (3) zmiana filtra dialogu w `file_import.py`; (4) fixture
z wycinkiem realnego pliku Kuczyński.EEG (anonimizowany nagłówek) + testy.

## Critical Implementation Details

- **Kalibracja = 0 → EEGFileError**: jeśli `cal ≤ 0.0` dla któregokolwiek kanału EEG,
  rzuć `EEGFileError("Uszkodzony nagłówek: kalibracja kanału {name} = 0")`.
  Nie używaj fallbacku — zerowa kalibracja wygeneruje dane zerowe bez ostrzeżenia.
- **n_ch: skanowanie + filtr kalibracji**: czytaj rekordy od `0x0480` co 64B, zatrzymaj się
  gdy `name.strip() in ("", "Default")` lub gdy `name[0]` jest bajtem < 0x20.
  Wynik to `ch_names_all` / `ch_cal_all` (wszystkie kanały z nagłówka, łącznie z ECG).
  Następnie oblicz `n_ch_data = sum(1 for c in ch_cal_all if c <= 1.0)` — kanały EEG
  (kalibracja ~0.179 µV/LSB). Kanały spoza zakresu EEG (np. ECG, cal=2.5 µV/LSB)
  są w nagłówku, ale **nie** w strumieniu danych — wyklucz je z `data_start` i `reshape`.
  Użyj `ch_names_data = [n for n, c in zip(ch_names_all, ch_cal_all) if c <= 1.0]`.
  Rzuć `EEGFileError` gdy `n_ch_data < 1`.
  Zakładane ograniczenie: kanały EEG zawsze mają kalibrację < 1.0 µV/LSB;
  jeśli przyszły model Elmiko używa innego wzmocnienia, próg wymaga rewizji.
- **Dane: frombuffer po tle wczytania**: plik DigiTrack może mieć 13 MB+ — używaj
  `np.frombuffer(data[data_start:], dtype='<i2').reshape(total_blocks, n_ch).T`
  (nie iteruj po próbkach — koszt O(n)).
- **Typ MNE**: `mne.io.RawArray` wymaga danych w V (nie µV) — `data_v = data_uv * 1e-6`.

---

## Phase 1: Core reader — `app/domain/eeg_file.py`

### Overview

Implementacja `read_raw_digitrack()` jako czystej funkcji (bez efektów ubocznych poza I/O),
aktualizacja `validate_eeg_header()` i `get_channel_names()` dla gałęzi `.eeg`.

### Changes Required:

#### 1. Dodaj import `struct` i `numpy`

**File**: `app/domain/eeg_file.py`

**Intent**: Czytnik binarny wymaga `struct` i `numpy`; obydwa są już w zależnościach
projektu (numpy jest zależnością MNE).

**Contract**: Dodaj `import struct` i `import numpy as np` na górze pliku.

#### 2. Dodaj `.eeg` do `SUPPORTED_EXTENSIONS`

**File**: `app/domain/eeg_file.py:6`

**Intent**: Udostępnienie rozszerzenia `.eeg` w walidacji, żeby `validate_extension()`
nie rzucał błędu przed sprawdzeniem sygnatury.

**Contract**: `SUPPORTED_EXTENSIONS = frozenset({".edf", ".vhdr", ".eeg"})`.
Uwaga: `validate_extension()` już ma gałąź `if suffix == ".eeg" and _is_digitrack()` —
ta gałąź po zmianie `SUPPORTED_EXTENSIONS` stanie się martwą ścieżką dla poprawnych
plików DigiTrack; usuń ją (obsługę błędu dla `.eeg` bez sygnatury DigiTrack przejmie
fallback niżej).

#### 3. Dodaj `read_raw_digitrack()`

**File**: `app/domain/eeg_file.py`

**Intent**: Załadować plik DigiTrack do `mne.io.RawArray` z poprawnymi nazwami kanałów,
częstotliwością próbkowania i danymi skalibrowanymi w V. Rzucić `EEGFileError`
gdy nagłówek jest uszkodzony.

**Contract**: Sygnatura:
```python
def read_raw_digitrack(path: Path) -> mne.io.RawArray:
```
Zwraca obiekt `mne.io.RawArray`. Rzuca `EEGFileError` gdy:
- sygnatura `_DIGITRACK_SIGNATURE` nieobecna,
- n_ch < 1,
- kalibracja któregokolwiek kanału ≤ 0.0,
- obliczony `data_start < 0`.

Logika n_ch: pętla `for i in range(32)` skanuje rekordy od `0x0480`, przerywa gdy
`name.strip()` jest puste lub `== "Default"` (lub gdy `name[0] < 0x20`). Zbiera
`ch_names_all` i `ch_cal_all` dla wszystkich znalezionych rekordów, po czym oblicza
`n_ch_data = len([c for c in ch_cal_all if c <= 1.0])` — tylko kanały EEG (kalibracja
≤ 1.0 µV/LSB) wchodzą do `data_start` i `reshape`. ECG (cal=2.5) jest automatycznie
wykluczony. Przekaż do `mne.create_info` jedynie `ch_names_data`.

#### 4. Zaktualizuj `validate_eeg_header()` — gałąź DigiTrack

**File**: `app/domain/eeg_file.py:59`

**Intent**: Walidacja pliku `.eeg` DigiTrack: sprawdź sygnaturę i czy `read_raw_digitrack()`
nie rzuca błędu, ale nie wczytuj danych (ustaw `preload=False` — tu tylko nagłówek).

**Contract**: Dodaj gałąź `elif suffix == ".eeg":` — wywołaj `_is_digitrack(path)`,
jeśli False → rzuć `EEGFileError("Plik .eeg nie jest w formacie EEGDigiTrack.")`,
następnie wczytaj tylko nagłówek (wywołaj `read_raw_digitrack` z wewnętrznym `preload=False`
lub czytaj nagłówek bez tablicy danych). Opcja prosta: wywołaj `read_raw_digitrack(path)`
(wczyta plik w całości, ale walidacja jest poprawna; wydajność nie jest tu priorytetem).

#### 5. Zaktualizuj `get_channel_names()` — gałąź DigiTrack

**File**: `app/domain/eeg_file.py:39`

**Intent**: Zwrócić nazwy kanałów EEG z nagłówka DigiTrack bez ładowania danych.

**Contract**: Dodaj gałąź `elif suffix == ".eeg":` wywołującą `read_raw_digitrack(path)`
i zwracającą `list(raw.ch_names)`. W bloku `except Exception` zwróć `[]`.

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/test_eeg_file.py -q` przechodzi (testy z Phase 4)
- `mypy app/domain/eeg_file.py --strict` bez błędów
- `ruff check app/domain/eeg_file.py` bez błędów

#### Manual Verification:

- `read_raw_digitrack(Path("D:/CVGOSI/NF dane/Testowe/Kuczyński.EEG"))` zwraca
  `RawArray` z 19 kanałami, sfreq=250, danymi w zakresie ±50 µV (sprawdź `raw.get_data(units="uV").mean()`)

**Implementation Note**: Po zakończeniu tej fazy i przejściu automatycznych weryfikacji,
zatrzymaj się na ręczne potwierdzenie zanim przejdziesz do Phase 2.

---

## Phase 2: Integracja pipeline — `app/domain/pipeline.py`

### Overview

Podłączenie `read_raw_digitrack()` do `_load_raw()`, jawne zerowanie PII
z `raw.info`, stub dekodera markerów DigiTrack.

### Changes Required:

#### 1. Gałąź `.eeg` w `_load_raw()`

**File**: `app/domain/pipeline.py:259`

**Intent**: Wywołać `read_raw_digitrack()` gdy plik ma rozszerzenie `.eeg`.

**Contract**: Po bloku `if suffix == ".vhdr":` dodaj osobną gałąź **poza** istniejącym
`try/except (OSError, Exception)` (lub z własnym `except EEGFileError`), żeby zachować
szczegółowy komunikat błędu czytnika DigiTrack:
```python
if suffix == ".eeg":
    from app.domain.eeg_file import read_raw_digitrack, EEGFileError as _EEGErr
    try:
        return read_raw_digitrack(path)
    except _EEGErr as exc:
        raise PipelineError("file_unreadable", str(exc)) from exc
```
Nie umieszczaj tej gałęzi wewnątrz istniejącego `except (OSError, Exception)` —
`EEGFileError` dziedziczy po `Exception` i zostałby złapany, tracąc szczegóły błędu
(np. "kalibracja kanału X = 0", "sygnatura nieobecna").

#### 2. Jawne zerowanie PII w `run()` dla DigiTrack

**File**: `app/domain/pipeline.py:330–338`

**Intent**: Gdy `anonymize_header=True`, `raw.anonymize()` działa na obiektach MNE
z metadanymi (EDF/BrainVision). Dla DigiTrack `RawArray` info nie niesie PII z nagłówka,
ale `subject_info` może być puste dict zamiast null — wyczyść jawnie dla spójności.

**Contract**: Po `raw.anonymize(...)` wywołaj:
```python
raw.info["subject_info"] = {}
```
Warunek: tylko gdy `anonymize_header=True`. Nie rzucaj wyjątku jeśli klucz nie istnieje.

#### 3. Stub dekodera markerów DigiTrack

**File**: `app/domain/pipeline.py` (nowa prywatna funkcja)

**Intent**: Stworzyć hook `_digitrack_annotations(data: bytes, sfreq: float)` jako
punkt rozszerzenia do przyszłego dekodowania binarnej strefy markerów. W tej wersji
zwraca `None` — nie dodaje adnotacji, pipeline używa fallback 3×3 min.

**Contract**: Sygnatura:
```python
def _digitrack_annotations(
    data: bytes, sfreq: float
) -> mne.Annotations | None:
    """Próbuje odczytać znaczniki zdarzeń z binarnej strefy DigiTrack.

    Zwraca None gdy format strefy jest nieznany — pipeline używa wtedy fallback 3×3 min.
    Pełne dekodowanie wymaga specyfikacji od Elmiko (patrz research.md Open Questions).

    Uwaga dla przyszłego implementatora: aktywacja tej funkcji wymaga refaktoru
    read_raw_digitrack() tak, by zwracała (RawArray, bytes) lub przechowywała
    surowe bajty — pipeline.run() operuje wyłącznie na mne.io.BaseRaw i nie ma
    dostępu do bajtów pliku po załadowaniu.
    """
    return None
```
Funkcja nie jest wywoływana przez `run()` w tej fazie — zostaje zarejestrowana
jako TODO w komentarzu w `read_raw_digitrack()`.

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/test_pipeline.py -q` przechodzi bez regresji
- `mypy app/domain/pipeline.py --strict` bez błędów

#### Manual Verification:

- Uruchom aplikację, wczytaj `Kuczyński.EEG`, kliknij „Analizuj" — analiza
  powinna przejść (segmentacja fallback, kanały C3/O1 znalezione)
- Przy zaznaczonym checkboxie „Wyczyść dane identyfikacyjne" — brak błędu

**Implementation Note**: Po zakończeniu tej fazy zatrzymaj się na ręczne potwierdzenie.

---

## Phase 3: UI — dialog wyboru pliku

### Overview

Rozszerzenie filtra dialogu w `FileImportView` o rozszerzenie `.eeg`/`.EEG`.

### Changes Required:

#### 1. Dodaj `*.eeg *.EEG` do filtra dialogu

**File**: `app/ui/views/file_import.py:105–108`

**Intent**: Pozwolić użytkownikowi widzieć i wybierać pliki `.eeg`/`.EEG` w standardowym
dialogu systemu Windows bez konieczności przełączania na „Wszystkie pliki".

**Contract**: Zmień `filetypes` na:
```python
filetypes=[
    ("Pliki EEG", "*.edf *.vhdr *.eeg *.EEG"),
    ("Wszystkie pliki", "*.*"),
]
```

### Success Criteria:

#### Automated Verification:

- `mypy app/ui/views/file_import.py --strict` bez błędów
- `ruff check app/ui/views/file_import.py` bez błędów

#### Manual Verification:

- Dialog „Wczytaj plik" pokazuje pliki `.EEG` w folderze testowym bez przełączania
  na „Wszystkie pliki"

**Implementation Note**: Faza jest mała — można wykonać razem z Phase 2 lub 4.

---

## Phase 4: Fixture i testy jednostkowe

### Overview

Stworzenie deterministycznej fixtures z wycinkiem realnego pliku DigiTrack
(anonimizowany nagłówek) i testów jednostkowych.

### Changes Required:

#### 1. Skrypt generatora fixture

**File**: `tests/fixtures/generate_digitrack_fixture.py` (jednorazowy skrypt)

**Intent**: Wyciąć pierwsze 10 sekund (2500 próbek × n_ch × 2 B) z realnego pliku
`Kuczyński.EEG`, wyzerować bajty PII (`0x00C4`–`0x0143`, ~128 B) i zapisać jako
`tests/fixtures/sample_digitrack.eeg`. Skrypt ma być uruchamiany ręcznie, nie w CI.

**Contract**: Skrypt czyta pełny plik, patchuje bajty PII znakami `\x00`,
oblicza nowy `total_blocks = 2500`, aktualizuje pole `0x0010`, skraca strumień danych
do `2500 × n_ch × 2` bajtów i zapisuje plik. Plik wynikowy ≈ 42 KB nagłówka + 95 KB
danych = ~137 KB — akceptowalne dla repozytorium.

#### 2. Testy jednostkowe DigiTrack

**File**: `tests/unit/test_eeg_file.py`

**Intent**: Pokryć ścieżki happy path i błędy czytnika DigiTrack.

**Contract**: Dodaj testy:
- `test_validate_extension_accepts_eeg_digitrack` — plik z sygnaturą `_DIGITRACK_SIGNATURE`
  przechodzi `validate_extension()` bez wyjątku (użyj `tmp_path` + zapisz minimalny nagłówek).
- `test_validate_extension_rejects_eeg_without_signature` — plik `.eeg` bez sygnatury →
  `EEGFileError` z komunikatem o nieobsługiwanym rozszerzeniu.
- `test_read_raw_digitrack_channel_count` — fixture `sample_digitrack.eeg` →
  `len(raw.ch_names) == 19`.
- `test_read_raw_digitrack_sfreq` — fixture → `raw.info["sfreq"] == 250.0`.
- `test_read_raw_digitrack_data_shape` — fixture → `raw.get_data().shape == (19, 2500)`.
- `test_read_raw_digitrack_calibration_zero_raises` — plik z zerową kalibracją w nagłówku
  → `EEGFileError`.
- `test_get_channel_names_digitrack` — fixture → `"C3" in get_channel_names(fixture_path)`.

Użyj `pytest.mark.skipif` lub `tmp_path` dla testów wymagających MNE (analogicznie do
istniejącego `test_validate_eeg_header_edf_ok` z `@patch("mne.io.read_raw_edf")`).
Dla `test_read_raw_digitrack_*` — użyj realnej fixture (nie mock), ponieważ testujemy
logikę parsowania binarnego.

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/ -q` — wszystkie 7 nowych testów przechodzi
- `python -m pytest tests/unit/test_eeg_file.py -v` — brak regresji starych testów
- `mypy tests/unit/test_eeg_file.py --strict` bez błędów

#### Manual Verification:

- Ręczne uruchomienie `generate_digitrack_fixture.py` tworzy plik < 200 KB

**Implementation Note**: Po zakończeniu tej fazy zatrzymaj się na ręczne potwierdzenie.

---

## Testing Strategy

### Unit Tests:

- `test_validate_extension_accepts_eeg_digitrack` — plik z sygnaturą
- `test_validate_extension_rejects_eeg_without_signature` — brak sygnatury
- `test_read_raw_digitrack_channel_count` — 19 kanałów
- `test_read_raw_digitrack_sfreq` — 250 Hz
- `test_read_raw_digitrack_data_shape` — kształt tablicy
- `test_read_raw_digitrack_calibration_zero_raises` — kalibracja = 0
- `test_get_channel_names_digitrack` — "C3" w liście

### Manual Testing Steps:

1. Uruchom aplikację, przejdź do FileImportView
2. Otwórz dialog — sprawdź że `.EEG` widoczne bez „Wszystkie pliki"
3. Wczytaj `Kuczyński.EEG` — oczekiwany komunikat „✓ Plik wczytany poprawnie"
4. Sprawdź mapowanie kanałów jeśli C3/O1 nieznalezione (może wymagać ChannelMappingView)
5. Kliknij „Analizuj" — analiza powinna przejść fallbackiem 3×3 min
6. Wygeneruj raport PDF — sprawdź brak wartości µV i obecność 4 sekcji
7. Zaznacz „Wyczyść dane identyfikacyjne" i powtórz flow — brak błędu

## Migration Notes

Fixture `tests/fixtures/sample_digitrack.eeg` (~137 KB) do dodania do repozytorium.
PII (imię, data urodzenia, PESEL) wyzerowane przez skrypt generatora.

## References

- Research: `context/changes/eegdigitrack-native-reader/research.md`
- Format binarny: `research.md` sekcja „Reverse engineering formatu binarnego"
- Istniejący czytnik EDF: `app/domain/eeg_file.py:44–56` (wzorzec do naśladowania)
- Istniejące testy: `tests/unit/test_eeg_file.py` (wzorzec mock-MNE)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Core reader — `app/domain/eeg_file.py`

#### Automated

- [x] 1.1 `pytest tests/unit/test_eeg_file.py -q` przechodzi (testy z Phase 4)
- [x] 1.2 `mypy app/domain/eeg_file.py --strict` bez błędów
- [x] 1.3 `ruff check app/domain/eeg_file.py` bez błędów

#### Manual

- [ ] 1.4 `read_raw_digitrack()` zwraca RawArray z 19 ch, sfreq=250, dane ±50 µV

### Phase 2: Integracja pipeline — `app/domain/pipeline.py`

#### Automated

- [x] 2.1 `pytest tests/unit/test_pipeline.py -q` bez regresji
- [x] 2.2 `mypy app/domain/pipeline.py --strict` bez błędów

#### Manual

- [ ] 2.3 Uruchom aplikację, wczytaj Kuczyński.EEG, analiza przechodzi fallbackiem 3×3 min
- [ ] 2.4 Checkbox anonimizacji nie powoduje błędu przy pliku DigiTrack

### Phase 3: UI — dialog wyboru pliku

#### Automated

- [x] 3.1 `mypy app/ui/views/file_import.py --strict` bez błędów
- [x] 3.2 `ruff check app/ui/views/file_import.py` bez błędów

#### Manual

- [ ] 3.3 Dialog pokazuje .EEG pliki bez przełączania na „Wszystkie pliki"

### Phase 4: Fixture i testy jednostkowe

#### Automated

- [x] 4.1 `pytest tests/unit/ -q` — 7 nowych testów DigiTrack przechodzi
- [x] 4.2 `pytest tests/unit/test_eeg_file.py -v` — brak regresji starych testów
- [x] 4.3 `mypy tests/unit/test_eeg_file.py --strict` bez błędów

#### Manual

- [ ] 4.4 `generate_digitrack_fixture.py` tworzy plik < 200 KB
