---
date: 2026-07-09T13:33:00+02:00
researcher: Cursor Agent
git_commit: a8a42d0e299a9af40499c6d6bc49374636e07aa1
branch: experiment/pipeline-amplitude-calibration
repository: NeuroFlag
topic: "Alternatywne układy siatki wyników RAG — grupowanie po zadaniu, paśmie lub macierzy kanał×zadanie"
tags: [research, ui, ux, results-grid, rag, readability]
status: complete
last_updated: 2026-07-09
last_updated_by: Cursor Agent
---

# Research: Czytelniejszy układ siatki wyników RAG

**Date**: 2026-07-09T13:33:00+02:00  
**Researcher**: Cursor Agent  
**Git Commit**: `a8a42d0e299a9af40499c6d6bc49374636e07aa1`  
**Branch**: `experiment/pipeline-amplitude-calibration`  
**Repository**: NeuroFlag

## Research Question

Obecny układ siatki 10 komórek RAG wydaje się mało czytelny — użytkownik prosi o propozycje alternatywnego układu zwiększającego widoczność, z możliwością pogrupowania po typie zadania lub falach. Zakres: porównanie wariantów UX z mockupami tekstowymi (bez planu implementacji).

## Summary

**Diagnoza:** Siatka 2×5 w `results_grid.py` to **mechaniczne wypełnienie** kolejności z `norms.json` (indeks `// 5`, `% 5`), bez logicznego grupowania. Przy kategorii „Wskazanie” (≥5 czerwonych) użytkownik widzi **ścianę jednolitego koloru** — trudno skanować, które zadanie lub lokalizacja są problematyczne.

**Kluczowy wniosek:** Kolejność danych w `AnalysisResult.cells` musi pozostać zgodna z normami (pipeline, kalibracja, historia), ale **kolejność wizualna może być dowolna** — wystarczy sortowanie/mapowanie przy renderowaniu.

**Rekomendacja:** **Wariant A — grupowanie po warunku zadaniowym (OO → OZ → ZP)** z nagłówkami sekcji i komórkami posortowanymi wewnątrz sekcji po kanale, potem paśmie. Najlepiej odpowiada protokołowi EEG i sposobowi czytania wyniku przez pedagoga. Wariant B (macierz kanał×zadanie) jako alternatywa dla użytkowników porównujących C3 vs O1 w tym samym zadaniu.

## Stan obecny — dlaczego jest mało czytelny

### Mechanizm renderowania

```126:127:app/ui/views/results_grid.py
        for idx, cell in enumerate(result.cells):
            self._make_cell(self._grid_frame, cell, row=idx // _GRID_COLS, col=idx % _GRID_COLS)
```

Stałe `_GRID_COLS = 5` → układ **5 kolumn × 2 wiersze**, wypełniany w kolejności tablicy `result.cells`.

### Faktyczne pozycje komórek (kolejność z `norms.json`)

| Indeks | Wiersz | Kolumna | Kanał | Zadanie | Pasmo |
|--------|--------|---------|-------|---------|-------|
| 0 | 0 | 0 | C3 | Oczy zamknięte | Theta |
| 1 | 0 | 1 | C3 | Zadanie pamięciowe | Theta |
| 2 | 0 | 2 | C3 | Zadanie pamięciowe | Beta1 |
| 3 | 0 | 3 | C3 | Oczy otwarte | Beta2 |
| 4 | 0 | 4 | O1 | Oczy otwarte | Delta |
| 5 | 1 | 0 | O1 | Oczy otwarte | Theta |
| 6 | 1 | 1 | O1 | Oczy zamknięte | Theta |
| 7 | 1 | 2 | O1 | Zadanie pamięciowe | Theta |
| 8 | 1 | 3 | O1 | Oczy otwarte | Beta2 |
| 9 | 1 | 4 | O1 | Zadanie pamięciowe | Beta2 |

**Problemy percepcyjne:**

1. **Brak nagłówków** — sąsiadujące komórki mogą dotyczyć różnych zadań i pasm bez wizualnego podziału.
2. **Przypadkowy wzorzec** — pierwszy wiersz to głównie C3 + jedna komórka O1; drugi wiersz to same O1 — wygląda jak grupowanie po kanale, ale tak nie jest (np. C3 OO Beta2 jest w kolumnie 3, nie razem z innymi OO).
3. **Dominacja jednego koloru** — przy Wskazaniu (zrzut ekranu użytkownika: 10 czerwonych) jedyną informacją jest drobny tekst wewnątrz komórek; brak „kotwic” wizualnych.
4. **Trzy linie tekstu w małej komórce** — kanał, zadanie, pasmo powtarzają się w każdej komórce, choć pozycja w siatce mogłaby niósć część tej informacji.

### Rozkład 10 kombinacji po wymiarach

| Wymiar | Rozkład | Uwagi |
|--------|---------|-------|
| Zadanie OO | 4 komórki | O1 ma 3 pasma (Delta, Theta, Beta2) |
| Zadanie OZ | 2 komórki | Najmniejsza sekcja |
| Zadanie ZP | 4 komórki | C3 i O1 po 2 pasma |
| Kanał C3 | 4 komórki | |
| Kanał O1 | 6 komórki | Nierówny podział |
| Pasmo Theta | 5 komórek | Dominuje |
| Pasmo Beta2 | 3 | |
| Pasmo Beta1 | 1 | |
| Pasmo Delta | 1 | |

Żaden wymiar nie daje równomiernej siatki 2×5 — stąd potrzeba **sekcji z nagłówkami** lub **macierzy z wieloma pasmami w jednej komórce**.

### Ograniczenia UI (bez implementacji — kontekst dla propozycji)

- Okno: `1000×720`, min `900×640` (`app_window.py:53-54`)
- Szerokość treści: ~804–904 px (po paddingu 48 px)
- Komórki: min 120×80, max 150×95 px (`results_grid.py:29-32`)
- Budżet wysokości pod siatkę przy minsize: ~438 px (nagłówek + stopka + karta kategorii)
- Brak scrolla w widoku wyników — przy układzie pionowym z sekcjami może być potrzebny `CTkScrollableFrame` (wzorzec: `metadata_form.py`)
- Planowany dashboard 40/60 został porzucony — 530 px nie mieści 5 kolumn × 120 px (`ui-redesign-brand-layout/plan.md:336`)

## Propozycje układów

### Wariant 0 — Obecny (punkt odniesienia)

```
┌────┬────┬────┬────┬────┐
│ C3 │ C3 │ C3 │ C3 │ O1 │   ← wiersz 1: mieszanka zadań
│ OZ │ ZP │ ZP │ OO │ OO │
├────┼────┼────┼────┼────┤
│ O1 │ O1 │ O1 │ O1 │ O1 │   ← wiersz 2: wygląda jak „wszystko O1”
│ OO │ OO │ OZ │ ZP │ ZP │
└────┴────┴────┴────┴────┘
```

| Za | Przeciw |
|----|---------|
| Prosty kod, mieści się w szerokości | Brak logiki grupowania |
| Spójny z PDF (ta sama kolejność) | Przy 10× czerwonym — „ściana czerwieni” |
| | Trudno odpowiedzieć: „co z zadaniem pamięciowym?” |

---

### Wariant A — Po warunku zadaniowym (REKOMENDOWANY)

Trzy sekcje z nagłówkiem `section_title`, wewnątrz komórki w rzędzie posortowane: kanał (C3 przed O1), potem pasmo.

```
┌─ Oczy otwarte ────────────────────────────────────────────────┐
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                           │
│ │ C3   │ │ O1   │ │ O1   │ │ O1   │   4 komórki, pełna szer. │
│ │ Beta2│ │ Delta│ │ Theta│ │ Beta2│                           │
│ └──────┘ └──────┘ └──────┘ └──────┘                           │
└───────────────────────────────────────────────────────────────┘

┌─ Oczy zamknięte ──────────────────────────────────────────────┐
│ ┌──────┐ ┌──────┐                                              │
│ │ C3   │ │ O1   │   2 komórki — wycentrowane lub wyrównane L  │
│ │ Theta│ │ Theta│                                              │
│ └──────┘ └──────┘                                              │
└───────────────────────────────────────────────────────────────┘

┌─ Zadanie pamięciowe ──────────────────────────────────────────┐
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                           │
│ │ C3   │ │ C3   │ │ O1   │ │ O1   │                           │
│ │ Theta│ │ Beta1│ │ Theta│ │ Beta2│                           │
│ └──────┘ └──────┘ └──────┘ └──────┘                           │
└───────────────────────────────────────────────────────────────┘
```

**Uproszczenie etykiet w komórce:** skoro sekcja = zadanie, wewnątrz komórki wystarczą **kanał (bold) + pasmo** — jedna linia mniej, większy kontrast.

| Za | Przeciw |
|----|---------|
| Zgodność z protokołem EEG (OO → OZ → ZP) | Sekcja OZ ma tylko 2 komórki — asymetria |
| Łatwe pytanie: „jak dziecko wypada w zadaniu pamięciowym?” | Większa wysokość → scroll przy minsize |
| Nagłówki łamią monotonię przy 10× czerwonym | PDF wymaga osobnej decyzji (obecnie płaska 2×5) |
| Naturalne dla opisu kategorii („kombinacje lokalizacja–zadanie–pasmo”) | |

**Ocena czytelności:** ★★★★★ dla pedagoga / specjalisty prowadzącego badanie przesiewowe.

---

### Wariant B — Macierz kanał × zadanie

Nagłówki kolumn = zadania, wiersze = kanały. Gdy w jednej komórce jest wiele pasm — mini-pasek pionowy lub podkomórki.

```
              Oczy otwarte      Oczy zamknięte    Zadanie pamięciowe
            ┌─────────────┐   ┌───────────┐   ┌───────────┐
    C3      │   Beta2     │   │   Theta   │   │ Theta     │
            │             │   │           │   │ Beta1     │
            └─────────────┘   └───────────┘   └───────────┘
            ┌─────────────┐   ┌───────────┐   ┌───────────┐
    O1      │ Delta       │   │   Theta   │   │ Theta     │
            │ Theta       │   │           │   │ Beta2     │
            │ Beta2       │   │           │   │           │
            └─────────────┘   └───────────┘   └───────────┘
```

| Za | Przeciw |
|----|---------|
| Natychmiastowe porównanie C3 vs O1 w tym samym zadaniu | Komórka O1/OO ma **3 pasma** — wymaga złożonego widgetu |
| Blisko macierzy PRD (lokalizacja × warunek × pasmo) | Najwyższy koszt implementacji |
| Kompaktowy — 2 wiersze danych + nagłówek | Przy wielu czerwonych w jednej komórce — nadal „czerwona ściana” wewnątrz |

**Ocena czytelności:** ★★★★☆ dla eksperta EEG; ★★★☆☆ dla pedagoga bez przyzwyczajenia do macierzy.

---

### Wariant C — Po paśmie częstotliwości

Sekcje: Theta (5), Beta2 (3), Beta1 (1), Delta (1). W komórce: kanał + skrót zadania.

```
┌─ Theta ───────────────────────────────────────────────────────┐
│ [C3/OZ] [C3/ZP] [O1/OO] [O1/OZ] [O1/ZP]                       │
└───────────────────────────────────────────────────────────────┘
┌─ Beta2 ───────────────┐ ┌─ Beta1 ─┐ ┌─ Delta ─┐
│ [C3/OO] [O1/OO] [O1/ZP]│ │ [C3/ZP] │ │ [O1/OO] │
└────────────────────────┘ └─────────┘ └─────────┘
```

| Za | Przeciw |
|----|---------|
| Sensowne dla neurofizjologa | Theta dominuje — reszta wygląda jak „dodatek” |
| Łatwe: „ile problemów w Thecie?” | Zadanie schowane w skrócie (C3/OZ) — gorsze dla protokołu |
| | Beta1 i Delta po 1 komórce — puste ramki wokół |

**Ocena czytelności:** ★★☆☆☆ dla grupy docelowej aplikacji (pedagog, rodzic).

---

### Wariant D — Uporządkowana siatka 2×5 + nagłówki osi (minimalna zmiana)

Zachować płaską siatkę, ale **przestawić komórki** wg `(zadanie, kanał, pasmo)` i dodać etykiety nad kolumnami / obok wierszy.

```
         Zadanie →
         OO      OO      OZ      ZP      ZP
       ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐
  C3   │β2  │  │    │  │θ   │  │θ   │  │β1  │
       └────┘  └────┘  └────┘  └────┘  └────┘
  O1   ┌────┐  ┌────┐  ┌────┐  ┌────┐  ┌────┐
       │δ   │  │θ β2│  │θ   │  │θ   │  │β2  │
       └────┘  └────┘  └────┘  └────┘  └────┘
```

Uwaga: czysta macierz 2×3 nie mieści 10 komórek — stąd 5 kolumn z powtórzeniami zadań.

| Za | Przeciw |
|----|---------|
| Najmniejsza zmiana wizualna | Nadal płaska siatka — słabsze grupowanie niż A |
| Mieści się w obecnym kodzie siatki | Kolumny OO i ZP się powtarzają — mylące nagłówki |
| Łatwa synchronizacja z PDF | Nie rozwiązuje „ściany czerwieni” w pełni |

**Ocena czytelności:** ★★★☆☆ — krok pośredni.

---

### Wariant E — Dwie strefy: „Wymaga uwagi” + „W normie”

Na górze komórki czerwone i żółte (posortowane po zadaniu), na dole zielone w zwiniętej sekcji lub mniejszym kontraście.

```
┌─ Kombinacje wymagające uwagi (7) ─────────────────────────────┐
│ [sekcje po zadaniu, tylko czerwone/żółte]                     │
└───────────────────────────────────────────────────────────────┘
┌─ W normie (3) ────────────── [rozwiń ▼] ─────────────────────┐
│ (zielone komórki, mniejsze lub zwinięte domyślnie)            │
└───────────────────────────────────────────────────────────────┘
```

| Za | Przeciw |
|----|---------|
| Przy Wskazaniu — natychmiastowy fokus | PRD wymaga widoczności **wszystkich 10** wartości |
| Mniej przytłaczające przy wielu czerwonych | Zwinięcie zielonych może być źle odebrane klinicznie |
| Dobre uzupełnienie wariantu A | Dodatkowa logika UX (próg, animacja) |

**Ocena:** ★★★★☆ jako **dodatek** do wariantu A, nie jako samodzielny układ.

---

## Porównanie wariantów

| Kryterium | Obecny | A (zadanie) | B (macierz) | C (pasmo) | D (osi) | E (strefy) |
|-----------|--------|-------------|-------------|-----------|---------|------------|
| Zgodność z protokołem EEG | ★★☆ | ★★★★★ | ★★★★ | ★★ | ★★★ | ★★★★ |
| Skanowanie przy 10× czerwonym | ★ | ★★★★★ | ★★★ | ★★ | ★★★ | ★★★★★ |
| Porównanie C3 vs O1 | ★★ | ★★★ | ★★★★★ | ★★★ | ★★★ | ★★★ |
| Prostość wizualna | ★★★ | ★★★★ | ★★ | ★★ | ★★★ | ★★★ |
| Nakład zmian w UI | — | Średni | Wysoki | Średni | Niski | Średni+wysoki |
| Mieści się w minsize bez scrolla | ★★★★ | ★★★ | ★★★★ | ★★★ | ★★★★ | ★★★ |

## Rekomendacja

**Wariant A (grupowanie po zadaniu)** jako docelowy układ ekranu wyników:

1. Odpowiada kolejności segmentów nagrania (OO → OZ → ZP) opisanej w `docs/EEG-segmentacja.md`.
2. Nagłówki sekcji dają **kotwice wizualne** przy monochromatycznej siatce.
3. Wewnątrz komórki można skrócić etykietę (kanał + pasmo), bo zadanie wynika z nagłówka.
4. Implementacja polega na **sortowaniu przy renderowaniu**, bez zmiany `AnalysisResult.cells`.

**Opcjonalne ulepszenia (łączone z A):**

- Delikatna legenda RAG pod siatką (🔴 poniżej normy / 🟡 strefa nieokreślona / 🟢 w normie) — jednorazowo, nie w każdej komórce.
- Przy sekcji z samymi czerwonymi — subtelna szara ramka sekcji (już sugerowane w `ui-redesign-brand-layout/research.md:133`).
- Wariant E jako przyszły „tryb skrócony” — po akceptacji eksperta, że zwijanie zielonych jest dopuszczalne.

**Wariant B** rozważyć tylko jeśli użytkownicy eksplicytnie proszą o porównanie C3/O1 w jednym rzucie oka.

## Code References

- `app/ui/views/results_grid.py:29-34` — stałe siatki i rozmiaru komórek
- `app/ui/views/results_grid.py:126-127` — mapowanie indeks → (row, col)
- `app/ui/views/results_grid.py:178-219` — treść komórki (kanał, zadanie, pasmo)
- `app/reports/pdf_generator.py` — siatka A′ w PDF (`_build_rag_grid_story`)
- `app/domain/algorithm.py:60-74` — kolejność `cells` = kolejność `config.norms`
- `norms.json:69-79` — kanoniczna macierz 10 kombinacji
- `app/ui/components/rag_colors.py:17-21` — etykiety zadań PL
- `app/ui/components/widgets.py:31-38` — `section_title` do nagłówków sekcji
- `app/ui/app_window.py:53-54` — wymiary okna
- `context/foundation/prd.md:145-158` — macierz norm (semantyka komórek)

## Architecture Insights

- **Dwa poziomy kolejności:** domena (stała, z `norms.json`) vs prezentacja (dowolna permutacja przy renderowaniu).
- **Nie zmieniać** kolejności w `classify()` ani w historii — tylko warstwa widoku (i opcjonalnie PDF).
- Kolory RAG pozostają niezmienne; czytelność osiąga się **grupowaniem i typografią**, nie nowymi kolorami chrome.
- Przy układzie sekcji pionowych prawdopodobnie potrzebny `CTkScrollableFrame` + `bind_auto_hide_scrollbar` (wzorzec z `metadata_form.py`).

## Historical Context

- `context/archive/2026-06-03-eeg-pipeline-and-results/plan.md` — pierwsza siatka: 2×5 lub 5×2, stałe 132×86 px, etykiety kanał/zadanie/pasmo.
- `context/archive/2026-06-22-pdf-report-and-save/plan-brief.md` — PDF: **2 rzędy × 5 kolumn** dla A4.
- `context/changes/ui-redesign-brand-layout/research.md:46` — diagnoza „cały ekran czerwony przy Wskazaniu”.
- `context/changes/ui-redesign-brand-layout/plan.md:336` — dashboard 40/60 porzucony na rzecz stosu pionowego; dynamiczna siatka zachowana.

## Related Research

- `context/changes/ui-redesign-brand-layout/research.md` — redesign chrome, ramowanie siatki RAG
- `context/changes/pipeline-expert-alignment/research.md` — macierz norm i kalibracja

## Open Questions

1. Czy PDF ma odzwierciedlać nowy układ grupowany, czy zostaje płaska 2×5 (spójność print vs ekran)?
2. Czy w komórce po grupowaniu po zadaniu wystarczy **kanał + pasmo**, czy użytkownicy wolą pełną etykietę?
3. Czy sekcja „Oczy zamknięte” (2 komórki) ma być wycentrowana, czy wyrównana do lewej jak pozostałe?
4. Czy dodać legendę RAG na stałe pod siatką, czy tylko w „Informacje”?

---

## Decyzja implementacyjna (2026-07-09)

Po iteracji w Canvasie (mockupy A–D i A′) użytkownik zaakceptował **Wariant A′** — rozszerzenie wariantu A o klastry kanałów C3 | O1 z pionową linią podziału.

| Element | Zachowanie |
|---------|------------|
| Układ strony | `two_column_body(left_weight=2, right_weight=3)` → 40% lewa / 60% prawa |
| Lewa karta | Kategoria + opis (`surface_card`, pasek RAG 4 px) |
| Prawa karta | Siatka wyników — **ta sama wysokość** co lewa (`pack(fill="both", expand=True)`) |
| Sekcje | 3 bloki: Oczy otwarte → Oczy zamknięte → Zadanie pamięciowe |
| W sekcji | C3 \| O1 obok siebie; linia pionowa tuż za komórkami C3 |
| W komórce | Tylko pasmo (np. Theta, Beta1) — bez kanału i zadania |
| Odstępy | Sekcje w grid **bez wag wierszy**; między zadaniami cienka linia + 4 px padding |
| Treść prawej karty | Zakotwiczona u góry (`anchor="n"`); ewentualna pusta przestrzeń pod ostatnim zadaniem |

**Nie zmieniono:** kolejność `AnalysisResult.cells` (pipeline, historia, kalibracja). Sortowanie wyłącznie przy renderowaniu (`app/domain/cell_layout.py`: `TASK_DISPLAY_ORDER`, `CHANNEL_DISPLAY_ORDER`, `BAND_DISPLAY_ORDER`, `cells_for_task_channel`).

**Usunięto z UI:** siatka 5×2 (`idx // 5`, `% 5`), dynamiczne skalowanie komórek (`_update_cell_sizes`, `_GRID_COLS`), `CTkScrollableFrame` w prawej karcie.

**Komórki:** kompaktowe kafelki 88×56 px; `wraplength` opisu synchronizowany z szerokością lewej kolumny (`_sync_text_wrap`).

**PDF:** Wariant A′ wdrożony (`e53b34b`) — sekcje zadań (OO/OZ/ZP), klastry C3|O1 obok siebie, w kafelku tylko pasmo; bez pionowej linii podziału (feedback UX 2026-07-09). Kolory RAG z `RAG_COLOR_BG`.

**Addendum do `ui-redesign-brand-layout/plan.md`:** dashboard 40/60 przywrócony na ekranie wyników (wcześniejszy addendum impl-review wskazywał układ pionowy).
