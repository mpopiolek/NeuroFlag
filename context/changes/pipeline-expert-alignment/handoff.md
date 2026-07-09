# Handoff: NeuroFlag ÔÇö analiza pipeline vs ekspert (2026-07-08/09)

> Dokument do przekazania kontekstu nast─Öpnemu agentowi. U┼╝ytkownik ma dodatkowe pliki i informacje od eksperta ÔÇö do wgrania w nowej sesji.

## Cel rozmowy

U┼╝ytkownik analizowa┼é rozbie┼╝no┼Ťci mi─Ödzy wynikami aplikacji NeuroFlag a ocen─ů eksperta domenowego. G┼é├│wny przypadek: **Kuczy┼äski.EEG** ÔÇö ekspert: *brak wskaza┼ä*, aplikacja: *Wskazanie do dalszej diagnozy*. Podejrzenie u┼╝ytkownika: czy algorytm bierze pod uwag─Ö tylko **C3/Beta2/OO**.

---

## Najwa┼╝niejszy wniosek #1: Algorytm NIE opiera si─Ö na jednej kom├│rce

- Klasyfikacja u┼╝ywa **wszystkich 10 kom├│rek** z `norms.json`.
- Regu┼éy (`recommendation_rules`):
  - **Wskazanie:** Ôëą5 czerwonych **i** ÔëĄ3 zielonych
  - **Brak wskaza┼ä:** Ôëą4 zielonych **i** ÔëĄ3 czerwonych
  - Reszta Ôćĺ **Uwa┼╝na obserwacja**
- `Matryca.docx` (od eksperta) to **macierz norm** (progi ┼Ürednia Z / ┼Ürednia K), nie wyniki pacjenta. Kolorowa legenda przy C3/Beta2/OO wyja┼Ťnia znaczenie kolor├│w, nie oznacza ┼╝e tylko ta kom├│rka decyduje.

**Pliki norm:** `norms.json`, dokumentacja eksperta: `D:\CVGOSI\NF dane\Matryca.docx`

---

## Najwa┼╝niejszy wniosek #2: Problem le┼╝y w pipeline, nie w regule kolor├│w

### Kuczy┼äski.EEG (DigiTrack `.EEG`)

- **Wynik aplikacji:** 10├Ś czerwony Ôćĺ Wskazanie
- **Amplitudy po filtracji:** ~2ÔÇô5 ┬ÁV (wszystkie kom├│rki)
- **Normy mean_z:** ~3.5ÔÇô42 ┬ÁV ÔÇö systematycznie za niskie
- **Segmentacja:** brak adnotacji OO/OZ/ZP Ôćĺ **fallback 3├Ś3 min od t=0** (0ÔÇô540 s z ~23 min nagrania)
- Plik: `D:\CVGOSI\NF dane\Testowe\Kuczy┼äski.EEG`
- Ekspert oceni┼é: **brak wskaza┼ä**

### Przyczyny rozjazdu (nak┼éadaj─ůce si─Ö)

1. **DigiTrack bez marker├│w** ÔÇö zawsze fallback 3├Ś3 min; pierwsze 9 min mog─ů by─ç setup, nie protok├│┼é OOÔćĺOZÔćĺZP
2. **Skala amplitud** ÔÇö broadband ~7ÔÇô10 ┬ÁV, po filtrze ~2ÔÇô5 ┬ÁV vs normy wymagaj─ůce 18ÔÇô42 ┬ÁV dla Theta; mo┼╝liwa niezgodno┼Ť─ç kalibracji DigiTrack vs spos├│b liczenia norm (N=200)
3. **Metoda oblicze┼ä** ÔÇö pipeline: `mean(abs(┬ÁV))` po notch + filtr pasma MNE; ekspert prawdopodobnie Excel, inna kolejno┼Ť─ç krok├│w

### Eksperyment metod amplitudy (NIE zacommitowane, lokalnie w workspace)

Dodano prototypowo `app/domain/amplitude.py`, pole `amplitude_method` w norms (cofni─Öte przed commitem), skrypt `scripts/compare_amplitude_methods.py`.

| Metoda | Kuczy┼äski (ekspert: brak) | ADHD (oczekiwane: wskazanie) |
|--------|---------------------------|------------------------------|
| `mean_abs` (domy┼Ťlna) | Wskazanie ÔŁî | Wskazanie Ôťů |
| `peak_to_peak_half` | Brak Ôťů | Brak ÔŁî |

**┼╗adna pojedyncza metoda nie rozr├│┼╝nia wszystkich przypadk├│w.** Potrzebne por├│wnanie z liczbami z Excela eksperta.

---

## Pliki referencyjne EDF (od u┼╝ytkownika)

┼Ücie┼╝ka: `D:\CVGOSI\NF dane\Testowe\`

| Plik | Oczekiwanie kliniczne | Wynik pipeline (mean_abs) | Uwagi |
|------|----------------------|---------------------------|-------|
| `ok_EEG.edf` | Brak wskaza┼ä (wzorcowe nagranie) | Wskazanie (10├Ś red, ampÔëł0) | **Identyczny hash** co `260116_000791_EEGok.edf`. C3/O1 (i inne kana┼éy) = **flat-line** (pp=0, sta┼ée ~2197 ┬ÁV DC). Po filtrze Ôćĺ 0 ┬ÁV. To **referencja formatu/protoko┼éu**, nie plik z poprawnym sygna┼éem do walidacji. |
| `ADHD_EEG.edf` | ADHD Ôćĺ wskazanie | Przed fixem: b┼é─ůd segmentacji; po fixie aliasu: Wskazanie Ôťů | Markery OO/OZ OK; ZP obci─Öty: `"zadanie pozna"` |
| `depresja_EEG.edf` | Depresja Ôćĺ wskazanie | B┼é─ůd `artifact_rejection` na OZ | Ten sam problem markera ZP; segment OZ ma pp ~527ÔÇô553 ┬ÁV |

---

## Commit wykonany w tej rozmowie

**Commit `6178904`** (tylko alias, reszta niezacommitowana):

```
fix(pipeline): rozpoznawaj obciety marker ZP zadanie pozna w EDF
```

- `app/domain/pipeline.py` ÔÇö dodany alias `"ZADANIE POZNA"` w `_TASK_KEYWORDS["ZP"]`
- `tests/unit/test_pipeline.py` ÔÇö `test_detect_task_segments_zp_alias_truncated_zadanie_pozna`

**Branch:** `coursor/dev-env-setup-2f65` (ahead of origin by 5 commits po tym commicie)

---

## Stan pipeline artefakt├│w (istniej─ůcy kod, nie z tej rozmowy)

W `app/domain/pipeline.py` jest `_mean_abs_after_artifact_rejection`:

- Dzieli sygna┼é **po filtracji pasma** na okna **1 s**
- Wyrzuca okna z peak-to-peak > **200 ┬ÁV**
- Liczy `mean(|uV|)` z pozosta┼éych okien
- Je┼Ťli **zero** czystych okien Ôćĺ `PipelineError(artifact_rejection)`

To bli┼╝ej ÔÇ×wycinania fragment├│wÔÇŁ ni┼╝ stara wersja (odrzucenie ca┼éego segmentu), ale **nie** odwzorowuje pe┼énego workflow eksperta.

---

## Workflow eksperta (informacja od u┼╝ytkownika)

Ekspert pracowa┼é **r─Öcznie (Excel)**, w kolejno┼Ťci:

1. **Usuni─Öcie zaburzonych fragment├│w** ÔÇö wyci─Öcie odcink├│w z bardzo du┼╝ymi pikami amplitudy
2. **Usuni─Öcie artefakt├│w** ÔÇö ruch, mruganie, napi─Öcie mi─Ö┼Ťni, padaczka
3. **Dopiero potem** analiza amplitud i por├│wnanie z normami

### Rozjazd z NeuroFlag

- My: filtr pasma Ôćĺ potem odrzucanie okien (jeden etap, jeden pr├│g 200 ┬ÁV)
- Ekspert: dwa etapy czyszczenia **przed** lub niezale┼╝nie od filtracji pasmowej
- Normy (mean Z/K) liczone na danych **po r─Öcznym czyszczeniu** ÔÇö st─ůd rozjazd skali

### Do doprecyzowania z ekspertem

- Pr├│g ┬ÁV dla ÔÇ×du┼╝ych pik├│wÔÇŁ
- Czy wycina┼é ca┼ée sekundy czy pojedyncze pr├│bki
- Kolejno┼Ť─ç: czyszczenie przed czy po podziale na pasma
- **10 liczb amplitud z Excela** dla jednego znanego pliku (np. ADHD) ÔÇö klucz do odtworzenia metody

---

## Proponowany kierunek implementacji (nie zrobione)

1. **Pass 1 (broadband, przed filtrem pasma):** wyrzu─ç okna 1 s z pp > X ┬ÁV
2. **Pass 2:** artefakty ruchowe/mruganie (heurystyki lub ten sam pr├│g na przefiltrowanym)
3. **Filtr pasma Ôćĺ mean(|uV|)** z czystych okien
4. **Minimum czystych danych** (np. Ôëą30 s z 180 s segmentu)
5. **DigiTrack:** dekodowanie marker├│w z nag┼é├│wka binarnego (blok ~0x09C0ÔÇô0x0A4E0) zamiast fallback od t=0
6. **Kalibracja DigiTrack** ÔÇö weryfikacja skali ┬ÁV vs normy N=200

---

## Lokalne pliki robocze (niezacommitowane, mog─ů za┼Ťmieca─ç workspace)

- `app/domain/amplitude.py` ÔÇö eksperymentalne metody amplitudy
- `tests/unit/test_amplitude.py`
- `scripts/compare_amplitude_methods.py`, `scripts/diagnose_patient_files.py`
- Zmiany w: `norms.py`, `types.py`, `norms.json.template`, `test_norms.py` (amplitude_method ÔÇö cofni─Öte z commita, mog─ů by─ç nadal lokalnie)
- `context/changes/eegdigitrack-native-reader/plan-brief.md`

---

## Kluczowe ┼Ťcie┼╝ki i dokumentacja w repo

| Co | Gdzie |
|----|-------|
| Algorytm kolor├│w | `app/domain/algorithm.py` |
| Pipeline EEG | `app/domain/pipeline.py` |
| Normy | `norms.json` |
| Reader DigiTrack | `app/domain/eeg_file.py` |
| Research all-red | `context/archive/2026-06-30-testing-critical-path-domain/research.md` (sekcja Follow-up 2026-06-30) |
| Plan signal fidelity | `context/archive/2026-07-01-pipeline-signal-fidelity/` |
| Pliki testowe | `D:\CVGOSI\NF dane\Testowe\` |
| Matryca norm eksperta | `D:\CVGOSI\NF dane\Matryca.docx` |

---

## Co u┼╝ytkownik ma od eksperta (do wgrania w nowej sesji)

U┼╝ytkownik wspomnia┼é, ┼╝e ma **pliki i informacje od eksperta**, ale zajm─ů du┼╝o kontekstu ÔÇö w tej rozmowie **nie by┼éy szczeg├│┼éowo analizowane** poza `Matryca.docx` (macierz norm) i screenshotem z progami. Nast─Öpny agent powinien poprosi─ç o:

- konkretne amplitudy z Excela per kom├│rka dla 1ÔÇô2 znanych przypadk├│w (Kuczy┼äski, ADHD),
- opis dok┼éadnej procedury czyszczenia (progi, okna czasowe),
- ewentualnie nowy plik kontrolny `ok` z realnym sygna┼éem EEG (nie flat-line).
