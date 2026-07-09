---
date: 2026-07-09T07:58:00+02:00
researcher: Cursor Agent
git_commit: da8116201b5894314ae388c338c343162c8973df
branch: coursor/dev-env-setup-2f65
repository: NeuroFlag
topic: "Pipeline NeuroFlag vs metodologia eksperta ÔÇö wyr├│wnanie amplitud i norm"
tags: [research, pipeline, norms, amplitude, expert-alignment, digitrack, mitsar]
status: complete
last_updated: 2026-07-09T08:42:00+02:00
last_updated_by: Cursor Agent (walidacja: 3 pliki EDF eksperta)
pipeline_run: 2026-07-09
pipeline_commit: da8116201b5894314ae388c338c343162c8973df
---

# Research: Pipeline NeuroFlag vs metodologia eksperta ÔÇö wyr├│wnanie amplitud i norm

**Date**: 2026-07-09 (UTC+2)  
**Researcher**: Cursor Agent  
**Git Commit**: `da8116201b5894314ae388c338c343162c8973df`  
**Branch**: `coursor/dev-env-setup-2f65`  
**Repository**: NeuroFlag

## Research Question

Dlaczego wyniki NeuroFlag rozjad─ů si─Ö z ocen─ů eksperta na **trzech plikach referencyjnych** (`ok_EEG.edf`, `ADHD_EEG.edf`, `depresja_EEG.edf`)?
Czy problem le┼╝y w regule kolor├│w, normach, segmentacji, skali amplitud czy metodzie oblicze┼ä?
Jak wykorzysta─ç pliki CSV i korespondencj─Ö od eksperta do zamkni─Öcia luki?

**Zestaw walidacyjny eksperta** (pewniki, `D:\CVGOSI\NF dane\Testowe\`):

| Plik | Oczekiwany wynik kliniczny | Diagnoza |
|------|---------------------------|----------|
| `ok_EEG.edf` | **Brak wskaza┼ä** | Pacjent klinicznie bez wskaza┼ä (kontrola) |
| `ADHD_EEG.edf` | **Wskazanie** | ADHD |
| `depresja_EEG.edf` | **Wskazanie** | Depresja |

Te trzy pliki s─ů **jedynym autorytatywnym zestawem walidacyjnym** od eksperta. `Kuczy┼äski.EEG` (DigiTrack) to **osobny, historyczny przypadek** z wcze┼Ťniejszej pracy nad readerem ÔÇö **nie** nale┼╝y do powy┼╝szej tr├│jki i **nie dotyczy tego samego pacjenta** co ┼╝aden z plik├│w EDF.

## Summary

1. **Regu┼éa kolor├│w nie jest winna** ÔÇö klasyfikacja u┼╝ywa wszystkich 10 kom├│rek z `norms.json`; Matryca eksperta to progi norm, nie wynik pojedynczej kom├│rki (`handoff.md`).

2. **Skala amplitud NeuroFlag jest rz─Ödu wielko┼Ťci za niska** wzgl─Ödem norm i danych eksperta. Dla `ADHD_EEG.edf` (i historycznie `Kuczy┼äski.EEG`) pipeline daje ~2ÔÇô5 ┬ÁV po filtracji, podczas gdy normy i ┼Ťrednie grupowe eksperta dla Thety/Delty wskazuj─ů **~14ÔÇô30 ┬ÁV**. St─ůd systematyczne ÔÇ×czerwoneÔÇŁ kom├│rki ÔÇö tak┼╝e u pacjenta klinicznie bez wskaza┼ä (`ok_EEG.edf`), gdy sygna┼é na C3/O1 jest dost─Öpny do analizy.

3. **Metodologia eksperta r├│┼╝ni si─Ö od NeuroFlag co do kolejno┼Ťci i metryki:**
   - Ekspert: ICA / skrypty artefakt├│w **przed** podzia┼éem na pasma Ôćĺ analiza widmowa Mitsar Ôćĺ ÔÇ×u┼Ťredniona moc bezwzgl─Ödna w pa┼ŤmieÔÇŁ (surowe ┬ÁV w CSV).
   - NeuroFlag: notch Ôćĺ filtr pasma MNE Ôćĺ odrzucanie okien 1 s (pp > 200 ┬ÁV) Ôćĺ `mean(|┬ÁV|)` na sygnale przefiltowanym.

4. **`norms.json` jest sp├│jny ze skal─ů CSV eksperta** (stosunek ┼Ťrednich grupy Z do `mean_z` w normach: ~0.7ÔÇô0.96 dla Thety/Delty). Normy nie wymagaj─ů pierwszej kolejno┼Ťci przeskalowania w d├│┼é ÔÇö **pipeline musi produkowa─ç warto┼Ťci w tej samej skali co normy**.

5. **Pliki CSV eksperta nie zawieraj─ů mapowania na pliki testowe** (`ok_EEG.edf`, `ADHD_EEG.edf`, `depresja_EEG.edf`). `wyniki_indywidualne.csv` ma 82 anonimowe ID ÔÇö bez powi─ůzania nie da si─Ö domkn─ů─ç walidacji per pacjent ani por├│wna─ç 10 amplitud Mitsar z pipeline.

6. **Kierunek implementacji** (z handoff + ten research): dwuetapowe czyszczenie przed filtracj─ů, metryka bli┼╝sza mocy widmowej / workflow Mitsar, markery DigiTrack, kalibracja skali ÔÇö w tej kolejno┼Ťci priorytet├│w do ustalenia w `/10x-frame`.

7. **Pipeline run 2026-07-09** (zestaw eksperta + legacy Kuczy┼äski):
   - `ok_EEG.edf` (ekspert: brak wskaza┼ä) Ôćĺ **Wskazanie** (10├Ś red, ampÔëł0 na C3/O1 ÔÇö flat-line w pliku; rozjazd techniczny + kliniczny).
   - `ADHD_EEG.edf` (ekspert: wskazanie) Ôćĺ **Wskazanie** (10├Ś red) ÔÇö kategoria **przypadkowa** (all-red).
   - `depresja_EEG.edf` (ekspert: wskazanie) Ôćĺ **b┼é─ůd segmentacji** (brak ZP po fixie aliasu nadal ÔÇö marker obci─Öty / brak pe┼énej tr├│jki).
   - Stosunek NF/mean_z dla Thety/Delty ~**0.13ÔÇô0.35** (4ÔÇô7├Ś za nisko). Pipeline **nie rozr├│┼╝nia** ok vs ADHD przy obecnej metryce. Priorytet: metryka/skalowanie, potem segmentacja depresji.

## Detailed Findings

### 1. ┼╣r├│d┼éa danych eksperta

| Plik | Zawarto┼Ť─ç | Rola w wyr├│wnaniu |
|------|-----------|-------------------|
| `OdpowiedziBartka.txt` | Mail + notatki metodologiczne | Definicja workflow i normalizacji |
| `srednie_i_odchylenia_grupowe.csv` | ┼Ürednie/SD grup 1 (K) i 2 (Z) per warunek ├Ś kana┼é ├Ś pasmo | Por├│wnanie z `norms.json` (N=200) |
| `wyniki_indywidualne.csv` | 82 os├│b ├Ś 515 kolumn (Mitsar, surowe ┬ÁV) | Walidacja pipeline per nagranie ÔÇö **wymaga mapowania ID** |
| `Z1_pasma_statystyki.csv` | Testy r├│┼╝nic mi─Ödzygrupowych (p, t) | Research ADHD vs kontrola ÔÇö poza scope matrycy 10 kom├│rek |
| `Z2_pasma_klasyfikacja.csv` | Poprawno┼Ť─ç klasyfikacji K vs Z | Dob├│r elektrod/pasm ÔÇö informacyjnie |
| `Z3_polaczenia_statystyki.csv` | Statystyki par elektrod | Poza scope aplikacji przesiewowej |
| `Raport_QEEG.pdf` | Pe┼ény raport | Uzupe┼énienie opisu Mitsar ÔÇö nie odczytany automatycznie |
| `srednie_i_odchylenia_grupowe (1).csv` | Duplikat z drobnymi r├│┼╝nicami whitespace | Ten sam dataset co plik bez `(1)` |

┼Ücie┼╝ka bazowa: `D:\CVGOSI\NF dane\analiza eeg\`

### 2. Mapowanie warunk├│w i pasm

| NeuroFlag (`norms.json`) | CSV eksperta | Uwagi |
|--------------------------|--------------|-------|
| `OO` | `oczy otwarte` | 1:1 |
| `OZ` | `oczy zamkniete` | 1:1 |
| `ZP` | `poznawcze` | 1:1 |
| `Delta` 0.5ÔÇô4 Hz | `Delta` | Zakresy zgodne z `band_ranges` |
| `Theta` 4ÔÇô8 Hz | `Theta` | Zgodne |
| `Beta1` 15ÔÇô18 Hz | `Beta1_bez_SMR` | **Do potwierdzenia** ÔÇö stosunek norm/ekspert ~0.33 dla C3 ZP Beta1 |
| `Beta2` 18ÔÇô25 Hz | `Beta2` | Stosunek ~0.36ÔÇô0.66 ÔÇö mo┼╝liwa inna definicja pasma w Mitsar |

Ekspert u┼╝ywa dodatkowych cech (`Alpha`, `SMR`, `Pelna_Beta1`, stosunki `Theta_do_Alpha`) ÔÇö NeuroFlag ich nie liczy.

### 3. Metodologia eksperta (z `OdpowiedziBartka.txt`)

**Normalizacja z-score** (odj─Öcie ┼Ťredniej, podzielenie przez SD ┼é─ůcznej pr├│by):
- Stosowana **wy┼é─ůcznie** do wykres├│w str. 6ÔÇô8 raportu QEEG.
- **Nie** wp┼éywa na testy statystyczne ani tabele CSV ÔÇö tam s─ů **surowe ┬ÁV**.

**Pipeline eksperta (skr├│t):**
1. Filtry sprz─Ötowe przed nagraniem ÔÇö ignorowane w analizie.
2. Usuni─Öcie artefakt├│w (ruch, mruganie, napi─Öcie mi─Ö┼Ťni) skryptami / **ICA** ÔÇö **przed** podzia┼éem na pasma.
3. Analiza widmowa (Mitsar) Ôćĺ eksport tabel Ôćĺ kompilacja do `wyniki_indywidualne.csv`.
4. Agregacja grupowa Ôćĺ `srednie_i_odchylenia_grupowe.csv`.

**Rozjazd z NeuroFlag:** jeden etap (filtr pasma Ôćĺ odrzucanie okien 200 ┬ÁV pp) zamiast dwuetapowego czyszczenia + metryki widmowej.

### 4. Por├│wnanie `norms.json` vs ┼Ťrednie grupy Z eksperta

Dla 10 kom├│rek aplikacji (`norms.json`, kolumna `mean_z`) vs grupa `2 (Z)` w CSV:

| Task | Ch | Band | mean_z (norms) | Expert Z (CSV) | exp / norm |
|------|-----|------|----------------|----------------|------------|
| OZ | C3 | Theta | 30.35 | 22.36 | 0.74 |
| ZP | C3 | Theta | 20.32 | 18.33 | 0.90 |
| ZP | C3 | Beta1 | 5.26 | 1.74* | 0.33 |
| OO | C3 | Beta2 | 5.18 | 3.19 | 0.62 |
| OO | O1 | Delta | 25.50 | 20.91 | 0.82 |
| OO | O1 | Theta | 18.23 | 14.23 | 0.78 |
| OZ | O1 | Theta | 27.02 | 26.03 | **0.96** |
| ZP | O1 | Theta | 18.04 | 16.04 | 0.89 |
| OO | O1 | Beta2 | 3.51 | 2.31 | 0.66 |
| ZP | O1 | Beta2 | 6.22 | 2.23 | 0.36 |

\* Mapowanie `Beta1` Ôćĺ `Beta1_bez_SMR` ÔÇö niepewne.

**Interpretacja:** Normy w aplikacji s─ů w tej samej skali co dane eksperta (rz─Ödu 10ÔÇô30 ┬ÁV dla Thety). R├│┼╝nice 20ÔÇô40% mog─ů wynika─ç z innej pr├│by N, definicji Beta lub zaokr─ůgle┼ä ÔÇö **nie** z rz─Ödu wielko┼Ťci 5ÔÇô10├Ś.

### 5. Zestaw walidacyjny eksperta (3 pliki EDF)

┼Ücie┼╝ka: `D:\CVGOSI\NF dane\Testowe\`

| Plik | HIS / metadane | Oczekiwany wynik | Wynik NeuroFlag (2026-07-09) | Uwagi |
|------|----------------|------------------|------------------------------|-------|
| `ok_EEG.edf` | `000693`, Alicja, 2026-01-16 | **Brak wskaza┼ä** (kontrola kliniczna) | Wskazanie (10├Ś red, ampÔëł0) | **Duplikat bajtowy** `260116_000791_EEGok.edf`. Markery OO/OZ/ZP obecne. Na C3/O1 w segmentach protoko┼éu: **flat-line** (sta┼ée ~2197 ┬ÁV DC, pp=0 Ôćĺ po filtrze 0 ┬ÁV). Ekspert ocenia pacjenta klinicznie jako bez wskaza┼ä; plik wymaga wyja┼Ťnienia, czy ekspert analizowa┼é inne kana┼éy/eksport, czy to artefakt eksportu EDF. |
| `ADHD_EEG.edf` | `000682`, 2008-05-27 | **Wskazanie** (ADHD) | Wskazanie (10├Ś red) Ôťů kategoria | Markery OO/OZ OK; ZP obci─Öty: `"zadanie pozna"` ÔÇö alias z commit `6178904` naprawia segmentacj─Ö. Amplitudy ~2ÔÇô5 ┬ÁV ÔÇö all-red **nie** dowodzi zgodno┼Ťci metodyki. |
| `depresja_EEG.edf` | `000739`, DoKo-markery, 2008-05-27 | **Wskazanie** (depresja) | B┼é─ůd `missing_task_segments` | Wykryto OO i OZ; ZP (`"zadanie pozna"`) nie domyka tr├│jki w pipeline. Osobny pacjent od ADHD (inny hash, inny sygna┼é). |

**Weryfikacja to┼╝samo┼Ťci (2026-07-09):** ┼╝aden z trzech plik├│w EDF **nie** odpowiada pacjentowi `Michal_KUCZYNSKI` z `Kuczy┼äski.EEG` (DigiTrack, nagranie 03.04.2025, ur. 06-JUL-1996).

### 6. Legacy: `Kuczy┼äski.EEG` (DigiTrack, poza zestawem eksperta)

| Aspekt | Stan |
|--------|------|
| Plik | `D:\CVGOSI\NF dane\Testowe\Kuczy┼äski.EEG` |
| Pochodzenie | Wcze┼Ťniejsza praca nad readerem DigiTrack (`eegdigitrack-native-reader`), **nie** plik z paczki ÔÇ×pewnik├│wÔÇŁ eksperta |
| Segmentacja | Brak marker├│w OO/OZ/ZP Ôćĺ fallback 3├Ś3 min od t=0 |
| Amplitudy NeuroFlag | ~2ÔÇô5 ┬ÁV (10├Ś czerwony Ôćĺ Wskazanie) |
| Ocena eksperta (historyczna) | Brak wskaza┼ä ÔÇö ten sam wzorzec skali co EDF-y |
| Eksperyment `amplitude_method` | `peak_to_peak_half` daje ÔÇ×brakÔÇŁ dla Kuczy┼äskiego, ale psuje ADHD ÔÇö **┼╝adna pojedyncza metoda nie rozdziela wszystkich przypadk├│w** |

Przypadek Kuczy┼äskiego ilustruje ten sam problem skali i segmentacji DigiTrack, ale **walidacja kliniczna opiera si─Ö wy┼é─ůcznie na trzech plikach EDF** od eksperta.

### 7. `wyniki_indywidualne.csv`

- **82 wiersze**: 44├Ś `2 (Z)`, 38├Ś `1 (K)`.
- Kolumny: `id`, `grupa`, potem `{warunek} {kanal} {pasmo}` (515 kolumn).
- ID zanonimizowane (`1g11n7l`, ÔÇŽ) ÔÇö **brak powi─ůzania z plikami w `Testowe/`**.
- Warto┼Ťci w ┬ÁV, separator dziesi─Ötny przecinek, format zgodny ze skal─ů grupow─ů.

### 8. Pliki Z1ÔÇôZ3 (analiza badawcza)

- **Z1**: ranking cech pod k─ůtem test├│w t (np. O1 Theta OO, C3 Theta ZP ÔÇö najni┼╝sze p).
- **Z2**: klasyfikacja binarna K vs Z (np. C3 Theta OZ ~69% poprawno┼Ťci).
- **Z3**: statystyki par elektrod ÔÇö nieu┼╝ywane w matrycy 10 kom├│rek NeuroFlag.

Te pliki wyja┼Ťniaj─ů **dlaczego** wybrano C3/O1 i pasma Theta/Beta2 w badaniu N=200, ale **nie substitute** tabeli 10 amplitud dla konkretnego pacjenta.

### 9. Pipeline run 2026-07-09

Uruchomiono `app/domain/pipeline.run` + `classify` na commit `da8116201b5894314ae388c338c343162c8973df`, `norms.json` domy┼Ťlny. Kolumna **GrpZ** = ┼Ťrednia grupy Z z `srednie_i_odchylenia_grupowe.csv` (populacja N=200) ÔÇö **nie** amplituda pacjenta w Mitsar.

#### ok_EEG.edf ÔÇö ekspert: brak wskaza┼ä (kontrola kliniczna)

| # | Task | Ch | Band | NF ┬ÁV | mean_z | NF/mean_z | Kolor |
|---|------|-----|------|-------|--------|-----------|-------|
| 1ÔÇô10 | (wszystkie kom├│rki) | C3/O1 | * | **0.00** | 3.5ÔÇô42 | **0.00** | red |

- Nagranie: **1665 s** (27.7 min), **23 adnotacje**, segmentacja OO/OZ/ZP z marker├│w poprawna
- C3/O1 w segmentach protoko┼éu: flat-line (pp=0) Ôćĺ amp=0 po filtracji
- Wynik: **Wskazanie** (R=10) ÔÇö **rozjazd z ocen─ů kliniczn─ů eksperta** (brak wskaza┼ä)
- **Uwaga:** problem mo┼╝e le┼╝e─ç w eksporcie EDF (zerowy sygna┼é na kana┼éach domenowych), nie w ocenie klinicznej ÔÇö do wyja┼Ťnienia z ekspertem

#### ADHD_EEG.edf ÔÇö ekspert: wskazanie (ADHD)

| # | Task | Ch | Band | NF ┬ÁV | mean_z | NF/mean_z | GrpZ | NF/GrpZ | Kolor |
|---|------|-----|------|-------|--------|-----------|------|---------|-------|
| 1 | OZ | C3 | Theta | 3.80 | 30.35 | 0.13 | 22.36 | 0.17 | red |
| 2 | ZP | C3 | Theta | 3.92 | 20.32 | 0.19 | 18.33 | 0.21 | red |
| 3 | ZP | C3 | Beta1 | 1.67 | 5.26 | 0.32 | 1.74 | 0.96 | red |
| 4 | OO | C3 | Beta2 | 2.08 | 5.18 | 0.40 | 3.19 | 0.65 | red |
| 5 | OO | O1 | Delta | 8.89 | 25.50 | 0.35 | 20.91 | 0.43 | red |
| 6 | OO | O1 | Theta | 4.82 | 18.23 | 0.26 | 14.23 | 0.34 | red |
| 7 | OZ | O1 | Theta | 5.58 | 27.02 | 0.21 | 26.03 | 0.21 | red |
| 8 | ZP | O1 | Theta | 5.10 | 18.04 | 0.28 | 16.04 | 0.32 | red |
| 9 | OO | O1 | Beta2 | 2.39 | 3.51 | 0.68 | 2.31 | 1.04 | red |
| 10 | ZP | O1 | Beta2 | 2.45 | 6.22 | 0.40 | 2.23 | 1.10 | red |

- Nagranie: **1266 s** (21.1 min), **126 adnotacji**
- Segmenty z marker├│w: OOÔëł(65.3, 239.2) OZÔëł(239.2, 418.4) ZPÔëł(418.4, 598.4) s
- Wynik: **Wskazanie** (R=10, Y=0, G=0) ÔÇö kategoria zgodna z oczekiwaniem klinicznym, ale **mechanizm all-red**, nie poprawna metryka

#### depresja_EEG.edf ÔÇö ekspert: wskazanie (depresja)

- Nagranie: **1266 s** (21.1 min), **146 adnotacji**
- Markery: OOÔëł62.4 s, OZÔëł237.3 s; ZP (`"zadanie pozna"`) ÔÇö **pipeline nie domyka tr├│jki** Ôćĺ `missing_task_segments`
- Wynik: **analiza przerwana** ÔÇö wymaga fixu segmentacji ZP (ten sam alias co ADHD lub osobny wariant markera)

#### Legacy: Kuczy┼äski.EEG (poza zestawem eksperta)

| # | Task | Ch | Band | NF ┬ÁV | mean_z | NF/mean_z | Kolor |
|---|------|-----|------|-------|--------|-----------|-------|
| 1 | OZ | C3 | Theta | 4.99 | 30.35 | 0.16 | red |
| ÔÇŽ | ÔÇŽ | ÔÇŽ | ÔÇŽ | ~2ÔÇô5 | ÔÇŽ | ~0.13ÔÇô0.35 | red (├Ś10) |

- Nagranie: **1374 s**, **0 adnotacji**, fallback 3├Ś3 min od t=0
- Wynik historyczny: **Wskazanie** ÔÇö ten sam wzorzec skali co ADHD; **nie** u┼╝ywa─ç jako pewnik walidacji

#### Wnioski z runu

1. **Skala dominuje nad segmentacj─ů:** `ADHD_EEG.edf` ma poprawne segmenty, `ok_EEG.edf` te┼╝ ÔÇö oba daj─ů all-red (ok przez flat-line, ADHD przez ~2ÔÇô5 ┬ÁV). NF/mean_z ~0.13ÔÇô0.35 dla Thety/Delty (~**4ÔÇô7├Ś za nisko**).
2. **ADHD ÔÇ×trafiaÔÇŁ mechanizmem ubocznym:** regu┼éa Ôëą5 red Ôćĺ Wskazanie; przy all-red ka┼╝dy pacjent dostaje Wskazanie ÔÇö w tym kontrola kliniczna (`ok_EEG.edf`).
3. **Brak rozr├│┼╝nienia ok vs ADHD:** przy obecnej metryce oba profile s─ů ÔÇ×czerwoneÔÇŁ; po naprawie skali ADHD mo┼╝e straci─ç poprawn─ů klasyfikacj─Ö, je┼Ťli profil Mitsar nie jest patologiczny.
4. **depresja_EEG.edf blokuje si─Ö na segmentacji** ÔÇö osobny problem od skali; do naprawy przed walidacj─ů wskazania.
5. **Kuczy┼äski.EEG** ÔÇö ilustracja problemu DigiTrack (fallback segment├│w); nie wchodzi w macierz walidacji eksperta.

## Code References

- `app/domain/pipeline.py:315-387` ÔÇö `_mean_abs_after_artifact_rejection`, `_amplitude_for_norm` (notch Ôćĺ filtr Ôćĺ mean|┬ÁV|)
- `app/domain/algorithm.py` ÔÇö regu┼éy RAG (Ôëą5 red + ÔëĄ3 green Ôćĺ Wskazanie)
- `app/domain/norms.py` ÔÇö ┼éadowanie `norms.json`
- `norms.json:65-76` ÔÇö 10 wpis├│w norm (mean_z / mean_k)
- `app/domain/eeg_file.py` ÔÇö reader DigiTrack
- `context/changes/pipeline-expert-alignment/handoff.md` ÔÇö pe┼ény kontekst sesji 2026-07-08/09
- `scripts/compare_amplitude_methods.py` ÔÇö eksperyment metod (lokalnie, niezacommitowany)
- `scripts/diagnose_patient_files.py` ÔÇö diagnostyka segmentacji i amplitud

## Architecture Insights

1. **Normy s─ů ÔÇ×ekspertoweÔÇŁ, pipeline nie** ÔÇö `norms.json` potwierdzony przez eksperta 2026-05-29; CSV Bartka 2026 potwierdza skal─Ö ~10ÔÇô30 ┬ÁV. Pipeline time-domain daje ~2ÔÇô5 ┬ÁV na tych samych pasmach logicznych Ôćĺ systematyczne przekroczenie prog├│w w d├│┼é (czerwony).

2. **Metryka to osobny problem od segmentacji** ÔÇö fallback DigiTrack (legacy Kuczy┼äski) pogarsza wynik, ale sam w sobie nie t┼éumaczy 5ÔÇô10├Ś r├│┼╝nicy skali; ICA + widmo vs mean|uV| po filtrze to silniejsza hipoteza.

3. **Algorytm klasyfikacji jest stabilny** ÔÇö zmiana metody amplitudy bez zmiany norm mo┼╝e odwr├│ci─ç pojedynczy przypadek, ale nie zast─ůpi odwzorowania workflow eksperta.

4. **Brak warstwy ÔÇ×spectral powerÔÇŁ** ÔÇö ca┼éa aplikacja opiera si─Ö na MNE filtr + time-domain; ekspert na Mitsar (FFT / moc w pa┼Ťmie).

## Historical Context (from prior changes)

- `context/archive/2026-06-30-testing-critical-path-domain/research.md` ÔÇö sekcja Follow-up all-red cells
- `context/archive/2026-07-01-pipeline-signal-fidelity/` ÔÇö wcze┼Ťniejszy plan wierno┼Ťci sygna┼éu
- `context/changes/eegdigitrack-native-reader/` ÔÇö natywny reader `.EEG`; markery w nag┼é├│wku binarnym nadal otwarte
- Commit `6178904` ÔÇö alias `"ZADANIE POZNA"` dla obci─Ötego markera ZP w EDF

## Related Research

- `context/changes/pipeline-expert-alignment/handoff.md` ÔÇö handoff poprzedniej sesji
- `context/archive/2026-07-01-pipeline-signal-fidelity/` ÔÇö signal fidelity
- `D:\CVGOSI\NF dane\Matryca.docx` ÔÇö macierz norm eksperta (progi, nie wyniki pacjenta)

## Open Questions

1. **Mapowanie ID Ôćĺ pliki eksperta:** kt├│re `id` w `wyniki_indywidualne.csv` to `ok_EEG` / `ADHD_EEG` / `depresja_EEG`? Albo 10 amplitud Mitsar per plik.

2. **ok_EEG.edf ÔÇö flat-line vs ocena kliniczna:** ekspert ocenia pacjenta jako bez wskaza┼ä, ale C3/O1 w EDF maj─ů pp=0. Czy ekspert analizowa┼é inny eksport / inne kana┼éy? Czy potrzebny nowy plik kontrolny z realnym sygna┼éem na C3/O1?

3. **Definicja metryki Mitsar:** dok┼éadny wz├│r ÔÇ×u┼Ťrednionej mocy bezwzgl─Ödnej w pa┼ŤmieÔÇŁ (┬ÁV vs ┬ÁV┬▓, czy sqrt(moc)?), okno/epoki, czy identyczne z Matryc─ů.

4. **Beta1 / Beta2:** czy `Beta1_bez_SMR` w CSV = `Beta1` 15ÔÇô18 Hz w `norms.json`? Dlaczego stosunek exp/norm dla Beta jest ~0.33ÔÇô0.66?

5. **ICA:** parametry skrypt├│w eksperta, pr├│g odrzucenia segment├│w, kolejno┼Ť─ç wzgl─Ödem epok.

6. **depresja_EEG.edf ÔÇö segmentacja ZP:** dlaczego alias `"ZADANIE POZNA"` wystarcza dla ADHD, a nie dla depresji? Inny wariant opisu markera?

7. **Kalibracja ┬ÁV DigiTrack (legacy):** czy reader `eeg_file.py` poprawnie skaluje do ┬ÁV wzgl─Ödem Mitsar/EDF?

8. **Raport PDF:** sekcja opisuj─ůca liczenie ┼Ťrednich w Matrycy (Bartek obieca┼é w mailu) ÔÇö r─Öczna weryfikacja `Raport_QEEG.pdf`.

9. **Po naprawie skali ÔÇö regresja ADHD:** czy profil ADHD w Mitsar rzeczywi┼Ťcie daje Ôëą5 kom├│rek poni┼╝ej mean_z, czy poprawny wynik by┼é artefaktem all-red? Czy `ok_EEG` w skali Mitsar daje profil zielony?

## Recommended Next Steps

| Krok | Skill / akcja |
|------|----------------|
| 1 | Poprosi─ç eksperta o mapowanie ID (lub 10 amplitud Mitsar) dla **ok / ADHD / depresja** |
| 2 | Wyja┼Ťni─ç z ekspertem flat-line C3/O1 w `ok_EEG.edf` vs ocena ÔÇ×brak wskaza┼äÔÇŁ |
| 3 | `/10x-frame` ÔÇö priorytetyzacja: metryka vs ICA vs segmentacja depresji vs kalibracja |
| 4 | `/10x-plan @context/changes/pipeline-expert-alignment/research.md` |
| 5 | Implementacja fazowa; `/10x-research` tylko w─ůsko (np. marker ZP depresji) je┼Ťli plan tego wymaga |

**Nie** stosowa─ç pe┼énego `/10x-research` od zera ÔÇö codebase i handoff ju┼╝ zmapowane; brakuje dowodu numerycznego per **trzy pliki EDF eksperta**.
