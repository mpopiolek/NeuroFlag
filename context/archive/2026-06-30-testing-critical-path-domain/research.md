---
date: 2026-06-30T19:38:00+02:00
researcher: AI Agent
git_commit: 8e0724066b166728e40ad59e5d053bd6c268386c
branch: coursor/dev-env-setup-2f65
repository: NeuroFlag
topic: "R4 spalony — jak sprawdzić, czy zbyt agresywne czyszczenie artefaktów powoduje wszystkie czerwone komórki"
tags: [research, pipeline, artifact-rejection, marker-fallback, rag-colors, all-red]
status: complete
last_updated: 2026-06-30
last_updated_by: AI Agent
---

# Research: Jak sprawdzić, czy czyszczenie artefaktów jest zbyt agresywne (R4)

**Date**: 2026-06-30T19:38:00+02:00
**Git Commit**: `8e0724066b166728e40ad59e5d053bd6c268386c`
**Branch**: coursor/dev-env-setup-2f65
**Repository**: NeuroFlag

---

## Research Question

Realne pliki pacjentów ze wskazaniami klinicznymi zwracają wyłącznie czerwone komórki. Dwie hipotezy:

- **(a) Zbyt agresywne czyszczenie** usuwa sygnał EEG razem z szumem → amplitudy bliskie zeru → wszystkie komórki czerwone.
- **(b) Fallback 3×3 min** — opis znacznika jest spoza listy aliasów → pipeline cicho przełącza się na pierwsze 9 minut nagrania → złe segmenty → błędne amplitudy → wszystko czerwone.

**Pytanie:** Jak możemy sprawdzić, czy to hipoteza (a)?

---

## Summary — kluczowy wniosek

> **Hipoteza (a) w tradycyjnym sensie (ICA, autoreject, wycinanie próbek) nie istnieje w kodzie.** Jedynym artefaktowym gejtem jest binarny próg `200 µV peak-to-peak` na całym segmencie. Gdy on się odpala, pipeline rzuca widoczny błąd `PipelineError("artifact_rejection")` pokazywany użytkownikowi — **nigdy nie produkuje cicho wszystkich-czerwonych**. Cicha ścieżka do wszystkich-czerwonych biegnie wyłącznie przez **nieprawidłowe amplitudy** docierające do `algorithm.classify()`, a głównym mechanizmem jest hipoteza (b): fallback 3×3 min.

Mimo to, **diagnozowanie (a) jest warte zrobienia**, bo:
1. Filtr pasmowoprzepustowy *zmienia* amplitudę (to design, ale normy muszą być liczone z tymi samymi filtrami).
2. Nie ma żadnego logowania pośrednich wartości — nie wiadomo, co wychodzi spod filtra.
3. Nie ma testu walidującego, że 50 µV wejściowe → >5 µV wyjściowe po filtracji.

---

## Detailed Findings

### 1. Architektura czyszczenia artefaktów

Cały pipeline czyszczenia żyje w jednej funkcji:

```299:338:app/domain/pipeline.py
def _amplitude_for_norm(
    raw: mne.io.BaseRaw,
    norm: NormEntry,
    segments: dict[str, tuple[float, float]],
    config: NormsConfig,
) -> float:
```

**Sekwencja na komórkę (channel × task × band):**

| Krok | Lokalizacja | Co robi |
|------|------------|---------|
| Crop do segmentu zadania | `pipeline.py:307–310` | Wycina ~180 s z nagrania |
| Notch filter | `pipeline.py:314–317` | 50 Hz z `config.power_line_frequency` |
| Bandpass filter | `pipeline.py:318–322` | Pasmo z `config.band_ranges[norm.band]` |
| Jeden epoch = cały segment | `pipeline.py:325–329` | `EpochsArray` z jedną epoką |
| Brama 200 µV p-p | `pipeline.py:330` | `drop_bad(reject={"eeg": 200e-6})` |
| Jeśli epoki=0 → error | `pipeline.py:331–336` | `PipelineError("artifact_rejection")` |
| Metryka = mean(abs(µV)) | `pipeline.py:337–338` | Wynik komórki |

Jedyna hardkodowana stała:

```30:30:app/domain/pipeline.py
_REJECT_EEG_VOLTS = 200e-6  # 200 µV peak-to-peak (dane MNE w V)
```

**Czego NIE MA w pipeline:** ICA, autoreject, interpolacja złych odcinków, sub-epoch windowing, EOG regression, baseline correction, detrending. Plan z archiwum (`context/archive/2026-06-03-eeg-pipeline-and-results/plan.md:44–46`) celowo wyklucza te mechanizmy jako out-of-MVP.

### 2. Dlaczego 200 µV nie może produkować cichego "wszystko czerwone"

`PipelineError("artifact_rejection")` jest zgłaszany gdy `len(epochs) == 0` wewnątrz pętli po 10 normach (`pipeline.py:374–383`). Błąd propaguje się przez `pipeline.run()` i jest łapany w UI:

```19:20:app/ui/views/analysis.py
"artifact_rejection": "Segment artefaktowy odrzucony",
```

Użytkownik widzi **komunikat błędu**, nie siatkę czerwonych komórek. Ścieżka `artifact_rejection` → wszystko-czerwone jest **niemożliwa** w obecnym kodzie.

### 3. Mechanizm RAG: czerwone = za NISKA amplituda

```17:22:app/domain/algorithm.py
def _cell_color(amplitude: float, mean_z: float, mean_k: float) -> CellColor:
    if amplitude <= mean_z + _EPSILON:
        return CellColor.RED
    if amplitude >= mean_k - _EPSILON:
        return CellColor.GREEN
    return CellColor.YELLOW
```

Komórka jest czerwona gdy `amplitude ≤ mean_z`. Progi z `norms.json`:

| id | channel | task | band | mean_z (RED ≤) | mean_k (GREEN ≥) |
|----|---------|------|------|----------------|-----------------|
| 1 | C3 | OZ | Theta | 30.35 µV | 35.44 µV |
| 2 | C3 | ZP | Theta | 20.32 µV | 25.25 µV |
| 3 | C3 | ZP | Beta1 | 5.26 µV | 6.56 µV |
| 4 | C3 | OO | Beta2 | 5.18 µV | 6.29 µV |
| 5 | O1 | OO | Delta | 25.50 µV | 28.63 µV |
| 6 | O1 | OO | Theta | 18.23 µV | 21.95 µV |
| 7 | O1 | OZ | Theta | 27.02 µV | 42.18 µV |
| 8 | O1 | ZP | Theta | 18.04 µV | 26.39 µV |
| 9 | O1 | OO | Beta2 | 3.51 µV | 5.36 µV |
| 10 | O1 | ZP | Beta2 | 6.22 µV | 7.95 µV |

Test waliduje zachowanie: `test_classify_with_real_norms_config()` — `amplitude=0.0` dla każdej normy → 10× RED → WSKAZANIE (`tests/unit/test_algorithm.py:243–249`).

### 4. Jak filtr pasmowoprzepustowy wpływa na amplitudę (ścieżka "cicha")

Bandpass nie odrzuca próbek — **zmienia amplitudę** poprzez tłumienie poza pasmem. Waskie pasma (Beta1: 15–18 Hz = 3 Hz; Beta2: 18–25 Hz = 7 Hz) z definicji dają niższe amplitudy niż broadband. To jest celowe i normy (`mean_z`/`mean_k`) muszą być liczone z tymi samymi ustawieniami filtra.

**Ryzyko "cichego" błędu amplitudy:**
- Jeśli normy (`norms.json`) zostały obliczone przy innych ustawieniach filtra (inna kolejność, inny typ: butterworth/fir, inna częstotliwość odcięcia) niż to, co aktualnie stosuje MNE → amplitudy po filtracji będą systematycznie niższe lub wyższe od oczekiwanych → bias w kolorach.
- Aktualnie parametry filtra (`power_line_frequency`, `band_ranges`) są konfiguralne przez `norms.json`, ale typ filtra i rząd są pozostawione MNE domyślnie (FIR, hamming window). Brak dokumentacji, czy normy były obliczone z MNE defaultami.

### 5. Mechanizm fallbacku znacznikowego (hipoteza b — silniejsza)

```236:248:app/domain/pipeline.py
def detect_task_segments(raw: mne.io.BaseRaw) -> dict[str, tuple[float, float]]:
    _require_recording_duration(raw)
    segments = _segments_from_annotations(raw)
    if len(segments) == len(_TASK_ORDER):
        return {k: segments[k] for k in _TASK_ORDER}
    if not _collect_task_markers(raw):
        return _fallback_segments(raw)
    raise PipelineError(
        "missing_task_segments",
        ...
    )
```

**Drzewo decyzji:**

| Stan znaczników | Wynik |
|----------------|-------|
| Kompletne OO→OZ→ZP z adnotacji | Segmenty z adnotacji ✓ |
| **Zero rozpoznanych znaczników** | **Cichy fallback 3×3 min od t=0** ⚠️ |
| Częściowe (np. tylko OO+OZ) | `PipelineError("missing_task_segments")` |

**Lista aliasów jest hardkodowana** w `_TASK_KEYWORDS` (`pipeline.py:32–61`):

```32:61:app/domain/pipeline.py
_TASK_KEYWORDS: dict[str, tuple[str, ...]] = {
    "OO": ("OCZY OTWARTE", "OCZY OTW", "EYES OPEN", "EYESOPEN", "OPEN EYES", "OO"),
    "OZ": ("OCZY ZAMKNIETE", "OCZY ZAMK", "EYES CLOSED", "EYESCLOSED", "CLOSED EYES", "OZ"),
    "ZP": ("MATEMATYKA POZNAWCZA", "ZADANIE POZNAWCZE", ... "ZP"),
}
```

Nazwy spoza listy (np. `"Czynność podstawowa"`, `"Sesja 1"`, `"Kalibracja"`, `"Stymulacja"`) są **cicho pomijane** (`pipeline.py:151: continue`). Efekt: całe plik z takimi znacznikami → fallback → pierwsze 9 minut = często setup + kalibracja + przygotowanie (niska aktywność mózgu) → amplitudy poniżej norm → wszystko czerwone.

### 6. Jak to sprawdzić — konkretne kroki diagnostyczne

#### 6.1 Diagnoza hipotezy (b): czy fallback jest przyczyną? [Priorytet 1 — łatwy]

Dodaj tymczasowe logowanie do `detect_task_segments`:

```python
import logging
_log = logging.getLogger(__name__)

def detect_task_segments(raw: mne.io.BaseRaw) -> dict[str, tuple[float, float]]:
    _require_recording_duration(raw)
    segments = _segments_from_annotations(raw)
    if len(segments) == len(_TASK_ORDER):
        _log.debug("Segmenty z adnotacji: %s", segments)
        return {k: segments[k] for k in _TASK_ORDER}
    all_markers = _collect_task_markers(raw)
    _log.warning(
        "Brak rozpoznanych markerów zadań. Adnotacje w pliku: %s. Użyję fallback 3x3 min.",
        [a.description for a in raw.annotations] if raw.annotations else []
    )
    if not all_markers:
        return _fallback_segments(raw)
    raise PipelineError("missing_task_segments", ...)
```

**Co pokazuje:** Jeśli log zawiera `"Brak rozpoznanych markerów"` z listą adnotacji spoza `_TASK_KEYWORDS`, hipoteza (b) potwierdzona.

#### 6.2 Diagnoza hipotezy (a): czy filtr redukuje amplitudę do ≤ mean_z? [Priorytet 2]

Dodaj logowanie amplitud przed i po filtracji w `_amplitude_for_norm`:

```python
def _amplitude_for_norm(...) -> float:
    ...
    cropped = raw.copy().crop(tmin=t_start, tmax=t_end).pick([norm.channel])
    
    # DIAGNOZA: amplituda przed filtrami
    pre_filter_amp = float(np.mean(np.abs(cropped.get_data(units="uV"))))
    
    cropped.notch_filter(freqs=config.power_line_frequency, verbose=False)
    cropped.filter(l_freq=band.l_freq, h_freq=band.h_freq, verbose=False)
    
    # DIAGNOZA: amplituda po filtrach, przed gate'em
    post_filter_amp = float(np.mean(np.abs(cropped.get_data(units="uV"))))
    
    segment_data = cropped.get_data()[np.newaxis, ...]
    epochs = mne.EpochsArray(segment_data, cropped.info, verbose=False)
    epochs.drop_bad(reject={"eeg": _REJECT_EEG_VOLTS}, verbose=False)
    
    _log.debug(
        "Cell %s/%s/%s [%.1f–%.1fs]: pre=%.2fµV post=%.2fµV epochs=%d/1 mean_z=%.2f mean_k=%.2f",
        norm.channel, norm.task, norm.band, t_start, t_end,
        pre_filter_amp, post_filter_amp, len(epochs), norm.mean_z, norm.mean_k
    )
    ...
```

**Co szukamy w logu:**
- `post_filter_amp ≤ mean_z` → komórka będzie czerwona
- `pre_filter_amp >> post_filter_amp` → filtr mocno tłumi (normalne dla wąskich pasm, ale ratio powinien być stały)
- `epochs=0/1` → 200 µV gate się odpalił → błąd pojawi się użytkownikowi (nie all-red)

#### 6.3 Skrypt diagnostyczny (bez modyfikacji kodu produkcyjnego)

Napisz `scripts/diagnose_pipeline.py`:

```python
"""Uruchom: python scripts/diagnose_pipeline.py path/to/patient.edf"""
import sys, logging
import mne
from pathlib import Path
from app.domain.pipeline import _collect_task_markers, _segments_from_annotations, _fallback_segments
from app.domain.norms import load, resolve_norms_path

logging.basicConfig(level=logging.DEBUG)

path = Path(sys.argv[1])
raw = mne.io.read_raw_edf(str(path), preload=True, verbose=False)

print(f"\n=== Adnotacje w pliku ({len(raw.annotations)}) ===")
for ann in raw.annotations:
    print(f"  '{ann['description']}' @ {ann['onset']:.1f}s dur={ann['duration']:.1f}s")

markers = _collect_task_markers(raw)
print(f"\n=== Rozpoznane markery ({len(markers)}) ===")
for m in markers:
    print(f"  {m}")

segments = _segments_from_annotations(raw)
print(f"\n=== Segmenty z adnotacji: {segments}")

if not segments:
    fb = _fallback_segments(raw)
    print(f"=== FALLBACK 3x3 min: {fb} ===")
```

**Uruchom na pliku pacjenta i sprawdź, czy któraś adnotacja jest poza `_TASK_KEYWORDS`.**

---

## Architecture Insights

1. **Filtrowanie ≠ czyszczenie artefaktów** w tym kodzie. Bandpass jest metryką domeny (wycinamy pasmo do zbadania), nie usuwaniem zakłóceń. "Zbyt agresywne" w tradycyjnym sensie (ICA remove components) nie istnieje.

2. **Brama 200 µV jest binary** — albo cały segment przechodzi, albo cały odpada z widocznym błędem. Nigdy nie produkuje cicho niskich amplitud.

3. **RED = za niska amplituda** (poniżej normy Z pacjentów klinicznych). To oznacza, że all-red = amplitudy systematycznie poniżej 5–30 µV zależnie od pasma. Przyczyna: złe segmenty LUB niski sygnał w prawidłowych segmentach (rzadko klinicznie).

4. **Fallback jest cichy** — brak komunikatu ostrzegawczego w UI, brak logowania. Użytkownik nie wie, że markery nie zostały rozpoznane.

5. **`norms.json` nie zawiera aliasów znaczników** — nie można rozszerzyć listy przez konfigurację, tylko przez zmianę kodu (`pipeline.py:32–61`).

---

## Historical Context

- `context/archive/2026-06-03-eeg-pipeline-and-results/plan.md:56` — decyzja: 200 µV p-p, MVP bez ICA/autoreject
- `context/foundation/test-plan.md:35–36` — R4 wprost mówi o ryzyku all-red z nadmiernego czyszczenia; R5 — cichy fallback przy nieznanych aliasach
- `context/foundation/prd.md:99` — raport jakości artefaktów odłożony do v2.0
- `context/changes/eegdigitrack-native-reader/plan.md:27–28` — DigiTrack ZAWSZE trafi w fallback (brak tekstowych markerów w binarnym formacie)
- `docs/EEG-segmentacja.md:96–104` — przykłady nierozerwalnych adnotacji: `"Czynność podstawowa"`, `"Artefakt"`, `"Stymulacja akustyczna"`

---

## Open Questions

1. **Czy normy w `norms.json` zostały obliczone z tymi samymi ustawieniami filtra MNE (typ FIR, rząd, okno Hamminga)?** Jeśli nie, ratio pre/post amplitudy będzie nieprawidłowy dla populacji.
2. **Jakie konkretnie opisy znaczników mają pliki pacjentów (nie fixture'y)?** → **Odpowiedź poniżej w sekcji Follow-up.**
3. **Czy pacjenci mają nagrania ≥8 min z protokołem OO→OZ→ZP w kolejności?** → **Odpowiedź poniżej w sekcji Follow-up.**
4. **Czy DigiTrack `.eeg` jest typem nagrania u tych pacjentów?** → **TAK — i to jest jeden z problemów (Follow-up poniżej).**

---

## Code References

- `app/domain/pipeline.py:30` — `_REJECT_EEG_VOLTS = 200e-6` — jedyny próg artefaktów
- `app/domain/pipeline.py:32–61` — `_TASK_KEYWORDS` — pełna lista aliasów znaczników
- `app/domain/pipeline.py:137–155` — `_collect_task_markers()` — `continue` na nieznanych adnotacjach
- `app/domain/pipeline.py:236–248` — `detect_task_segments()` — logika fallbacku
- `app/domain/pipeline.py:299–338` — `_amplitude_for_norm()` — cały pipeline czyszczenia
- `app/domain/pipeline.py:331–336` — `PipelineError("artifact_rejection")` — widoczny błąd, nie all-red
- `app/domain/algorithm.py:17–22` — `_cell_color()` — RED gdy amplituda ≤ mean_z
- `norms.json:65–76` — 10 progów mean_z / mean_k per komórka
- `tests/unit/test_algorithm.py:243–249` — `amplitude=0.0` → wszystko RED → WSKAZANIE
- `tests/unit/test_pipeline.py:23–24` — fixture używa 50 µV < 200 µV

---

## Follow-up Research 2026-06-30: Diagnostyka na realnych plikach pacjentów

### Pliki zbadane

| Plik | Format | Czas | Kanały |
|------|--------|------|--------|
| `260116_000791_EEGok.edf` | EDF | 27.7 min | 31 (prefiks "EEG ") |
| `kobryń.EEG` | DigiTrack | 22.8 min | 19 |
| `Kuczyński.EEG` | DigiTrack | 22.9 min | 19 |

### 260116_000791_EEGok.edf — wyniki

| Krok | Wynik |
|------|-------|
| Adnotacje | 23 szt.: `"10:51:38 Oczy otwarte"`, `"10:54:06 Oczy zamknięte"`, `"10:56:40 zadanie poznawcze matematyka"`, `"Artefakt"` (×14), `"10:59:07 czynność podstawowa"` |
| Markery rozpoznane | 3/3 (OO @ 157.4s, OZ @ 305.9s, ZP @ 459.1s) |
| Ścieżka segmentacji | ADNOTACJE (poprawna) |
| Segment ZP | **6.5 sekundy** (459.1–465.6s — koniec wyznaczony przez `"Artefakt"` @ 465.6s) |
| pre_µV (broadband) | **2197.36 µV — identyczne dla WSZYSTKICH 10 komórek** |
| post_µV (po notch+bandpass) | **0.00 µV dla WSZYSTKICH 10 komórek** |
| Brama 200 µV | NIE wyzwolona |
| Kolor | **10× RED → WSKAZANIE** |

**Diagnoza:** Wartość `pre_µV = 2197.36 µV` identyczna dla C3 i O1 w każdym segmencie oznacza, że sygnał na tych kanałach jest w istocie stały (DC offset lub flat-line). Bandpass filtr z definicji usuwa DC → `post_µV = 0.00`. To nie jest problem nadmiernego czyszczenia — to problem z jakością nagrania. Brama 200 µV p-p nie odpala, bo peak-to-peak stałej wartości = 0.

Dodatkowy problem: **segment ZP trwa 6.5s**, bo `_segments_from_annotations` wyznacza koniec ZP przez następną adnotację — a nią jest `"Artefakt"` @ 465.6s (zaledwie 6.5s po starcie ZP). MNE zgłasza `RuntimeWarning: filter_length (1651) > signal (1633)`.

### kobryń.EEG i Kuczyński.EEG — wyniki

| Krok | kobryń | Kuczyński |
|------|--------|-----------|
| Adnotacje | BRAK | BRAK |
| Markery rozpoznane | 0 | 0 |
| Ścieżka segmentacji | **FALLBACK 3×3 min** | **FALLBACK 3×3 min** |
| pre_µV zakres | 4.7–6.4 µV | 6.9–9.6 µV |
| post_µV zakres | 1.1–3.9 µV | 1.8–5.0 µV |
| mean_z zakres (normy) | 3.5–30.4 µV | 3.5–30.4 µV |
| Komórki poniżej mean_z | **10/10** | **10/10** |
| Kolor | **10× RED** | **10× RED** |

**Diagnoza — dwie nakładające się przyczyny:**

1. **Brak adnotacji → fallback**: DigiTrack `.EEG` nigdy nie ma adnotacji w formacie tekstowym (stub `_digitrack_annotations` zwraca `None`). Pierwsze 9 minut od t=0 może zawierać setup/kalibrację zamiast protokołu OO→OZ→ZP.

2. **Amplitudy systematycznie za niskie**: Broadband pre-filter = 5–10 µV, podczas gdy normalny EEG dziecka wynosi 50–150 µV. Normy (`mean_z`) wymagają minimum 5–30 µV **po filtracji pasmowej**. Nawet najniższy próg (id 9: mean_z=3.51 µV dla O1/OO/Beta2) jest blisko post-filter wartości 1–2 µV. **Amplitudy DigiTrack są o rząd wielkości za niskie** — możliwa przyczyna: błędna kalibracja w `read_raw_digitrack()` lub normy liczone z innego sprzętu.

### Trzy stwierdzone przyczyny all-red

| # | Przyczyna | Plik | Dowód |
|---|-----------|------|-------|
| 1 | **DC offset / flat-line na kanałach** — bandpass usuwa DC → 0 µV | EDF | pre=2197µV, post=0.00µV |
| 2 | **Segment ZP = 6.5s** — za krótki dla filtra MNE, zniekształcony | EDF | RuntimeWarning, ZP koniec wyznaczony przez `"Artefakt"` |
| 3 | **DigiTrack: amplitudy 5-15× za niskie** — kalibracja lub niezgodność norm | .EEG | pre 5–10µV vs mean_z 20–42µV |
| 4 | **DigiTrack: fallback 3×3 min** — brak adnotacji, potencjalnie złe segmenty | .EEG | 0 markerów, fallback aktywny |

### Kolejne kroki

1. Dla EDF: zbadaj wizualnie C3/O1 — czy są flat-line przez całe nagranie? Sprawdź jednostki w nagłówku EDF (`physical_min`, `physical_max` dla tych kanałów).
2. Dla EDF: fix wyznaczania końca ZP — znacznik `"Artefakt"` nie powinien być znacznikiem końca segmentu zadania. Sprawdź `_segments_from_annotations` linia wyznaczająca `t_end` ZP.
3. Dla DigiTrack: zweryfikuj kalibrację w `eeg_file.py` — czy gain Elmiko EEG-1042 jest prawidłowo stosowany?
4. Dla DigiTrack: sprawdź na jakich plikach były liczone normy (EDF czy DigiTrack?) i czy użyto tych samych parametrów filtracji.
