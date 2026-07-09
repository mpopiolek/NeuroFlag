# Siatka wyników A′ — PDF i domknięcie change — Implementation Plan

## Overview

Change `results-grid-layout` wdrożył **Wariant A′** na ekranie wyników (commit `3729d27`), ale pominął plan, impl-review i aktualizację PDF. Ten plan domyka change: wydziela wspólną logikę prezentacji komórek, przenosi układ A′ do raportu PDF (decyzja użytkownika), aktualizuje testy i produkuje impl-review obejmujący UI (retro) oraz PDF.

## Current State Analysis

### Co już istnieje

- **UI A′ (shipped):** `app/ui/views/results_grid.py` — `two_column_body(2,3)`, `_build_task_grouped_grid`, klastry C3|O1, komórki 88×56 px z samym `cell.band`; stałe `_TASK_ORDER`, `_CHANNEL_ORDER`, `_BAND_ORDER` i `_cells_for_task_channel()` **lokalnie w widoku**.
- **Research + decyzja:** `context/changes/results-grid-layout/research.md` → sekcja „Decyzja implementacyjna” opisuje kontrakt A′.
- **PDF (stary):** `app/reports/pdf_generator.py:205-251` — tabela ReportLab 2×5, indeks `idx // 5`, w komórce trzy linie (kanał, zadanie, pasmo).
- **Testy PDF:** `tests/unit/test_pdf_generator.py` — metadane, brak µV, keywords; brak asercji układu sekcji.

### Key Discoveries

- `pdf_generator.py` już importuje `TASK_LABELS` z `app/ui/components/rag_colors.py` — wzorzec współdzielenia etykiet PL między UI a PDF istnieje.
- Sortowanie przy renderowaniu **nie wymaga** zmiany `AnalysisResult.cells` (`research.md`, `algorithm.py`) — ten sam kontrakt obowiązuje PDF.
- ReportLab `SimpleDocTemplate` buduje story jako listę flowables — sekcje A′ to sekwencja `Paragraph` + `Table` + `Spacer`, nie jedna macierz 2×5.
- Użytkownik potwierdził: **PDF = A′**; **`_CELL_W=88` bez zmian** responsywnych.

## Desired End State

1. `app/domain/cell_layout.py` eksponuje kolejność wyświetlania (zadanie → kanał → pasmo) i `cells_for_task_channel()` — importowane przez UI i PDF.
2. PDF „Wyniki analizy” renderuje 3 sekcje (OO, OZ, ZP) z klastrami C3 | O1; w kafelku tylko nazwa pasma; kolory RAG z `RAG_COLOR_BG`.
3. Testy jednostkowe weryfikują obecność sekcji zadań i pasm w story PDF (monkeypatch `Paragraph` / helper budujący story).
4. `context/changes/results-grid-layout/reviews/impl-review.md` — pełny review: UI retro (`3729d27`) + PDF vs research „Decyzja implementacyjna”.
5. `mypy app/ --strict` i `pytest -q` — pass.

### Weryfikacja manualna

- Wygeneruj PDF dla wyniku z mieszanymi kolorami i scenariuszem „Wskazanie” — sekcje OO/OZ/ZP widoczne, C3 obok O1, bez płaskiej 2×5.
- Porównaj ekran wyników z PDF — ta sama grupa logiczna komórek.

## What We're NOT Doing

- Zmiana kolejności `result.cells`, `classify()`, historii SQLite, kalibracji
- Responsywne zmniejszanie `_CELL_W` w UI przy wąskiej kolumnie 60%
- Legenda RAG pod siatką (open question #4 z research — poza zakresem)
- Wycentrowanie sekcji OZ (2 komórki) — zostaje wyrównanie do lewej jak w UI
- Zmiana rozmiaru okna, scrolla, dashboardu 40/60 (już wdrożone)

## Implementation Approach

**Wspólny moduł domenowy** (`cell_layout.py`) — czyste funkcje na `CellResult`, bez importów CustomTkinter ani ReportLab. UI i PDF importują stamtąd; `results_grid.py` usuwa lokalne duplikaty stałych.

**PDF** — zastąpić blok 2×5 helperem `_build_rag_grid_story(cells, styles) -> list[Flowable]` budującym sekcje jak UI. Szerokości kafelków w cm dopasowane do A4 (content ~17 cm); max 3 kafelki w klastrze O1 (OO).

**impl-review** — po fazach 2–3 uruchomić `/10x-impl-review results-grid-layout`; UI ocenić retro względem `research.md` „Decyzja implementacyjna” (plan fazy 1 = dokumentacja tego, co już jest).

## Phase 1: UI A′ — ekran wyników (pre-completed)

### Overview

Dashboard 40/60 i siatka Wariant A′ wdrożone w `results_grid.py` przed utworzeniem planu. Faza służy jako punkt odniesienia dla impl-review; brak dodatkowego kodu poza ewentualnym refaktorem importu w fazie 2.

### Changes Required:

#### 1. ResultsGridView — layout A′

**File**: `app/ui/views/results_grid.py`

**Intent**: Już zrealizowane — sekcje po zadaniu, klastry C3|O1, komórka = pasmo, grid bez wag wierszy, anchor `"n"`.

**Contract**: Zgodność z tabelą w `research.md` → „Decyzja implementacyjna”. Commit referencyjny: `3729d27`.

### Success Criteria:

#### Automated Verification:

- `python -m mypy app/ui/views/results_grid.py --strict`
- `python -m pytest tests/unit/test_navigation.py -q`

#### Manual Verification:

- Lewa 40% / prawa 60%, równe karty; brak dużych luk między zadaniami; linia C3|O1 tuż za ostatnią komórką C3

**Implementation Note**: Faza ukończona przed planem — impl-review w fazie 4 weryfikuje retro.

---

## Phase 2: Wspólna logika prezentacji komórek

### Overview

Wydzielić sortowanie i stałe kolejności z widoku UI do modułu domenowego, aby PDF i UI nie rozjechały się przy kolejnych zmianach.

### Changes Required:

#### 1. Moduł cell_layout

**File**: `app/domain/cell_layout.py` (nowy)

**Intent**: Jedno źródło prawdy dla kolejności wyświetlania komórek RAG (nie pipeline).

**Contract**:
- `TASK_DISPLAY_ORDER: tuple[str, ...] = ("OO", "OZ", "ZP")`
- `CHANNEL_DISPLAY_ORDER: tuple[str, ...] = ("C3", "O1")`
- `BAND_DISPLAY_ORDER: tuple[str, ...] = ("Theta", "Beta2", "Beta1", "Delta")`
- `def cells_for_task_channel(cells: Sequence[CellResult], task: str, channel: str) -> list[CellResult]` — filtr + sort po `_BAND_DISPLAY_ORDER`
- Pełne adnotacje typów, `from __future__ import annotations`

#### 2. Refaktor ResultsGridView

**File**: `app/ui/views/results_grid.py`

**Intent**: Usunąć lokalne `_TASK_ORDER`, `_CHANNEL_ORDER`, `_BAND_ORDER`, `_cells_for_task_channel`, `_band_sort_key`; import z `app.domain.cell_layout`.

**Contract**: Zachowanie wizualne identyczne z `3729d27`; `_CELL_W = 88` bez zmian.

#### 3. Testy cell_layout

**File**: `tests/unit/test_cell_layout.py` (nowy)

**Intent**: Sprawdzić sortowanie pasm i filtrowanie po zadaniu/kanale na fixture 10 komórek.

**Contract**: OO/C3 zwraca posortowane pasma; nieznane pasmo trafia na koniec listy.

### Success Criteria:

#### Automated Verification:

- `python -m mypy app/domain/cell_layout.py app/ui/views/results_grid.py --strict`
- `python -m pytest tests/unit/test_cell_layout.py tests/unit/test_navigation.py -q`

#### Manual Verification:

- Krótki smoke UI — layout identyczny jak przed refaktorem importu

**Implementation Note**: Po automated verification — potwierdzenie manualne przed fazą 3.

---

## Phase 3: PDF — siatka Wariant A′

### Overview

Zastąpić płaską tabelę 2×5 w raporcie PDF układem sekcji zgodnym z ekranem i research „Decyzja implementacyjna”.

### Changes Required:

#### 1. Helper story siatki RAG

**File**: `app/reports/pdf_generator.py`

**Intent**: Sekcja „Wyniki analizy” buduje flowables grupowane po zadaniu z klastrami C3 | O1.

**Contract**:
- Import: `TASK_DISPLAY_ORDER`, `CHANNEL_DISPLAY_ORDER`, `cells_for_task_channel` z `app.domain.cell_layout`; `TASK_LABELS`, `RAG_COLOR_BG` bez zmian semantyki kolorów
- Dla każdego zadania w `TASK_DISPLAY_ORDER`:
  - (opcjonalnie) cienka linia / `Spacer` między sekcjami — analogicznie do UI
  - `Paragraph` z `TASK_LABELS[task]` (`style_h3`)
  - `Table` dwuwierszowa: wiersz 0 — etykiety „C3” / „O1”; wiersz 1 — kolorowe komórki (tylko `cell.band`, bold, kolor tekstu jak dziś RED/GREEN → white)
  - Kolumna pośrednia: wąska pionowa linia (border) między klastrami — wizualny odpowiednik UI
- Usunąć pętlę `idx // 5` i tabelę `grid_data` 2×5
- **Nigdy** nie emitować wartości µV

#### 2. Szerokości kafelków PDF

**File**: `app/reports/pdf_generator.py`

**Intent**: 3 kafelki O1 w sekcji OO mieszczą się w szerokości treści A4.

**Contract**: Stałe szerokości w `cm` (np. kafelek ~2.0–2.2 cm, gap ~0.15 cm); jeśli klastr ma mniej komórek, puste miejsca bez fałszywych ramek.

### Success Criteria:

#### Automated Verification:

- `python -m mypy app/reports/pdf_generator.py --strict`
- `python -m pytest tests/unit/test_pdf_generator.py -q`

#### Manual Verification:

- PDF dla Wskazania — sekcje czytelne, nie „ściana” bez nagłówków zadań
- PDF dla mieszanych kolorów — kolory RAG zgodne z ekranem
- Zapis PDF z widoku wyników działa bez regresji

**Implementation Note**: Po automated verification — porównanie ekran vs PDF przed fazą 4.

---

## Phase 4: Testy PDF + impl-review

### Overview

Rozszerzyć testy o kontrakt layoutu A′ i wyprodukować raport impl-review dla całego change (UI retro + PDF).

### Changes Required:

#### 1. Asercje layoutu PDF

**File**: `tests/unit/test_pdf_generator.py`

**Intent**: Wykryć regresję powrotu do płaskiej 2×5 lub brak sekcji zadań.

**Contract**:
- Test z monkeypatch `Paragraph`: story zawiera etykiety z `TASK_LABELS` dla OO, OZ, ZP (pełne nazwy PL)
- Test: story zawiera nazwy pasm z fixture `_CELLS` (np. „Theta”, „Beta1”) w kontekście siatki
- Zachować istniejące testy metadanych / brak µV

#### 2. Raport impl-review

**File**: `context/changes/results-grid-layout/reviews/impl-review.md`

**Intent**: Udokumentować zgodność implementacji z research i planem; retro UI + weryfikacja PDF.

**Contract**: Format jak `context/changes/ui-redesign-brand-layout/reviews/impl-review.md` (nagłówek `<!-- IMPL-REVIEW-REPORT -->`, werdykty, findings, automated verification).

#### 3. Aktualizacja research

**File**: `context/changes/results-grid-layout/research.md`

**Intent**: Zaktualizować linię „PDF: nadal płaska 2×5” — po fazie 3 PDF = A′.

**Contract**: Sekcja „Decyzja implementacyjna” — wiersz PDF odzwierciedla decyzję użytkownika.

### Success Criteria:

#### Automated Verification:

- `python -m pytest -q`
- `python -m mypy app/ --strict`

#### Manual Verification:

- impl-review: brak CRITICAL drift vs „Decyzja implementacyjna”
- Progress w plan.md — wszystkie checkboxy `[x]` z sha commitów

**Implementation Note**: Po review — aktualizacja `change.md` `status: implemented`.

---

## Testing Strategy

### Unit Tests:

- `test_cell_layout.py` — sortowanie, filtry, edge: nieznane pasmo
- `test_pdf_generator.py` — rozszerzenie o sekcje zadań w story; regresja metadanych

### Integration Tests:

- Brak nowych E2E — manualny zapis PDF z GUI wystarczy

### Manual Testing Steps:

1. Uruchom app → wynik z ≥5 czerwonymi → sekcje OO/OZ/ZP na ekranie
2. Zapisz PDF → te same sekcje i grupowanie
3. Okno min 900 px — dashboard 40/60 bez regresji
4. Historia → podgląd wyniku — layout bez zmian (ten sam widok)

## Performance Considerations

- PDF: kilka małych tabel zamiast jednej — pomijalny overhead ReportLab
- Brak dodatkowego sortowania w pipeline — tylko O(10) przy generowaniu raportu

## Migration Notes

- Istniejące PDF wygenerowane przed zmianą pozostają w starym układzie — brak migracji
- Historia SQLite nie wymaga zmian — przechowuje `AnalysisResult`, nie layout

## References

- Research: `context/changes/results-grid-layout/research.md`
- UI commit: `3729d27`
- PDF obecny: `app/reports/pdf_generator.py:205-251`
- Wzorzec review: `context/changes/ui-redesign-brand-layout/reviews/impl-review.md`
- Lekcja layoutu: `context/foundation/lessons.md` → „Grid bez wag wierszy”

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands.

### Phase 1: UI A′ — ekran wyników (pre-completed)

#### Automated

- [x] 1.1 `python -m mypy app/ui/views/results_grid.py --strict` — 3729d27
- [x] 1.2 `python -m pytest tests/unit/test_navigation.py -q` — 3729d27

#### Manual

- [ ] 1.3 Smoke UI: dashboard 40/60, sekcje bez luk, linia C3|O1

### Phase 2: Wspólna logika prezentacji komórek

#### Automated

- [x] 2.1 `python -m mypy app/domain/cell_layout.py app/ui/views/results_grid.py --strict`
- [x] 2.2 `python -m pytest tests/unit/test_cell_layout.py tests/unit/test_navigation.py -q`

#### Manual

- [x] 2.3 Smoke UI po refaktorze importu — layout identyczny

### Phase 3: PDF — siatka Wariant A′

#### Automated

- [ ] 3.1 `python -m mypy app/reports/pdf_generator.py --strict`
- [ ] 3.2 `python -m pytest tests/unit/test_pdf_generator.py -q`

#### Manual

- [ ] 3.3 PDF Wskazanie + mieszane kolory; zapis z widoku wyników

### Phase 4: Testy PDF + impl-review

#### Automated

- [ ] 4.1 `python -m pytest -q`
- [ ] 4.2 `python -m mypy app/ --strict`

#### Manual

- [ ] 4.3 impl-review bez CRITICAL drift; `change.md` → `implemented`
