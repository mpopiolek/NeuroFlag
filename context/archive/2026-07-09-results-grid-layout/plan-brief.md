# Siatka wyników A′ — PDF i domknięcie change — Plan Brief

> Full plan: `context/changes/results-grid-layout/plan.md`
> Research: `context/changes/results-grid-layout/research.md`

## What & Why

Ekran wyników ma już układ **Wariant A′** (sekcje OO/OZ/ZP, klastry C3|O1, w komórce tylko pasmo). Raport PDF nadal renderuje płaską siatkę 2×5 w kolejności `norms.json` — użytkownik oczekuje **spójności print vs ekran**. Ten plan domyka change: wspólna logika sortowania, PDF A′, testy i impl-review (UI wdrożone wcześniej bez planu).

## Starting Point

- **UI (gotowe):** `app/ui/views/results_grid.py` — commit `3729d27`; dashboard 40/60, `_TASK_ORDER` / `_cells_for_task_channel()` lokalnie w widoku.
- **PDF (stary układ):** `app/reports/pdf_generator.py:205-251` — tabela 2×5, w komórce kanał + zadanie + pasmo.
- **Testy PDF:** `tests/unit/test_pdf_generator.py` — asercje metadanych/keywords, brak asercji układu wizualnego.
- **Decyzje użytkownika (2026-07-09):** PDF odzwierciedla A′; `_CELL_W=88` bez skalowania responsywnego; plan + impl-review nadrabiamy teraz.

## Desired End State

Raport PDF grupuje 10 komórek identycznie jak ekran (OO → OZ → ZP, C3 | O1, etykieta kanału nad klastrem, w kafelku tylko pasmo). Logika sortowania jest w jednym module domenowym importowanym przez UI i PDF. `impl-review.md` potwierdza zgodność UI + PDF z research „Decyzja implementacyjna”. Kolejność `AnalysisResult.cells` w pipeline bez zmian.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|----------|--------|-------------------|--------|
| Układ PDF | Wariant A′ (jak UI) | Spójność ekran ↔ wydruk dla pedagoga | User / Plan |
| Kolejność danych | Bez zmian w pipeline | Kalibracja, historia, norms.json wymagają stałej tablicy | Research |
| Rozmiar komórek UI | `_CELL_W=88` bez skalowania | Użytkownik: domyślnie OK | User |
| Wspólna logika | Moduł `app/domain/cell_layout.py` | Unikaj duplikacji sortowania UI vs PDF | Plan |
| impl-review | Pełny (UI retro + PDF) | Change poszedł research → implementacja bez planu | User |

## Scope

**In scope:**
- Ekstrakcja sortowania/prezentacji do `app/domain/cell_layout.py`
- Refaktor importu w `results_grid.py`
- Sekcja siatki w `pdf_generator.py` — layout A′
- Aktualizacja / rozszerzenie testów PDF
- `context/changes/results-grid-layout/reviews/impl-review.md`

**Out of scope:**
- Zmiana kolejności `result.cells` / `classify()` / historii
- Responsywne skalowanie `_CELL_W` w UI
- Legenda RAG pod siatką (open question #4 z research)
- Wycentrowanie sekcji OZ (open question #3 — zostaje wyrównanie do lewej jak UI)

## Architecture / Approach

```
AnalysisResult.cells (stała kolejność norms.json)
        │
        ▼
app/domain/cell_layout.py  ← TASK/CHANNEL/BAND order + cells_for_task_channel()
        │
   ┌────┴────┐
   ▼         ▼
results_grid.py   pdf_generator.py
(CTk A′)          (ReportLab flowables: sekcje + tabele klastrów)
```

ReportLab: zamiast jednej tabeli 2×5 — sekwencja `Paragraph` (nagłówek zadania) + `Table` (wiersz etykiet C3/O1, wiersz kolorowych komórek z samym pasmem) + cienka linia między sekcjami.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|-------|------------------|----------|
| 1. UI A′ (done) | Dashboard 40/60, siatka zadań | — (retro w impl-review) |
| 2. Wspólna logika | `cell_layout.py` + refaktor UI | Import cykliczny UI↔reports — unikać przez moduł domenowy |
| 3. PDF A′ | Raport grupowany jak ekran | Szerokość A4 przy 3 komórkach O1 w OO |
| 4. Testy + impl-review | Testy PDF, raport review | ReportLab kompresuje treść — asercje story vs surowe bajty |

**Prerequisites:** UI A′ na branchu (`3729d27`); research „Decyzja implementacyjna”.

**Estimated effort:** ~1–2 sesje (fazy 2–4; faza 1 już zrobiona).

## Open Risks & Assumptions

- Sekcja OO z 3 komórkami O1 musi mieścić się w szerokości A4 (~17 cm treści) — stałe szerokości kafelków w PDF, bez skalowania UI.
- Testy PDF oparte na monkeypatch `Paragraph` / inspekcji story są stabilniejsze niż parsowanie skompresowanych strumieni.
- impl-review UI będzie retroaktywne względem research, nie względem planu z fazy 1.

## Success Criteria (Summary)

- PDF wizualnie grupuje wyniki jak ekran (3 sekcje zadań, C3|O1, tylko pasmo w kafelku).
- UI i PDF importują sortowanie z `cell_layout.py`.
- `pytest` + `mypy app/ --strict` zielone; impl-review bez krytycznych driftów.
