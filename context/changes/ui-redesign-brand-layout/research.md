---
date: 2026-07-08T18:12:00+02:00
researcher: Cursor Agent
git_commit: 2768a76f5e89ec6bc0a3ece2de905db654163f84
branch: coursor/dev-env-setup-2f65
repository: NeuroFlag
topic: "Propozycje redesignu układu i kolorystyki UI (spójność z ulotką NEUROD)"
tags: [research, ui, ux, theme, branding, layout]
status: complete
last_updated: 2026-07-08
last_updated_by: Cursor Agent
---

# Research: Propozycje redesignu układu i kolorystyki UI

**Date**: 2026-07-08T18:12:00+02:00  
**Researcher**: Cursor Agent  
**Git Commit**: `2768a76f5e89ec6bc0a3ece2de905db654163f84`  
**Branch**: `coursor/dev-env-setup-2f65`  
**Repository**: NeuroFlag

## Research Question

Użytkownik nie jest zadowolona z obecnego układu i kolorystyki aplikacji NeuroFlag w porównaniu z ulotką NEUROD(6-10). Prośba o propozycje alternatyw — zakres: szybkie rekomendacje, priorytet spójności z ulotką, rewolucyjna zmiana layoutu.

## Summary

Obecny UI to **jednokolumnowy wizard** (szerokość treści ~720 px, wyrównanie do lewej) z **pomarańczowym akcentem na wszystkich kontrolkach** CTk i **białym tłem**. Ulotka NEUROD proponuje natomiast **miętowe tło**, **bloki granat + pomarańcz** oraz wyraźną hierarchię sekcji. Największe problemy wizualne to: pusta przestrzeń po prawej, „krzykliwa” czerwień wyników bez ramy kontekstu, pomarańcz na radio/checkbox/selector (nie tylko CTA), oraz ciężkie granatowe paski w oknie Informacje.

Rekomendujemy **dwa warianty rewolucyjne** — oba zachowują niezmienne kolory RAG (`#CC0000` / `#F5A800` / `#00AA00`) i nazwę produktu NeuroFlag:

1. **Wariant A — „Panel boczny + karta”** (rekomendowany): stały granatowy sidebar ze stepperem, miętowe tło, białe karty wyśrodkowane, pomarańcz tylko na głównych CTA.
2. **Wariant B — „Nagłówek + dwie kolumny”**: poziomy pasek z krokami, na szerokim oknie formularz + panel kontekstu; wyniki jako dashboard 40/60.

Implementacja jest dobra pod redesign: hook w `AppWindow._shell` / `_chrome` / `_view_host`, tokeny w `theme.py` + `neuroflag.json`, wzorce w `widgets.py`.

## Detailed Findings

### Stan obecny — co widać na ekranach

| Ekran | Problem wizualny | Przyczyna w kodzie |
|-------|------------------|-------------------|
| Dane dziecka | Wąska kolumna, dużo pustki po prawej | `WRAP_WIDTH=720`, `anchor="w"` (`theme.py:13`, `widgets.py:14-18`) |
| Dane dziecka | Pomarańcz na wieku, płci, checkboxach | CTk JSON ustawia `#F9A825` na RadioButton/CheckBox/OptionMenu (`neuroflag.json`) |
| Wczytaj plik | Skok layoutu po wczytaniu pliku | Dynamiczne `pack_forget`/`pack` karty identyfikacji (`file_import.py:267`) |
| Wyniki | Cały ekran „czerwony” przy Wskazaniu | Siatka 10 komórek RAG bez neutralnej ramy; duży nagłówek w kolorze kategorii (`results_grid.py:63-87`) |
| Historia | Przycisk „Wskazanie” wygląda jak błąd | Badge kategorii = pełny czerwony przycisk (`history.py:201-209`) |
| Informacje | Ciężkie granatowe belki | `_section_header` z pełnym `COLOR_SECTION_NAVY` (`info_dialog.py:158-171`) |

### Paleta — ulotka vs aplikacja

**Ulotka NEUROD(6-10):**
- Tło: jasny miętowy / turkusowy
- Akcent: nasycony pomarańcz (bloki PRODUKT, KONTAKT)
- Struktura: ciemny granat (blok wartości)
- Biel: nagłówek z grafiką mózgu
- Akcent dodatkowy: jasna zieleń w tytule (dekoracyjna)

**Aplikacja (chrome — elastyczne):**
- Tło: białe / jasnoszare (`#FFFFFF`, `#F7F9FC`)
- Akcent: `#F9A825` na przyciskach **i** kontrolkach formularza
- Granat: tylko w dialogu Informacje (`#283593`)

**Wyniki kliniczne (sztywne — nie zmieniać):**
- Czerwień `#CC0000`, żółć `#F5A800`, zieleń `#00AA00` (`rag_colors.py`)

Zmiana `flyer-theme-info-screen` (zarchiwizowana) już wprowadziła pomarańcz i granat, ale **bez miętowego tła** i **bez nowego układu nawigacji**.

### Architektura UI — co ułatwia rewolucję

```
AppWindow (920×680)
└── _shell
    ├── _chrome          ← dziś: tylko „Informacje”
    └── _view_host       ← niszczy/tworzy widok przy każdej nawigacji
```

Naturalny flow kroków już istnieje: Metadane → Import (+ opcjonalnie Mapowanie) → Analiza → Wyniki. Brakuje tylko **widocznego steppera** i **stałego chrome**.

Pliki do zmiany przy redesignie: `app_window.py`, `theme.py`, `neuroflag.json`, `widgets.py`, wszystkie widoki w `app/ui/views/`, `info_dialog.py`, opcjonalnie `pdf_generator.py` (spójność typografii).

---

## Propozycje redesignu

### Wariant A — „Panel boczny + karta” (rekomendowany)

Najbliżej charakteru ulotki, najlepiej rozwiązuje pustą przestrzeń i chaos pomarańczu.

#### Layout

```
┌──────────────┬────────────────────────────────────────────┐
│  NeuroFlag   │  (miętowe tło)                             │
│  [ikona]     │     ┌─────────────────────────┐            │
│              │     │  BIAŁA KARTA (max 640px) │            │
│  ● 1 Dane    │     │  tytuł + treść formularza│            │
│  ○ 2 Plik    │     │                          │            │
│  ○ 3 Wynik   │     └─────────────────────────┘            │
│              │                                            │
│  Historia    │  ┌──────────────────────────────────────┐  │
│  Informacje  │  │ ← Wstecz          Dalej → (pomarańcz)│  │
└──────────────┴──┴──────────────────────────────────────┴──┘
```

- **Sidebar ~200 px**, tło granat `#1E3A5F` (bliżej ulotki niż obecne `#283593`)
- Logo / ikona mózgu-EEG (asset z ulotki, bez napisu NEUROD)
- **Stepper pionowy** — aktywny krok: pomarańczowa kropka; ukończone: biała checkmark
- **Obszar treści**: tło miętowe `#E3F0EC` (z ulotki)
- **Karta**: biała, `corner_radius=12`, cień przez `border_color` + padding 32 px, **wyśrodkowana**
- **Stopka stała** (nie w scrollu): Wstecz (ghost) | Dalej / Analizuj (pomarańcz)

#### Kolorystyka (chrome)

| Token | Hex | Zastosowanie |
|-------|-----|--------------|
| `COLOR_CANVAS` | `#E3F0EC` | Tło główne (z ulotki) |
| `COLOR_SIDEBAR` | `#1E3A5F` | Panel boczny |
| `COLOR_CARD` | `#FFFFFF` | Karty formularzy |
| `COLOR_ACCENT` | `#F9A825` | **Tylko** primary CTA (Dalej, Analizuj, PDF) |
| `COLOR_ACCENT_MUTED` | `#FFCC80` | Hover/disabled secondary |
| `COLOR_TEXT` | `#1A2B3C` | Tekst na jasnym |
| `COLOR_ON_SIDEBAR` | `#FFFFFF` | Tekst w sidebarze |
| `COLOR_CONTROL` | `#CBD5E0` | Obramowanie radio/checkbox/selector |
| `COLOR_CONTROL_ACTIVE` | `#1E3A5F` | Zaznaczenie radio/checkbox (nie pomarańcz!) |

**Kluczowa zmiana:** w `neuroflag.json` RadioButton/CheckBox/OptionMenu/SegmentedButton → **granatowe zaznaczenie**, nie pomarańcz. Pomarańcz zostaje wyłącznie na `CTkButton` primary.

#### Ekran wyników (Wskazanie)

- Nagłówek kategorii w **białej karcie-hero** z kolorowym **paskiem bocznym** (4 px) w kolorze kategorii — zamiast całego tytułu na czerwono
- Siatka 10 komórek w **drugiej karcie**, wyśrodkowana; komórki RAG bez zmian
- Przy dominacji czerwieni: delikatna szara ramka wokół siatki oddziela „dane kliniczne” od reszty UI
- Akcje: PDF (pomarańcz), reszta secondary w stopce

#### Historia

- Kategoria = **chip** (zaokrąglony label), nie przycisk „Wskazanie”
- Edytuj: secondary; Usuń: danger outline (nie pełna czerwień obok chipa wskazania)

#### Informacje

- Zamiast pełnych granatowych belki → **karty z lewym paskiem** (jak wyniki)
- Sekcje: ikona + tytuł granatowy, treść na białym — lżejsze, spójne z resztą app

---

### Wariant B — „Nagłówek + dwie kolumny”

Bardziej „medyczny dashboard”, mniej „marketingowy” niż sidebar.

#### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ [logo] NeuroFlag    (1)─(2)─(3)─(4) kroki      Informacje  │  ← biały header + miętowy pasek 4px
├────────────────────────────┬────────────────────────────────┤
│ Formularz (60%)            │ Panel kontekstu (40%)          │
│                            │ • RODO / offline               │
│                            │ • Wymagania pliku .edf         │
│                            │ • Skrót pomocy                 │
└────────────────────────────┴────────────────────────────────┘
│ ← Wstecz                              Dalej →               │
└─────────────────────────────────────────────────────────────┘
```

- **Header** stały: logo, **stepper poziomy** (kropki + etykiety), Informacje
- **Miętowy akcent**: cienki pasek pod headerem (`#B8D8D0`) — nod do ulotki bez zalania całego tła
- **Dwie kolumny** na krokach 1–2; na wąskim oknie (<900 px) panel kontekstu schodzi pod formularz
- **Wyniki**: lewa kolumna = kategoria + opis + przyciski; prawa = siatka 2×5 (większe komórki, skalują się z oknem)
- **Analiza**: overlay na `_view_host` zamiast osobnego widoku — mniej „migania” ekranów

#### Kolorystyka

- Tło główne: `#F7F9FC` (obecne — spokojniejsze niż pełne mięta)
- Nagłówki sekcji: granat `#1E3A5F` (tekst, nie bloki)
- Pomarańcz: max 1 przycisk primary na ekran
- Panel kontekstu: `COLOR_SURFACE` z ikoną kłódki (offline)

---

## Porównanie wariantów

| Kryterium | Wariant A (sidebar) | Wariant B (header 2-col) |
|-----------|---------------------|--------------------------|
| Spójność z ulotką | ★★★★★ (mięto + granat + pomarańcz) | ★★★☆☆ (subtelniejsze) |
| Czytelność wyników RAG | ★★★★☆ (karty ramują czerwień) | ★★★★★ (dashboard) |
| Nakład pracy w CTk | Średni (nowy shell) | Średni-wysoki (responsive 2-col) |
| Historia globalna | Naturalna w sidebarze | Wymaga miejsca w headerze |
| Wąskie okno 820 px | Sidebar zwijany do ikon | Kolumny stackują się |

**Rekomendacja:** Wariant A dla spójności z ulotką i „rewolucji” bez przeładowania wyników.

---

## Code References

- `app/ui/theme.py:9-33` — tokeny layoutu i kolorów chrome
- `app/ui/assets/themes/neuroflag.json` — paleta CTk (tu zmienić radio/checkbox)
- `app/ui/app_window.py:55-69` — shell do rozbudowy (sidebar)
- `app/ui/components/widgets.py:14-142` — fabryki przycisków i kart
- `app/ui/components/rag_colors.py:5-27` — kolory kliniczne (niezmienne)
- `app/ui/views/results_grid.py:63-162` — siatka wyników
- `app/ui/views/history.py:171-212` — wiersze historii (chip zamiast button)
- `app/ui/components/info_dialog.py:158-171` — sekcje informacji

## Architecture Insights

- Dwa systemy kolorów muszą pozostać rozdzielone: **chrome** (elastyczny) vs **RAG** (sztywny).
- Pomarańcz UI (`#F9A825`) i żółć RAG (`#F5A800`) są bliskie — pomarańcz tylko na CTA, nigdy na elementach wynikowych.
- `font_heading()` (20 bold) jest zdefiniowany ale nieużywany — dobry kandydat na tytuły kart w redesignie.
- Warto dodać `surface_card()` w `widgets.py` — dziś karty powielane inline w 3 widokach.

## Historical Context

- `context/changes/flyer-theme-info-screen/` — wprowadzono pomarańcz CTA i granat w Informacjach; świadomie **bez** miętowego tła i grafik ulotki; RAG bez zmian.
- `context/changes/metadata-and-import/` — ustalono wizard linearny, light theme, exclusion warning.
- `context/changes/eeg-pipeline-and-results/` — siatka 10 komórek, stałe rozmiary 132×86 px.

## Related Research

- `context/changes/eeg-file-personal-data/research.md` — prywatność i info_box na pierwszym ekranie
- `context/changes/eegdigitrack-native-reader/research.md` — import plików (kontekst ekranu wczytywania)

## Open Questions

1. Czy dodać grafikę mózgu z ulotki do sidebara (asset PNG/SVG)?
2. Czy miętowe tło (`#E3F0EC`) na całym canvas, czy tylko jako akcent (Wariant B)?
3. Czy sidebar ma być zwijany na oknach <900 px, czy stała szerokość?
4. Czy PDF ma dostać miętowy pasek w nagłówku dla spójności z aplikacją?
