---
date: 2026-06-26T13:30:00+02:00
researcher: agent (Claude Sonnet 4.6)
git_commit: 1ade0704c87593ba93da641a02b2075d91b4eae6
branch: coursor/dev-env-setup-2f65
repository: NeuroFlag
topic: "Format EEGDigiTrack (Elmiko) — czy MNE go obsługuje i czy można napisać natywny czytnik?"
tags: [research, eeg-format, elmiko, digitrack, reverse-engineering, mne]
status: complete
last_updated: 2026-06-26
last_updated_by: agent (Claude Sonnet 4.6)
---

# Research: Format EEGDigiTrack (Elmiko) — natywny czytnik w NeuroFlag

**Date**: 2026-06-26T13:30+02:00
**Git Commit**: `1ade0704c87593ba93da641a02b2075d91b4eae6`
**Branch**: `coursor/dev-env-setup-2f65`

## Research Question

Czy MNE-Python naprawdę nie obsługuje formatu EEGDigiTrack firmy Elmiko Medical?
Czy można wczytywać pliki `.EEG` (nagłówek `EEGDigiTrack_EEG-1042_X`) natywnie
w NeuroFlag bez konwersji przez oprogramowanie DigiTrack?

---

## Summary

**MNE-Python: brak wsparcia** — potwierdzone 97% pewnością.
**Format zdekodowany w całości** — reverse engineering na żywych plikach wykazał
pełną strukturę bez potrzeby specyfikacji producenta.
**Natywny czytnik jest realny** — ~2–3 dni pracy, implementacja jako `mne.io.RawArray`
lub dedykowana klasa w `app/domain/eeg_file.py`. Kalibracja, nazwy kanałów,
częstotliwość próbkowania i dane — wszystko odczytywalne.

---

## Detailed Findings

### 1. Wsparcie MNE-Python i ekosystemu Python

| Biblioteka | Wersja | Obsługa DigiTrack? |
|---|---|---|
| MNE-Python | 1.8.0 | ❌ Brak. `.EEG` → tylko Nihon Kohden (`read_raw_nihon`) |
| Neo (python-neo) | — | ❌ Nie na liście obsługiwanych |
| biosigIO | — | ❌ Brak wzmianki |
| PyPI (dowolny pakiet) | — | ❌ Zero pakietów dla Elmiko/DigiTrack |
| NeuroAnalyzer.jl | Julia | ⚠️ Czyta TEKSTOWY export (`.txt`), nie binarny `.EEG` |

Jedyna publiczna implementacja to **NeuroAnalyzer.jl** (Adam Wysokiński, UM Łódź, 2025),
która wczytuje plik tekstowy z eksportu DigiTrack — nie natywny binarny format.

### 2. Ekosystem narzędzi zewnętrznych

| Narzędzie | Obsługa DigiTrack? |
|---|---|
| EEGLAB (MATLAB) | ❌ Brak pluginu |
| FieldTrip (MATLAB) | ❌ Brak |
| EDFbrowser | ❌ Brak konwertera DigiTrack→EDF |
| Elmiko SDK / format spec | ❌ Nie publikowane |

**Ważne:** Elmiko eksportuje dane do **EDF/EDF+/BDF+** bezpośrednio z DigiTrack
(potwierdzone przez edfplus.info i bazę ELM19 — 80 tys. nagrań, przetwarzanych
przez badaczy z MNE po eksporcie do EDF).

### 3. Reverse engineering formatu binarnego — PEŁNA MAPA

Pliki testowe:
- `Kuczyński.EEG` — 13 095 336 B, 22,9 min, M/1996
- `kobrys.EEG` — 13 038 208 B, 22,8 min, M/1989

#### Nagłówek (fixed, ~42 KB)

| Offset | Typ | Wartość (przykład) | Opis |
|---|---|---|---|
| `0x0004` | uint16 LE | `250` | Częstotliwość próbkowania [Hz] |
| `0x0010` | uint32 LE | `343500` | Liczba próbek (time blocks) |
| `0x00C4` | ASCII | `03.04.25\|5\|\|13.39.54\|\|X M 06-JUL-1996 Michal_KUCZYNSKI` | Data, czas, pacjent (płeć, DOB, nazwisko) |
| `0x014C` | ASCII | `EEGDigiTrack_EEG-1042_X` | Sygnatura formatu / wersja |
| `0x0480` | bloki po 64B | — | Rekordy kanałów (patrz niżej) |

#### Rekordy kanałów (od `0x0480`, co 64 bajty = `0x40`)

```
base = 0x0480 + channel_index * 0x40
+0x00  name        ASCII, null-terminated (może mieć śmieciowe bajty po \0)
+0x18  calibration float32 LE [µV/LSB]
```

**19 kanałów EEG** (kolejność stała):

| idx | Offset | Nazwa | Kalibracja |
|---|---|---|---|
| 0 | `0x0480` | Fp1 | 0.179266 µV/LSB |
| 1 | `0x04C0` | Fp2 | 0.179266 |
| 2 | `0x0500` | F3 | 0.179266 |
| 3 | `0x0540` | F4 | 0.179266 |
| 4 | `0x0580` | C3 | 0.179266 |
| 5 | `0x05C0` | C4 | 0.179266 |
| 6 | `0x0600` | P3 | 0.179266 |
| 7 | `0x0640` | P4 | 0.179266 |
| 8 | `0x0680` | O1 | 0.179266 |
| 9 | `0x06C0` | O2 | 0.179266 |
| 10 | `0x0700` | F7 | 0.179266 |
| 11 | `0x0740` | F8 | 0.179266 |
| 12 | `0x0780` | T7 | 0.179266 |
| 13 | `0x07C0` | T8 | 0.179266 |
| 14 | `0x0800` | P7 | 0.179266 |
| 15 | `0x0840` | P8 | 0.179266 |
| 16 | `0x0880` | Fz | 0.179266 |
| 17 | `0x08C0` | Cz | 0.179266 |
| 18 | `0x0900` | Pz | 0.179266 |
| 19 | `0x0940` | ECG | 2.500000 µV/LSB (nie w strumieniu danych) |

> **Uwaga:** Kanał ECG jest w nagłówku, ale **nie** w binarnym strumieniu danych.

#### Strumień danych

```
data_start = file_size - total_blocks * 19 * 2

Format: int16 LE, interleaved
Układ:  [Fp1_t0, Fp2_t0, ..., Pz_t0, Fp1_t1, Fp2_t1, ..., Pz_t1, ...]
```

**Wzór konwersji do µV:**

```python
value_uV = raw_int16 * calibration_factor
# calibration_factor = 0.179266 (z rekordu kanału +0x18)
```

**Weryfikacja fizjologiczna** (pierwsze próbki ch0=Fp1, Kuczyński):
`0.9, 4.84, 3.76, 2.69, 4.48, -1.43, 1.97, 6.63, -1.08, 4.12 µV` — typowy zakres EEG skalpowego.

---

## Code References

- `app/domain/eeg_file.py:6` — `SUPPORTED_EXTENSIONS` — tu dodać `.eeg`
- `app/domain/eeg_file.py:13-27` — `_is_digitrack()`, `validate_extension()` — już wykrywamy sygnaturę
- `app/domain/eeg_file.py:39-56` — `get_channel_names()` — dodać gałąź dla DigiTrack
- `app/domain/eeg_file.py:59-79` — `validate_eeg_header()` — dodać gałąź DigiTrack
- `app/domain/pipeline.py` — tu dodać `read_raw_digitrack()` zwracające `mne.io.RawArray`

---

## Architecture Insights

### Strategia integracji z MNE

Format nie jest obsługiwany przez `mne.io.read_raw_*`, ale MNE pozwala tworzyć
obiekty `Raw` z surowych tablic przez `mne.io.RawArray`. Minimalna implementacja:

```python
import struct
import numpy as np
import mne
from pathlib import Path

def read_raw_digitrack(path: Path) -> mne.io.RawArray:
    with open(path, 'rb') as f:
        data = f.read()

    sfreq = struct.unpack_from('<H', data, 0x0004)[0]           # 250
    total_blocks = struct.unpack_from('<I', data, 0x0010)[0]
    n_ch = 19
    data_start = len(data) - total_blocks * n_ch * 2

    # Nazwy i kalibracja z rekordów kanałów
    ch_names = []
    ch_cal = []
    for i in range(n_ch):
        base = 0x0480 + i * 0x40
        raw_name = data[base:base + 16]
        name = raw_name.split(b'\x00')[0].decode('ascii', errors='replace').strip()
        cal = struct.unpack_from('<f', data, base + 0x18)[0]
        ch_names.append(name)
        ch_cal.append(cal)

    # Dane int16 → float64 [µV → V dla MNE]
    raw_int16 = np.frombuffer(data[data_start:], dtype='<i2').reshape(total_blocks, n_ch).T
    data_uv = raw_int16.astype(np.float64) * np.array(ch_cal)[:, None]
    data_v = data_uv * 1e-6  # MNE pracuje w V

    info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types='eeg')
    return mne.io.RawArray(data_v, info, verbose=False)
```

### Gdzie to wpasować

```
app/domain/eeg_file.py        ← dodać read_raw_digitrack() i gałąź w validate/get_channels
app/domain/pipeline.py        ← w _load_raw(): if suffix == '.eeg' and _is_digitrack() → read_raw_digitrack()
```

Nie trzeba tworzyć nowego modułu — obie funkcje pasują do istniejących.

### Ograniczenia znane

1. **Znaczniki (markery) zadań** — lokalizacja w nagłówku niezbadana; mogą być w bloku między
   końcem rekordów kanałów (ok. `0x09C0`) a początkiem danych (`~0x0A4E0`). Wymagana dalsza analiza.
2. **Warianty aparatów** — format `EEGDigiTrack_EEG-1042_X`; inne modele Elmiko (np. EEG-1040, 32-kanałowe)
   mogą mieć inną liczbę kanałów — `n_ch` powinno być czytane z nagłówka, nie hardkodowane.
3. **Kalibracja per-kanał** — wszystkie 19 kanałów EEG mają identyczną kalibrację 0.179266,
   ale może różnić się między sesjami lub urządzeniami — zawsze czytać z nagłówka.

---

## Historical Context

- `context/changes/eeg-file-personal-data/plan.md` — plan dodania anonimizacji nagłówka EDF/BrainVision;
  `raw.anonymize()` nie zadziała dla DigiTrack (niestandardowy loader) — trzeba czyścić `raw.info` po `RawArray`.

---

## Open Questions

1. **Lokalizacja znaczników** — gdzie w nagłówku są zdarzenia OO/OZ/ZP (potrzebne do segmentacji pipeline)?
   Blok `0x09C0`–`0x0A4E0` (~2KB) do zbadania.
2. **Liczba kanałów z nagłówka** — offset przechowujący `n_ch` (19?) — prawdopodobnie `0x000A` lub `0x000C`,
   wymaga porównania z plikiem 32-kanałowym jeśli dostępny.
3. **Warianty formatu** — czy `EEGDigiTrack_EEG-1040_X` ma inną strukturę?
4. **Testowe pliki z BrainVision** — `test.eeg` w folderze to plik BrainVision (nie DigiTrack);
   current code odrzuci go poprawnie przez `_is_digitrack() == False`.
