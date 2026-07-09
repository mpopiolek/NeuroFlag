---
id: results-grid-layout
title: "Czytelniejszy układ siatki wyników RAG"
status: implemented
created: 2026-07-09
updated: 2026-07-09
---

> **Decyzja UX 2026-07-09:** Wariant A′ (sekcje po zadaniu + klastry C3/O1 z linią podziału, w komórce tylko pasmo) — wdrożony w `results_grid.py`. Dashboard wyników: `two_column_body(left_weight=2, right_weight=3)` → 40% kategoria / 60% siatka; obie karty równej wysokości (`pack(fill="both", expand=True)`).

Badanie alternatywnych układów siatki 10 komórek RAG na ekranie wyników — grupowanie po zadaniu, paśmie lub macierzy kanał×zadanie w celu zwiększenia czytelności, szczególnie przy dominacji jednego koloru (np. Wskazanie).
