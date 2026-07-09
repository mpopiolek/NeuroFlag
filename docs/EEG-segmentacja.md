# Segmentacja nagrań EEG — reguły domenowe

> Źródło: wymagania eksperta domenowego (2026-06-11). Obowiązuje pipeline `app/domain/pipeline.py`.

## Kiedy można wykonać analizę przesiewową

### Warunek wspólny

Nagranie musi trwać **co najmniej 8 minut** (480 s). Krótsze → `insufficient_duration`, brak wskazań.

### Ścieżka A — znaczniki OO → OZ → ZP

Gdy w pliku da się znaleźć **trzy znaczniki** zadań w poprawnej kolejności (patrz niżej), segmenty wyznaczamy **z adnotacji** — pierwszy OO nie musi być w `t = 0`.

### Ścieżka B — brak znaczników zadań (fallback)

Gdy plik ma **≥ 8 min** i **nie zawiera żadnego** rozpoznanego znacznika OO/OZ/ZP, stosujemy **fallback**: trzy kolejne okna **3 min** od początku nagrania:

| Segment | Domyślny zakres |
|---------|-----------------|
| OO | 0:00 – 3:00 |
| OZ | 3:00 – 6:00 |
| ZP | 6:00 – 9:00 |

Przy nagraniu 8–9 min trzeci segment może być krótszy niż 3 min (kończy się na końcu pliku).

### Kiedy analiza **nie** jest możliwa

- nagranie **&lt; 8 min**;
- są **częściowe** znaczniki (np. tylko OO i OZ, bez ZP) — fallback **nie** obowiązuje; komunikat `missing_task_segments`.

W takich przypadkach aplikacja kończy pipeline komunikatem po polsku — **bez wskazań**.

## Jak operator nagrywa

Obsługujący aparat często uruchamia **zapis i nagranie jednocześnie**. Wtedy:

- pierwszy rozpoznany znacznik **OO** rozpoczyna sekcję oczu otwartych (niekoniecznie w `t = 0`);
- kolejne sekcje zaczynają się przy **pierwszym** znaczniku OZ, potem **pierwszym** ZP;
- po trzech zadaniach mogą być **dalsze znaczniki** (np. „czynność podstawowa”, „artefakt”) — **ignorujemy je** przy wyznaczaniu segmentów;
- powtórzone OO/OZ/ZP (drugi „Oczy otwarte” itd.) — **ignorujemy**, liczy się tylko pierwsze wystąpienie każdego typu w kolejności OO → OZ → ZP.

## Kolejność znaczników

Wymagana kolejność chronologiczna pierwszych trzech dopasowań:

| Kolejność | Kod | Zadanie |
|-----------|-----|---------|
| 1 | OO | Oczy otwarte |
| 2 | OZ | Oczy zamknięte |
| 3 | ZP | Zadanie pamięciowe / obliczenia |

Znacznik OZ przed OO lub ZP przed OZ jest pomijany — aplikacja szuka pierwszego poprawnego ciągu OO → OZ → ZP.

## Koniec segmentu

- **OO** kończy się przy początku **OZ** (lub +3 min / koniec nagrania, jeśli brak kolejnego znacznika).
- **OZ** kończy się przy początku **ZP**.
- **ZP** kończy się przy **następnym dowolnym znaczniku** w pliku albo +3 min / koniec nagrania.

## Rozpoznawane nazwy znaczników (MVP — głównie polskie)

Dopasowanie: bez względu na wielkość liter, polskie znaki, opcjonalny prefiks czasu (`12:34:56 …`). Szukamy **frazy** w opisie adnotacji.

### OO — oczy otwarte

| Fraza |
|-------|
| `Oczy otwarte` |
| `Oczy otw.` / `Oczy otw` |
| `OO` (osobne słowo) |
| `Eyes open` / `Eyesopen` / `Open eyes` |

### OZ — oczy zamknięte

| Fraza |
|-------|
| `Oczy zamknięte` / `Oczy zamkniete` |
| `Oczy zamk.` / `Oczy zamk` |
| `OZ` (osobne słowo) |
| `Eyes closed` / `Eyesclosed` / `Closed eyes` |

### ZP — zadanie pamięciowe / obliczenia

| Fraza |
|-------|
| `Zadanie poznawcze` |
| `Zadanie pozna` / `zadanie pozna` (obcięta etykieta EDF) |
| `Zadanie pamięciowe` / `Zadanie pamieciowe` |
| `Matematyka poznawcza` |
| `Matematyka` |
| `Mat.` (skrót) |
| `Obliczenia` |
| `Memory task` / `Memory` |
| `ZP` (osobne słowo) |

### Przykłady **nie** mapowanych na zadania

Te znaczniki nie uruchamiają segmentu (mogą kończyć segment ZP):

- `Czynność podstawowa`
- `Stymulacja akustyczna`
- `Artefakt`

Listę można rozszerzać w `_TASK_KEYWORDS` w `app/domain/pipeline.py` po weryfikacji z kolejnymi aparatami.

## Komunikaty błędów (UI)

| Kod | Znaczenie |
|-----|-----------|
| `insufficient_duration` | Nagranie &lt; 8 min |
| `missing_task_segments` | Częściowe znaczniki (brak pełnego OO→OZ→ZP w kolejności) |
