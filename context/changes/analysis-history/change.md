---
id: analysis-history
title: "Historia badań — lokalna baza SQLite z trendami"
status: implemented
created: 2026-06-30
updated: 2026-07-06
roadmap_ref: ~
prd_refs: [US-01-v2, FR-010]
unlocks: []
---

## Cel

Umożliwić pedagogowi przeglądanie i usuwanie historii przeprowadzonych badań przesiewowych.
Każde badanie zapisywane automatycznie do lokalnej bazy SQLite — bez działania użytkownika.
Spełnia kryterium CRUD (Create/Read/Delete) dla certyfikacji MVP.

**Rozszerzenie (Phase 6):** zbieranie wcześniejszych diagnoz psychologiczno-pedagogicznych
(ASD, ADHD, depresja/lęki, dysleksja, inne) w metryce dziecka — zapis lokalny i w PDF,
bez wpływu na algorytm przesiewowy; fundament pod rozszerzanie norm w v2.0.
