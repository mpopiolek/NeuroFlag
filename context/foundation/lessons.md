# Lessons Learned

> Append-only register of recurring rules and patterns. Re-read at start by /10x-frame, /10x-research, /10x-plan, /10x-plan-review, /10x-implement, /10x-impl-review.

## Touched-set per phase (git commit scope)

**Context:** `git add` podczas phase-end commit w `/10x-implement` (np. change metadata-and-import obok norms-replacement w tym samym commicie).

**Problem:** Szeroki commit miesza niepowiązane foldery `context/changes/<inny-change>/` z kodem bieżącej zmiany — utrudnia review i rollback.

**Rule:** Przy commicie fazy stage wyłącznie touched-set bieżącej zmiany + `plan.md`; nie używaj `git add -A`. Niezwiązane dirty paths zostaw lub commituj w osobnym change.

**Applies to:** `/10x-implement`, `/10x-archive`, ręczne commity agenta

## Zawsze zadawaj pytania po polsku

- **Context**: w całej komunikacji z użytkownikiem
- **Problem**: dłużej zajmuje zrozumienie, gdy pytania są po angielsku
- **Rule**: Zawsze zadawaj pytania użytkownikowi po polsku.
- **Applies to**: all

## CTkLabel wraplength w wąskich kolumnach

**Context:** Ostrzeżenie o diagnozach wykluczających w `MetadataFormView` (krok 1, układ dwukolumnowy).

**Problem:** Stały `wraplength=t.WRAP_WIDTH` (720 px) jest szerszy niż kolumna formularza (~60% okna) — tekst się nie zawija i jest ucięty.

**Rule:** Etykiety z `wraplength` w scrollable frame / wąskiej kolumnie synchronizuj dynamicznie z `winfo_width()` kontenera (wzorzec jak `ResultsGridView._sync_text_wrap`), nie hardkoduj globalnego `WRAP_WIDTH`.

**Applies to:** `/10x-implement` (CustomTkinter, układ dwukolumnowy)

## Grid bez wag wierszy w rozciągniętej karcie

**Context:** Siatka wyników RAG w `ResultsGridView` — sekcje po zadaniu w prawej karcie o stałej wysokości (dashboard 40/60).

**Problem:** `grid_rowconfigure(weight=1)` na sekcjach lub `pack(fill="x", expand=True)` w wysokim rodzicu rozpycha bloki w pionie — duże luki między zadaniami (OO / OZ / ZP).

**Rule:** W scrollowalnej lub rozciągniętej karcie układaj sekcje w `grid` **bez wag wierszy**; treść zakotwicz u góry (`pack(anchor="n")` lub `grid(sticky="nw")`). Odstępy między sekcjami kontroluj explicite (cienka linia + stały `pady`), nie przez `expand`.

**Applies to:** `/10x-implement` (CustomTkinter, siatki wyników, karty o równej wysokości)
