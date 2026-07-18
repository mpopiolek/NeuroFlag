# Redesign UI — Wariant B (nagłówek + dwie kolumny)

## Overview

Przebudowa interfejsu NeuroFlag według **Wariantu B** z researchu: stały nagłówek z poziomym stepperem, miętowy pasek akcentu, układ dwukolumnowy (formularz + panel kontekstu) na krokach 1–2, dashboard wyników 40/60, spójna stopka nawigacji. Kolorystyka chrome: granat na kontrolkach formularza, pomarańcz wyłącznie na primary CTA. Kolory RAG wyników klinicznych pozostają niezmienione.

## Current State Analysis

- Wizard jednokolumnowy, treść ~720 px wyrównana do lewej (`theme.py:13`, `widgets.py:14-18`)
- Globalny chrome to jeden przycisk „Informacje” (`app_window.py:58-66`)
- Pomarańcz `#F9A825` na wszystkich kontrolkach CTk (`neuroflag.json` + `test_theme.py:14-31`)
- Każdy widok sam układa przyciski Wstecz/Dalej — brak spójnej stopki
- Blok RODO na dole formularza metadanych (`metadata_form.py`) — w Wariancie B trafia do panelu kontekstu
- Wyniki: pionowy stos, czerwony nagłówek + 10 komórek (`results_grid.py:63-87`)
- Historia: kategoria jako kolorowy chip (`CTkLabel`) — wygląda jak przycisk przez `fg_color`; Phase 4 ujednolica przez `category_chip()`
- Informacje: ciężkie granatowe belki (`info_dialog.py:158-171`)

### Key Discoveries

- Hook architektoniczny: `AppWindow._shell` / `_chrome` / `_view_host` (`app_window.py:55-69`)
- Tokeny chrome w `theme.py`; widżety CTk w `neuroflag.json` — oba muszą być zsynchronizowane
- `test_theme.py` wymusi aktualizację po rozdzieleniu koloru akcentu i kontrolek
- Brak testów GUI — weryfikacja manualna + `pytest`/`mypy` dla logiki pomocniczej
- `font_heading()` (20 bold) zdefiniowany, nieużywany — tytuły kart w panelu kontekstu

## Desired End State

Aplikacja uruchamia się z **białym nagłówkiem** (logo NeuroFlag, stepper 1→2→3→4, przyciski Informacje i Historia), **miętowym paskiem 4 px** pod nagłówkiem i **szarym tłem** `#F7F9FC`. Kroki 1–2 pokazują formularz po lewej (60%) i panel kontekstu po prawej (40%); przy szerokości <900 px kolumny układają się pionowo. Stopka stała: Wstecz (ghost) po lewej, jeden primary CTA po prawej. Ekran wyników: lewa kolumna (kategoria w karcie z paskiem bocznym, opis, akcje), prawa (siatka 10 komórek RAG, skalowalna). Historia: chip kategorii zamiast czerwonego przycisku; „Usuń" w pomarańczowym akcencie (`danger_button` → `COLOR_ACCENT`). Informacje: lekkie karty z lewym paskiem granatowym. Pomarańcz na primary CTA i akcjach destruktywnych w historii; radio/checkbox/selector w granacie `#1E3A5F`.

### Weryfikacja końcowa

- Pełny flow: Dane → Plik → Analiza → Wyniki → PDF → Historia — bez regresji funkcjonalnej
- `python -m pytest -q` i `mypy app/ --strict` — pass
- Wizualnie zgodne z mockupem Wariantu B (nagłówek + 2 kolumny + dashboard wyników)

## What We're NOT Doing

- Wariant A (sidebar) — odrzucony przez użytkownika
- Zmiana kolorów RAG (`rag_colors.py`) i algorytmu wyników
- Zmiana nazwy produktu na NEUROD
- Pełne miętowe tło całego okna (tylko pasek akcentu)
- Redesign PDF (poza ewentualną korektą typografii jeśli konieczna — poza zakresem)
- Dark mode
- Drag & drop plików
- Nowa ikona `.exe` z ulotki (osobny task)
- Grafika mózgu w nagłówku — placeholder tekstowy; asset PNG opcjonalny jeśli dostarczony później

## Implementation Approach

Refaktoryzacja od dołu do góry: najpierw tokeny i prymitywy layoutu, potem shell aplikacji (nagłówek/stepper/stopka), następnie migracja widoków jeden po drugim. Widoki zachowują logikę domenową; zmienia się wyłącznie układ i delegacja nawigacji do shell. Stepper aktualizowany przez `AppWindow` na podstawie klasy widoku, nie przez sam widok.

## Critical Implementation Details

**Stepper a widoki opcjonalne:** Krok 3 (Analiza) i opcjonalne mapowanie kanałów nie są osobnymi krokami steppera — stepper pokazuje 4 etykiety (Dane, Plik, Analiza, Wynik), ale podczas `ChannelMappingView` stepper pozostaje na kroku 2 (Plik), a podczas `AnalysisView` na kroku 3. Mapowanie kanałów w Phase 5 staje się modalem — nie zmienia steppera.

**Kolory kontrolek vs test:** Po zmianie `neuroflag.json` test `test_neuroflag_json_accent_colors_match_theme_constants` musi rozdzielić pary „accent” (tylko `CTkButton`) od par „control” (`CheckBox`, `RadioButton`, `OptionMenu` → `COLOR_CONTROL_ACTIVE`). Inaczej test wymusi powrót pomarańcza na checkboxach.

**Stopka a primary CTA:** Widoki rejestrują akcje w shell przez `AppWindow.set_footer(...)` wołane w `__init__`. **`show_view` zawsze woła `_clear_footer()` przed `destroy()`** bieżącego widoku — nie polegaj na per-view `destroy()`. Zapobiega duplikacji i stale state stopki.

## Phase 1: Tokeny designu i prymitywy layoutu

### Overview

Ujednolicenie palety Wariantu B i dodanie reużywalnych komponentów layoutu, na których zbuduje się shell i widoki.

### Changes Required

#### 1. Rozszerzenie tokenów w theme.py

**File**: `app/ui/theme.py`

**Intent**: Dodać stałe Wariantu B i rozdzielić kolor akcentu (CTA) od koloru kontrolek formularza.

**Contract**: Nowe stałe:
- `COLOR_HEADER_BG = "#FFFFFF"`
- `COLOR_MINT_STRIPE = "#B8D8D0"`
- `COLOR_NAVY = "#1E3A5F"` (nagłówki sekcji, aktywny krok steppera)
- `COLOR_CONTROL_ACTIVE = "#1E3A5F"` (zaznaczenie radio/checkbox/selector)
- `COLOR_CONTROL_BORDER = "#CBD5E0"`
- `CONTENT_MAX_WIDTH = 960`
- `COL_FORM_WEIGHT = 3`, `COL_CONTEXT_WEIGHT = 2` (proporcja 60/40)
- `BREAKPOINT_STACK_COLS = 900`
- `COLOR_CARD = "#FFFFFF"` (alias kart formularzy; tożsamy z `COLOR_SURFACE_ELEVATED`)

Zachować istniejące `COLOR_ACCENT*` dla przycisków primary.

#### 2. Aktualizacja neuroflag.json

**File**: `app/ui/assets/themes/neuroflag.json`

**Intent**: Pomarańcz tylko na `CTkButton` (i progress/slider jeśli używane jako wskaźnik postępu); kontrolki formularza w granacie.

**Contract**: `CTkCheckBox`, `CTkRadioButton`, `CTkOptionMenu`, `CTkSegmentedButton` — `fg_color` / `selected_color` → `#1E3A5F`; hover → ciemniejszy granat `#152E4A`. `CTkButton` bez zmian (pomarańcz).

#### 3. Test synchronizacji kolorów

**File**: `tests/unit/test_theme.py`

**Intent**: Test musi odzwierciedlać nowy podział accent vs control.

**Contract**: `_accent_pairs` — tylko `CTkButton` (+ progress/slider jeśli nadal accent). Nowa funkcja `_control_pairs` weryfikuje `CheckBox`/`RadioButton`/`OptionMenu`/`SegmentedButton` względem `COLOR_CONTROL_ACTIVE`.

#### 4. Prymitywy layoutu w widgets.py

**File**: `app/ui/components/widgets.py`

**Intent**: Wyciągnąć powtarzalne wzorce kart, panelu kontekstu i układu dwukolumnowego.

**Contract**: Nowe fabryki:
- `surface_card(parent) -> CTkFrame` — biała karta z borderem (`COLOR_CARD` / `COLOR_BORDER`, `corner_radius=12`)
- `context_panel(parent, title: str, body: str, *, icon: str = "🔒") -> CTkFrame` — panel prawej kolumny na `COLOR_SURFACE`
- `two_column_body(parent) -> tuple[CTkFrame, CTkFrame]` — grid 3:2 z `columnconfigure` weight; zwraca `(form_col, context_col)`
- `category_chip(parent, text, bg, fg) -> CTkLabel` — zaokrąglony badge (historia)

#### 5. Teksty panelu kontekstu

**File**: `app/ui/context_copy.py` (nowy)

**Intent**: Centralizacja treści paneli kontekstu per krok — łatwe do edycji bez grzebania w widokach.

**Contract**: Moduł ze stałymi `CONTEXT_METADATA` (verbatim z obecnego `info_box` w `metadata_form.py:183-191`), `CONTEXT_FILE_IMPORT` (wymagania `.edf`/`.vhdr`, skrót pomocy) — teksty po polsku, bez µV.

### Success Criteria

#### Automated Verification

- `python -m pytest tests/unit/test_theme.py -q` — pass
- `mypy app/ --strict` — pass
- `python -m pytest -q` — pełny pass

#### Manual Verification

- Uruchomienie aplikacji — checkbox/radio/selector granatowe, przyciski primary pomarańczowe
- Import modułu `context_copy` bez błędów

**Implementation Note**: Po automated verification — potwierdzenie manualne przed Phase 2.

---

## Phase 2: Shell aplikacji (nagłówek, stepper, stopka)

### Overview

Przebudowa `AppWindow` w stały szkielet Wariantu B: nagłówek, miętowy pasek, obszar widoku, stopka nawigacji.

### Changes Required

#### 1. Komponent steppera

**File**: `app/ui/components/stepper.py` (nowy)

**Intent**: Poziomy stepper z 4 krokami: „Dane”, „Plik”, „Analiza”, „Wynik”.

**Contract**: Klasa `WorkflowStepper(CTkFrame)` z metodą `set_active_step(step: int)` (1–4) i `set_completed_through(step: int)`. Aktywny krok: granatowe kółko + etykieta bold; ukończone: checkmark; przyszłe: szare kółko. Bez interakcji kliknięcia (tylko wskaźnik postępu).

#### 2. Mapowanie widok → krok

**File**: `app/ui/navigation.py` (nowy)

**Intent**: Jedno miejsce mapujące klasę widoku na numer kroku steppera.

**Contract**: `VIEW_STEP: dict[type, int]` — `MetadataFormView→1`, `FileImportView→2`, `ChannelMappingView→2`, `AnalysisView→3`, `ResultsGridView→4`, `HistoryView→4` (historia = kontekst wyników).

#### 3. Przebudowa AppWindow

**File**: `app/ui/app_window.py`

**Intent**: Zastąpić minimalny `_chrome` pełnym shellem Wariantu B.

**Contract**:
- `geometry("1000x720")`, `minsize(900, 640)`
- Struktura `_shell`:
  - `_header` (biały): logo/tytuł „NeuroFlag” (lewo), `WorkflowStepper` (środek), `secondary_button` „Informacje” + „Historia” (prawo; Historia disabled gdy `history_store` pusty; handler `_on_history()` → `show_view(HistoryView, return_context=...)`)
  - `_mint_stripe` — `CTkFrame` wys. 4 px, `COLOR_MINT_STRIPE`
  - `_view_host` — `fg_color=COLOR_ROW_BG` (`#F7F9FC`)
  - `_footer` — stały pasek: `secondary_button` Wstecz (lewo), slot na primary CTA (prawo)
- Metody publiczne:
  - `_on_history()` — `show_view(HistoryView, return_target="results" if app_state.analysis_result else "metadata")`
  - `set_footer(*, back_text, back_cmd, back_visible, primary_text, primary_cmd, primary_visible)`
  - `_clear_footer()` — ukrywa/wyzerowuje przyciski stopki; wołane w `show_view` **przed** `destroy()` poprzedniego widoku
  - `_update_stepper_for_view(view_class)` — wołane w `show_view`
- Usunąć stary przycisk Informacje z osobnego miejsca — tylko w headerze

#### 4. Test mapowania nawigacji

**File**: `tests/unit/test_navigation.py` (nowy)

**Intent**: Utrwalić mapowanie widok→krok bez testów GUI.

**Contract**: Asserty na `VIEW_STEP` dla wszystkich 6 klas widoków.

### Success Criteria

#### Automated Verification

- `python -m pytest tests/unit/test_navigation.py tests/unit/test_theme.py -q` — pass
- `mypy app/ --strict` — pass

#### Manual Verification

- Start aplikacji — widoczny nagłówek, miętowy pasek, stepper na kroku 1
- Przejście Metadata→Import→(overlay Analiza)→Results aktualizuje stepper (krok 3 podczas overlay po Phase 5)
- Przycisk Historia w nagłówku (jeśli są wpisy w bazie)

**Implementation Note**: Po automated verification — potwierdzenie manualne przed Phase 3.

**Addendum (impl-review 2026-07-08):** Przycisk Historia zawsze aktywny (pusty stan w `HistoryView`). Nawigacja powrotu: `open_history()` + `return_view=type(bieżący_widok)` zamiast `return_target` string.

**Addendum (impl-review 2026-07-09):** Informacje jako pełnoekranowy `InfoView` (commit `90136fa`) zamiast modala — wzorzec `return_view` + `preserve_stepper=True`, spójny z Historią. `build_info_content()` w `info_dialog.py` pozostaje współdzielonym modułem treści.

---

## Phase 3: Widoki formularzy — układ dwukolumnowy

### Overview

Migracja `MetadataFormView` i `FileImportView` na layout 60/40 z panelem kontekstu; delegacja przycisków nawigacji do stopki shell.

### Changes Required

#### 1. MetadataFormView

**File**: `app/ui/views/metadata_form.py`

**Intent**: Formularz w lewej kolumnie (karta), RODO i pomoc w prawym panelu kontekstu; usunąć dolny `info_box` i przycisk „Dalej” z widoku.

**Contract**:
- Zastąpić `page_container` układem `two_column_body`
- Lewa kolumna: `surface_card` z tytułem „Dane dziecka” i dotychczasowymi polami (wiek, płeć, diagnozy, wykluczenia, ostrzeżenie)
- Prawa kolumna: `context_panel` z `CONTEXT_METADATA`
- W `__init__`: `app_window.set_footer(primary_text="Dalej →", primary_cmd=self._on_continue, back_visible=False)`
- `_on_continue` bez zmian logicznych (walidacja wykluczeń → `FileImportView`)

#### 2. FileImportView

**File**: `app/ui/views/file_import.py`

**Intent**: Import pliku w lewej kolumnie; wymagania formatu i offline w panelu kontekstu; stopka shell.

**Contract**:
- Lewa kolumna: wybór pliku, nazwa pliku, checkbox anonimizacji, status, progress, karta identyfikacji
- Prawa kolumna: `CONTEXT_FILE_IMPORT`
- Stopka: `← Wróć` + `Analizuj` (primary disabled dopóki plik nie wczytany)
- Usunąć `button_row` z widoku
- Zachować logikę `pack_forget` statusu/progressu — bez skoku layoutu karty identyfikacji (stała rezerwa lub `grid` zamiast dynamicznego `pack`)

#### 3. Responsywność kolumn

**File**: `app/ui/components/widgets.py`

**Intent**: Przy wąskim oknie (<900 px) panel kontekstu pod formularzem.

**Contract**: W `two_column_body` bind `<Configure>` na rodzicu — gdy `winfo_width() < BREAKPOINT_STACK_COLS`, przełącz grid z 2 kolumn na 1 (`form_col` row=0, `context_col` row=1).

### Success Criteria

#### Automated Verification

- `mypy app/ --strict` — pass
- `python -m pytest -q` — pass

#### Manual Verification

- Ekran „Dane dziecka”: 2 kolumny na szerokim oknie; RODO w prawym panelu, nie na dole formularza
- Ekran „Wczytaj plik”: panel kontekstu z wymaganiami `.edf`/`.vhdr`
- Stopka: Wstecz/Dalej/Analizuj działają; jeden pomarańczowy primary
- Okno 900 px (minimum): kolumny układają się pionowo bez obcięcia treści

**Implementation Note**: Po automated verification — potwierdzenie manualne przed Phase 4.

---

## Phase 4: Wyniki, historia i Informacje

### Overview

Dashboard wyników 40/60, chipy kategorii w historii, odświeżenie dialogu Informacje — spójne z nowym chrome.

### Changes Required

#### 1. ResultsGridView — dashboard

**File**: `app/ui/views/results_grid.py`

**Intent**: Lewa kolumna: kategoria + opis + akcje; prawa: siatka RAG w karcie; mniej „alarmowy” nagłówek.

**Contract**:
- `two_column_body` z wagami odwróconymi dla wyników: lewa 2, prawa 3 (40/60)
- Lewa: `surface_card` z **lewym paskiem 4 px** w `CATEGORY_COLOR[category]`; tytuł kategorii w `font_heading()`, kolor tekstu `COLOR_TEXT` (nie cały nagłówek na czerwono); opis — **bez przycisków w karcie**
- Prawa: `surface_card` z siatką 5×2; komórki RAG bez zmian (`_COLOR_BG`/`_COLOR_FG`); rozmiar komórki obliczany z szerokości karty zamiast stałych 132×86 (min 120×80, max 150×95)
- Stopka shell: primary „Zapisz raport PDF”; back „← Nowe badanie”. **Usunąć** `btn_row` z widoku. „Historia badań” wyłącznie w nagłówku (F4), nie w widoku wyników

#### 2. HistoryView — chipy i nagłówek

**File**: `app/ui/views/history.py`

**Intent**: Kategoria jako chip; usunąć duplikat nagłówka „Wróć do wyników” na rzecz stopki shell.

**Contract**:
- Zamienić `CTkButton` kategorii na `category_chip`
- Usunąć `header_row` z przyciskiem powrotu — `set_footer(back_text="← Wróć do wyników", back_cmd=...)` gdzie `back_cmd` nawiguje do `ResultsGridView` jeśli `return_target=="results"`, inaczej `MetadataFormView` (parametr `return_target` przekazany z `show_view`)
- Stepper pozostaje na kroku 4

#### 3. InfoDialog — lekkie sekcje

**File**: `app/ui/components/info_dialog.py`

**Intent**: Zastąpić pełne granatowe belki kartami z lewym paskiem (jak wyniki).

**Contract**: `_section_header` → `surface_card` + pasek 4 px `COLOR_NAVY` + tytuł `font_subheading()` w granacie na białym tle; treść sekcji wewnątrz karty.

#### 4. ChannelMappingView — stopka tymczasowa

**File**: `app/ui/views/channel_mapping.py`

**Intent**: Dopóki modal (Phase 5) nie jest gotowy — dopasować do stopki shell.

**Contract**: Usunąć `button_row`; `set_footer(primary_text="Kontynuuj", back_text="← Anuluj", ...)`. Layout jednokolumnowy w karcie wyśrodkowanej (mapowanie to krótka treść).

### Success Criteria

#### Automated Verification

- `mypy app/ --strict` — pass
- `python -m pytest -q` — pass

#### Manual Verification

- Wynik „Wskazanie”: nagłówek czytelny, siatka po prawej, RAG kolory bez zmian
- Historia: chip „Wskazanie” / „Obserwacja” / „Brak” — nie wygląda jak przycisk błędu
- Informacje: sekcje lżejsze, spójne z kartami wyników
- PDF generuje się poprawnie po redesignie wyników

**Implementation Note**: Po automated verification — potwierdzenie manualne przed Phase 5.

**Addendum (impl-review 2026-07-09):** Dashboard wyników pozostaje w układzie pionowym (karta kategorii nad siatką RAG) zamiast `two_column_body` 40/60 — świadoma decyzja UX po implementacji; karty, pasek kategorii i dynamiczna siatka bez zmian.

**Addendum (results-grid-layout 2026-07-09):** Dashboard 40/60 (`two_column_body` lewa 2 / prawa 3) **przywrócony** na ekranie wyników w ramach change `results-grid-layout`. Siatka RAG: Wariant A′ (sekcje po zadaniu, klastry C3|O1), nie płaska 5×2. Szczegóły: `context/changes/results-grid-layout/research.md` → sekcja „Decyzja implementacyjna”.

---

## Phase 5: UX przejść (overlay analizy, modal mapowania)

### Overview

Redukcja „migania” ekranów: analiza jako overlay, mapowanie kanałów jako modal.

### Changes Required

#### 1. Overlay analizy

**File**: `app/ui/components/analysis_overlay.py` (nowy), `app/ui/views/file_import.py`, `app/ui/views/analysis.py`

**Intent**: Zamiast pełnej zamiany widoku na `AnalysisView`, półprzezroczysta nakładka na `_view_host` z progress barem i Anuluj.

**Contract**:
- `AnalysisOverlay(CTkFrame)` — place/regrid nad aktywnym widokiem; woła `app_window._stepper.set_active_step(3)` na starcie, `set_active_step(4)` po sukcesie; wywołuje dotychczasową logikę wątku z `analysis.py`
- `file_import.py` po „Analizuj” → overlay zamiast `show_view(AnalysisView)` (gdy brak mapowania)
- `AnalysisView` pozostaje jako helper z logiką wątku (wyciągnięty do overlay); **nie** jako fallback smoke-test
- Po sukcesie: `show_view(ResultsGridView)`; po błędzie: overlay znika, błąd w karcie na `FileImportView`

#### 2. Modal mapowania kanałów

**File**: `app/ui/components/channel_mapping_dialog.py` (nowy), `app/ui/views/file_import.py`

**Intent**: `ChannelMappingView` jako `CTkToplevel` modalny (wzorzec `_EditStudyDialog` z `history.py`).

**Contract**:
- Dialog ~480×320, wyśrodkowany; dropdowny C3/O1; Kontynuuj/Anuluj
- Po Kontynuuj → zamknij dialog → uruchom overlay analizy
- Usunąć nawigację `show_view(ChannelMappingView)` z importu
- `ChannelMappingView` — deprecate lub thin wrapper wołający dialog

### Success Criteria

#### Automated Verification

- `mypy app/ --strict` — pass
- `python -m pytest -q` — pass

#### Manual Verification

- Analiza: brak pełnoekranowego „Trwa analiza…” — overlay na ekranie importu
- Brak C3/O1: modal mapowania, po zamknięciu powrót do importu
- Anuluj analizy: overlay znika, można ponowić

**Implementation Note**: Faza opcjonalna pod kątem funkcjonalności — aplikacja jest używalna po Phase 4; Phase 5 poprawia płynność UX.

---

## Testing Strategy

### Unit Tests

- `test_theme.py` — synchronizacja accent vs control colors
- `test_navigation.py` — mapowanie widok→krok steppera
- Istniejące testy domenowe — bez regresji (pipeline, PDF, historia)

### Manual Testing Steps

1. Pełny flow z przykładowym `.edf` — wszystkie kroki steppera
2. Wykluczająca diagnoza — ostrzeżenie + blokada Dalej
3. Plik bez C3/O1 — modal mapowania (Phase 5)
4. Wynik z dominacją czerwieni — czytelność dashboardu
5. Historia — chipy, edycja, usuwanie
6. Okno 900 px (minimum) — stack kolumn
7. `--smoke-test` build exe — okno startuje, motyw ładuje się

## Performance Considerations

- Bind `<Configure>` na resize — throttling przez `after_idle` (wzorzec z `bind_auto_hide_scrollbar`)
- Siatka wyników: przeliczanie rozmiaru komórek max raz na resize, nie co frame
- Overlay analizy: jeden `CTkFrame`, nie drugie okno

## Migration Notes

- Brak migracji danych — wyłącznie warstwa prezentacji
- Użytkownicy po aktualizacji widzą nowy layout; flow bez zmian
- Rollback: revert commitów fazowych; `neuroflag.json` i `theme.py` przywracają stary wygląd

## References

- Research: `context/changes/ui-redesign-brand-layout/research.md`
- Mockup: `assets/neuroflag-variant-b-header-2col.png`
- Shell hook: `app/ui/app_window.py:55-88`
- RAG (niezmienne): `app/ui/components/rag_colors.py`
- Prior flyer theme: `context/changes/flyer-theme-info-screen/`

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands.

### Phase 1: Tokeny designu i prymitywy layoutu

#### Automated

- [x] 1.1 `python -m pytest tests/unit/test_theme.py -q` — pass — a43fd54
- [x] 1.2 `mypy app/ --strict` — pass — a43fd54
- [x] 1.3 `python -m pytest -q` — pełny pass — a43fd54

#### Manual

- [x] 1.4 Checkbox/radio/selector granatowe; primary CTA pomarańczowe — a43fd54

### Phase 2: Shell aplikacji (nagłówek, stepper, stopka)

#### Automated

- [x] 2.1 `python -m pytest tests/unit/test_navigation.py tests/unit/test_theme.py -q` — pass — 803c1d7
- [x] 2.2 `mypy app/ --strict` — pass — 803c1d7

#### Manual

- [x] 2.3 Nagłówek, miętowy pasek, stepper aktualizuje się po nawigacji — 803c1d7
- [x] 2.4 Przycisk Historia w nagłówku (zawsze aktywny; pusty stan w widoku) — 803c1d7

### Phase 3: Widoki formularzy — układ dwukolumnowy

#### Automated

- [x] 3.1 `mypy app/ --strict` — pass — c0047d1
- [x] 3.2 `python -m pytest -q` — pass — c0047d1

#### Manual

- [x] 3.3 Metadata i import: 2 kolumny, panel kontekstu, stopka shell — c0047d1
- [x] 3.4 Okno 900 px (minimum): kolumny stackują się pionowo — c0047d1

### Phase 4: Wyniki, historia i Informacje

#### Automated

- [x] 4.1 `mypy app/ --strict` — pass — 424e67b
- [x] 4.2 `python -m pytest -q` — pass — 424e67b

#### Manual

- [x] 4.3 Dashboard wyników 40/60; RAG bez zmian — 424e67b
- [x] 4.4 Historia: chipy kategorii; Informacje: lekkie karty — 424e67b
- [x] 4.5 PDF generuje się poprawnie — 424e67b

### Phase 5: UX przejść (overlay analizy, modal mapowania)

#### Automated

- [x] 5.1 `mypy app/ --strict` — pass — c48f64b
- [x] 5.2 `python -m pytest -q` — pass — c48f64b

#### Manual

- [x] 5.3 Overlay analizy zamiast pełnego ekranu — c48f64b
- [x] 5.4 Modal mapowania kanałów; Anuluj działa — c48f64b
- [x] 5.5 Anuluj analizy: overlay znika, można ponowić — c48f64b
