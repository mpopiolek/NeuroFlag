# Manual QA — mapowanie plików na testy (S-02)

Pliki EEG **nie są w repozytorium** (`.gitignore`). Użyj ścieżek lokalnych poniżej.

**Reguły segmentacji (znaczniki, min. 8 min):** [`docs/EEG-segmentacja.md`](../../docs/EEG-segmentacja.md)

## Wymagania pliku do analizy przesiewowej

- Nagranie **≥ 8 min**
- **Albo** trzy znaczniki **OO → OZ → ZP** w kolejności, **albo** brak znaczników zadań → fallback 3×3 min od początku
- Kanały **C3** i **O1** (po aliasach lub pickerze)
- Częściowe znaczniki (np. tylko OO/OZ) → błąd, bez analizy

## Lokalizacje plików

| Źródło | Ścieżka |
|--------|---------|
| Pliki produkcyjne (prawdziwe) | `D:\CVGOSI\NF dane\Testowe\` |
| Pliki syntetyczne (generowane) | `tests\fixtures\` — `python tests/fixtures/generate_test_edfs.py` |

## Uruchomienie

**GUI (pełny flow):**
```powershell
cd d:\CVGOSI\NeuroFlag
python app/main.py
```

**Sonda pipeline (bez okna — szybka weryfikacja kroków 1.3 / 1.4):**
```powershell
python tests/fixtures/probe_pipeline.py "D:\CVGOSI\NF dane\Testowe\260116_000791_EEGok.edf"
python tests/fixtures/probe_pipeline.py --dir "D:\CVGOSI\NF dane\Testowe"
```

**Spowolnienie analizy (tylko test anulowania 3.5):**
```powershell
python app/main.py --debug-slow-analysis=3
```

**Metryka przykładowa (większość testów):** wiek 8, płeć dowolna, bez wykluczeń klinicznych.

---

## Mapowanie: test → plik

### Faza 1 — pipeline

| Test | Plik | Oczekiwany wynik |
|------|------|------------------|
| **1.3** Pipeline OK | `260116_000791_EEGok.edf` | Sonda/GUI: `OK`, siatka wyników |
| **1.3** (syntetyczny) | `tests\fixtures\test_standard.edf` | Pełne znaczniki OO/OZ/ZP |
| **1.4** Brak C3/O1 | `LIGHT.edf` | `missing_channels` |
| **1.4** Brak znaczników (fallback) | `D0000212.EDF` | ≥8 min, brak adnotacji → fallback 3×3 min |
| **1.4** Za krótkie nagranie | `230615_000351_EEGok.edf` | `insufficient_duration` (&lt; 8 min) |
| **1.4** Brak ZP w kolejności | `230915_000372_EEG.edf` | `missing_task_segments` (brak znacznika ZP) |

### Faza 3 — UI

| Test | Plik | Uwagi |
|------|------|-------|
| **3.4** Pełny flow | `260116_000791_EEGok.edf` | Bez µV w UI |
| **3.5a** Błąd pipeline | `230915_000372_EEG.edf` | Częściowe znaczniki → PL + Szczegóły + powrót |
| **3.5b** Anuluj | `260116_…` + `--debug-slow-analysis=3` | |
| **3.6** Czas ≤ 10 min | `260116_000791_EEGok.edf` | |

### Faza 4 — picker

| Test | Plik |
|------|------|
| **4.3** / **4.4** | `tests\fixtures\test_bad_channels.edf` |

---

## Pliki — szybka ściągawka

| Plik | Nadaje się do |
|------|----------------|
| `260116_000791_EEGok.edf` | **Główny plik QA** — OO/OZ/ZP, ≥8 min |
| `D0000212.EDF` | Fallback 3×3 min (brak znaczników, ~17 min) |
| `230915_000372_EEG.edf` | Błąd: brak ZP (`missing_task_segments`) |
| `230615_000351_EEGok.edf` | Błąd: &lt; 8 min |
| `LIGHT.edf` | Błąd: brak C3/O1 |
| `test_standard.edf` | Syntetyczny sukces |
| `test_no_annotations.edf` | Syntetyczny fallback 3×3 min (≥8 min, bez adnotacji) |
| `test_bad_channels.edf` | Picker kanałów |

---

## Checklist (plan S-02)

- [x] 1.3 Pipeline na `.edf` — 10 wartości, bez NaN
- [x] 1.4 Plik bez C3/O1 — `PipelineError` po polsku
- [x] 3.4 Flow metryka → import → Analizuj → wyniki bez µV
- [x] 3.5a Błąd pipeline — PL + Szczegóły + powrót
- [x] 3.5b Anuluj — `--debug-slow-analysis=3`
- [x] 3.6 Czas ≤ 10 min
- [x] 4.3 Picker — mapowanie → sukces
- [x] 4.4 Anuluj w pickerze

Potwierdzone: manual QA 2026-06-11 (przed zmianą reguł segmentacji 2026-06-11 — ponowna weryfikacja zalecana po tej aktualizacji).
