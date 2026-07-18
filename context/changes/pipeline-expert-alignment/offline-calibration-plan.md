---
date: 2026-07-09T08:52:00+02:00
author: Cursor Agent
status: draft
related: [research.md, handoff.md]
---

# Plan kalibracji offline ÔÇö bez dodatkowych danych od eksperta

**Data:** 2026-07-09  
**Kontekst:** `pipeline-expert-alignment`  
**Za┼éo┼╝enie:** nie otrzymamy mapowania ID Ôćĺ pliki testowe, 10 amplitud Mitsar per pacjent ani szczeg├│┼éowej procedury ICA.

## Cel

Zbli┼╝y─ç pipeline NeuroFlag do ocen eksperta **bez bezpo┼Ťredniego kontaktu**, wykorzystuj─ůc:

- dane populacyjne z CSV (82 osoby, skala Mitsar),
- dwa pliki EDF z etykiet─ů kliniczn─ů (ADHD, depresja),
- analiz─Ö profili amplitud wzgl─Ödem `norms.json`.

Zestaw walidacyjny eksperta (pewniki): `ok_EEG.edf`, `ADHD_EEG.edf`, `depresja_EEG.edf` ÔÇö patrz `research.md`.

---

## Co ju┼╝ mamy (bez eksperta)

| Zas├│b | Do czego s┼éu┼╝y |
|-------|----------------|
| `wyniki_indywidualne.csv` (82 os├│b, amplitudy Mitsar) | **Offline oracle** ÔÇö wiadomo, jakie warto┼Ťci daje metoda eksperta |
| `srednie_i_odchylenia_grupowe.csv` + `norms.json` | Potwierdzenie skali norm (~10ÔÇô30 ┬ÁV) |
| `ADHD_EEG.edf` | Etykieta kliniczna: **Wskazanie** (ADHD) |
| `depresja_EEG.edf` | Etykieta kliniczna: **Wskazanie** (depresja) ÔÇö wymaga fixu segmentacji ZP |
| `ok_EEG.edf` | Etykieta kliniczna: **Brak wskaza┼ä** ÔÇö ale C3/O1 = flat-line w pliku (s┼éaby technicznie) |

### Kluczowy wniosek z analizy CSV (2026-07-09)

Klasyfikacja **amplitud Mitsar** (nie pipeline) algorytmem NeuroFlag na 82 wierszach:

| Kategoria (algorytm) | n | Mediana `amp/mean_z` (profil) |
|----------------------|---|-------------------------------|
| Wskazanie | 60 | Ôëł **0.63** (nisko Ôćĺ czerwone) |
| Brak wskaza┼ä | 6 | Ôëł **1.38** (wy┼╝ej Ôćĺ zielone) |
| Uwa┼╝na obserwacja | 16 | Ôëł **1.14** |

Obecny pipeline na `ADHD_EEG.edf` daje `NF/mean_z` Ôëł **0.13ÔÇô0.35** ÔÇö **za nisko nawet wzgl─Ödem profilu ÔÇ×WskazanieÔÇŁ w skali eksperta** (~0.63).

**Implikacja:** celem nie jest prosty globalny mno┼╝nik ├Ś5, lecz doprowadzenie pipeline do **tego samego zakresu co Mitsar** (ratio ~0.6 vs ~1.4), a nie do obecnych ~0.2.

Mapowanie 10 kolumn CSV Ôćĺ kom├│rki matrycy (znane):

| Task | Ch | Band | Kolumna CSV |
|------|-----|------|-------------|
| OZ | C3 | Theta | `oczy_zamkniete C3 Theta` |
| ZP | C3 | Theta | `poznawcze C3 Theta` |
| ZP | C3 | Beta1 | `poznawcze C3 Beta1_bez_SMR` |
| OO | C3 | Beta2 | `oczy_otwarte C3 Beta2` |
| OO | O1 | Delta | `oczy_otwarte O1 Delta` |
| OO | O1 | Theta | `oczy_otwarte O1 Theta` |
| OZ | O1 | Theta | `oczy_zamkniete O1 Theta` |
| ZP | O1 | Theta | `poznawcze O1 Theta` |
| OO | O1 | Beta2 | `oczy_otwarte O1 Beta2` |
| ZP | O1 | Beta2 | `poznawcze O1 Beta2` |

---

## Testy mo┼╝liwe bez eksperta

### 1. Shadow validation na CSV (najwy┼╝sza warto┼Ť─ç)

Dla ka┼╝dej wersji pipeline / metryki:

1. Pobierz 10 kolumn z CSV odpowiadaj─ůcych kom├│rkom matrycy.
2. Klasyfikuj 82 wiersze Ôćĺ rozk┼éad kategorii w skali eksperta.
3. Oblicz centroidy profili `amp/mean_z` per kategoria (Wskazanie / Brak / Obserwacja).

**Kryterium sukcesu wariantu pipeline:** profil 10 amplitud z EDF (ADHD, depresja) jest **bli┼╝ej centroidu ÔÇ×WskazanieÔÇŁ** ni┼╝ centroidu ÔÇ×BrakÔÇŁ ÔÇö bez mapowania ID na konkretny wiersz.

### 2. Sweep metod amplitudy

Prototyp: `scripts/compare_amplitude_methods.py`, `app/domain/amplitude.py`.

| Metoda | Hipoteza |
|--------|----------|
| `mean_abs` (obecna) | Za niska |
| `rms` | ~├Ś1.25 vs mean_abs |
| Welch / ÔłÜPSD (moc widmowa) | Bli┼╝ej Mitsar (FFT) |
| `epoch_mean_abs` | Bli┼╝ej r─Öcznego liczenia w Excelu |
| `peak_to_peak_half` | Odrzucona ÔÇö psuje ADHD |

### 3. Sweep kolejno┼Ťci czyszczenia artefakt├│w

Warianty bez ICA (przybli┼╝enie workflow eksperta):

- Pass 1: odrzucanie okien broadband **przed** filtrem pasma.
- Pass 2: obecny pr├│g 200 ┬ÁV pp po filtrze.
- Progi: 100 / 150 / 200 / 300 ┬ÁV.
- Minimum czystego segmentu: 30 / 60 / 90 s z 180 s.

Por├│wnanie: odleg┼éo┼Ť─ç profilu ADHD od centroidu CSV ÔÇ×WskazanieÔÇŁ.

### 4. Kalibracja skali (ostro┼╝nie)

Mediana `NF/mean_z` na ADHD Ôëł 0.3 Ôćĺ teoretyczny mno┼╝nik ~3.3 zbli┼╝a do ~0.6.

**Ograniczenie:** globalny gain **nie rozdziela** ok vs ADHD ÔÇö oba id─ů w t─Ö sam─ů stron─Ö. To co najwy┼╝ej krok po┼Ťredni; rozr├│┼╝nienie wymaga **innej metryki** (widmo), nie samego wsp├│┼éczynnika.

### 5. Naprawa segmentacji `depresja_EEG.edf`

Drugi plik EDF z etykiet─ů ÔÇ×WskazanieÔÇŁ ÔÇö fix markera ZP odblokowuje trzeci constraint w sweepie. Bez tego optymalizacja opiera si─Ö na jednym EDF + CSV.

### 6. Diagnostyka `ok_EEG.edf`

Pacjent klinicznie **bez wskaza┼ä**, ale w pliku:

- C3, O1 (kana┼éy domenowe) = flat-line (pp=0).
- T3, T4, O2 maj─ů sygna┼é ÔÇö prawdopodobny problem eksportu/monta┼╝u EDF.

Test eksperymentalny: pipeline na O2 zamiast O1 ÔÇö czy profil wchodzi w skal─Ö? Nie jest to rozwi─ůzanie docelowe, ale rozr├│┼╝nia problem metryki od uszkodzonego kana┼éu.

### 7. Sygna┼éy syntetyczne

Sinusoidy w pasmach Theta/Beta (15 / 25 / 35 ┬ÁV) Ôćĺ weryfikacja ┼éa┼äcucha `norms.json` + `classify()` niezale┼╝nie od eksperta.

---

## Proponowana kolejno┼Ť─ç prac

```
Fix segmentacji depresja
    Ôćĺ Sweep metryk + czyszczenia (ADHD + depresja)
        Ôćĺ Por├│wnanie profili z centroidami CSV Mitsar
            Ôćĺ Wyb├│r wariantu minimalizuj─ůcego odleg┼éo┼Ť─ç od profilu ÔÇ×WskazanieÔÇŁ
                Ôćĺ Regresja na CSV: czy rozk┼éad 82 profili nadal sensowny
                    Ôćĺ ok_EEG: je┼Ťli C3/O1 flat Ôćĺ pomi┼ä w EDF, polegaj na profilu ÔÇ×BrakÔÇŁ z CSV
```

---

## Czego nie da si─Ö zrobi─ç bez eksperta

1. **Potwierdzi─ç** zgodno┼Ť─ç `ok_EEG.edf` z ocen─ů kliniczn─ů na C3/O1 ÔÇö plik jest technicznie wadliwy na kana┼éach domenowych.
2. **Zagwarantowa─ç** zgodno┼Ť─ç z ocen─ů kliniczn─ů eksperta ÔÇö nawet na samych danych Mitsar algorytm daje tylko 6/82 ÔÇ×Brak wskaza┼äÔÇŁ; ekspert m├│g┼é u┼╝ywa─ç szerszego kontekstu ni┼╝ 10 kom├│rek.
3. **Odtworzy─ç ICA** 1:1 ÔÇö bez parametr├│w skrypt├│w to przybli┼╝enie.

---

## Prognoza skuteczno┼Ťci

| Dzia┼éanie | Szansa na popraw─Ö | Bez eksperta? |
|-----------|-------------------|---------------|
| Metryka widmowa (Welch/PSD) zamiast mean\|uV\| | **Wysoka** | Tak |
| Dwuetapowe czyszczenie artefakt├│w | **┼ÜredniaÔÇôwysoka** | Tak |
| Fix segmentacji depresji | **Konieczne** | Tak |
| Shadow validation na 82 wierszach CSV | **Bardzo wysoka** (jako target) | Tak |
| Globalny mno┼╝nik ├Ś3 | Niska (all-red zostaje) | Tak, ale ma┼éo |
| Walidacja `ok_EEG.edf` na C3/O1 | **Brak** dop├│ki flat-line | Nie w pe┼éni |

---

## Rekomendacja

Traktowa─ç `wyniki_indywidualne.csv` jako **zast─Öpczy ground truth skali i profili**, a `ADHD_EEG.edf` + `depresja_EEG.edf` jako **dwie kotwice EDF**. Optymalizowa─ç pipeline tak, by profil 10 amplitud by┼é statystycznie bliski centroidom Mitsar ÔÇö **bez mapowania ID**.

Kolejny krok implementacyjny (opcjonalny): skrypt `scripts/calibrate_against_expert_csv.py` ÔÇö sweep metod + odleg┼éo┼Ť─ç od centroid├│w CSV + raport dla ADHD/depresja.

---

## Powi─ůzane pliki

- `context/changes/pipeline-expert-alignment/research.md` ÔÇö pe┼ény research
- `context/changes/pipeline-expert-alignment/handoff.md` ÔÇö kontekst sesji 2026-07-08/09
- `D:\CVGOSI\NF dane\analiza eeg\wyniki_indywidualne.csv` ÔÇö dane Mitsar N=82
- `scripts/compare_amplitude_methods.py` ÔÇö istniej─ůcy sweep metod
