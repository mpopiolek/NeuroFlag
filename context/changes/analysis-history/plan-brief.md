# Historia badań — Plan Brief

> Full plan: `context/changes/analysis-history/plan.md`

## What & Why

Dodanie lokalnej historii badań przesiewowych: każde zakończone badanie jest automatycznie
zapisywane do SQLite (`history.db` obok `neuroflag.exe`). Pedagog może przeglądać listę
poprzednich badań i usuwać rekordy. Funkcja spełnia kryterium CRUD dla certyfikacji MVP
i stanowi fundament pod trendy terapeutyczne planowane w v2.0.

**Phase 6** rozszerza metrykę o opcjonalne, wcześniej postawione diagnozy
(ASD, ADHD, depresja/lęki, dysleksja, inne) — zbierane lokalnie obok inicjałów i roku
urodzenia, bez wpływu na wynik przesiewowy w v1.0, zgodnie z FR-010.

## Starting Point

Historia badań (fazy 1–5) jest zaimplementowana: `history.db`, auto-zapis po analizie,
`HistoryView`, pola identyfikacyjne na ekranie importu pliku. Brakuje zbierania
diagnoz informacyjnych (ASD, ADHD, depresja/lęki, dysleksja, inne) — Phase 6.

## Desired End State

Po zakończeniu analizy wynik jest automatycznie zapisywany w lokalnej bazie SQLite.
Na ekranie wyników pojawia się przycisk „Historia badań" (gdy historia niepusta),
otwierający listę z datą, identyfikatorem dziecka i kolorową kategorią wynikową.
Pedagog może usunąć wybrany rekord. Komunikat RODO pojawia się jednorazowo przy pierwszym zapisie.

Po Phase 6: formularz metryki pozwala opcjonalnie zaznaczyć wcześniejsze diagnozy;
dane trafiają do `history.db` (`diagnoses_json`) i do raportu PDF — algorytm przesiewowy
bez zmian.

## Key Decisions Made

| Decyzja | Wybór | Dlaczego | Źródło |
|---------|-------|----------|--------|
| Persystencja | SQLite (`history.db`) | Wbudowany w Python, zero zależności, jeden plik | Plan |
| Kiedy zapisać | Automatycznie po analizie | Bez wysiłku użytkownika — nie straci rekordu | Plan |
| Identyfikacja dziecka | Inicjały + data urodzenia + opcjonalna etykieta | RODO-friendly, czytelne dla pedagoga | Plan |
| Dostęp do historii | Przycisk w wynikach (gdy historia niepusta) | Minimalny zasięg UI — nie rozbudowuje nawigacji | Plan |
| Akcje na rekordzie | Podgląd + usunięcie | MVP scope; prefill do formularza = v2.0 | Plan |
| RODO komunikat | Jednorazowy przy pierwszym zapisie | Wymagany przez użytkowniczkę, przechowywany w `settings` w tej samej DB | Plan |
| Diagnozy informacyjne | Osobny enum `ClinicalDiagnosis`, nie wpływa na algorytm | Zbieranie danych na v2.0 (normy/ML); wykluczenia nadal blokują analizę | FR-010, rozmowa 2026-07-06 |
| Diagnozy w PDF | Tak, gdy zaznaczone | FR-010 wymaga metryki w raporcie; wykluczenia nie trafiają do PDF | Plan |

## Scope

**In scope:**
- Nowy moduł `app/storage/history.py` (`HistoryStore`, `StudyRecord`, `resolve_history_db_path`)
- Opcjonalne pola w `PatientMetadata`: `initials`, `birth_date`, `custom_label`
- 3 opcjonalne pola UI w `MetadataFormView`
- Auto-zapis w `AnalysisView._on_done()` + jednorazowy komunikat RODO
- Nowy `HistoryView` (lista + usuwanie)
- Przycisk „Historia badań" w `ResultsGridView`
- 13 testów jednostkowych dla `HistoryStore`

**In scope (Phase 6):**
- Enum `ClinicalDiagnosis` + pola `diagnoses` / `other_diagnosis_note` w `PatientMetadata`
- Sekcja UI „Zdiagnozowane wcześniej (opcjonalnie)" w `MetadataFormView`
- Kolumna `diagnoses_json` w `history.db` (migracja ALTER TABLE)
- Wiersz diagnoz w raporcie PDF
- 6 testów jednostkowych (typy, storage, PDF)

**Out of scope:**
- Prefill formularza z historii (v2.0)
- Wykresy trendów / porównania badań (v2.0)
- Szyfrowanie bazy (v2.0)
- Eksport CSV/Excel (v2.0)
- Wyszukiwanie/filtrowanie listy (v2.0)
- Użycie diagnoz w algorytmie przesiewowym lub segmentacji norm (v2.0)
- Filtrowanie historii po diagnozie (v2.0)

## Architecture / Approach

```
app/storage/
  __init__.py
  history.py          ← HistoryStore (SQLite), StudyRecord, resolve_history_db_path()

app/domain/types.py   ← +3 pola opt. w PatientMetadata
app/ui/views/
  metadata_form.py    ← +3 pola UI
  analysis.py         ← auto-zapis w _on_done()
  results_grid.py     ← przycisk "Historia badań"
  history.py          ← nowy widok listy

history.db            ← obok neuroflag.exe (= obok norms.json)
```

`HistoryStore` otwiera/zamyka połączenie per-operacja lub trzyma je jako atrybut instancji.
Inicjalizacja schematu (`CREATE TABLE IF NOT EXISTS`) przy pierwszym `__init__`.

## Phases at a Glance

| Faza | Co dostarcza | Główne ryzyko |
|------|-------------|---------------|
| 1. Storage layer | `HistoryStore` + schema SQLite | Poprawna lokalizacja DB w trybie PyInstaller vs dev |
| 2. Typy + formularz | `PatientMetadata` z inicjałami, pola UI | Kompatybilność wsteczna istniejących testów |
| 3. Auto-zapis | Hook w `_on_done()`, komunikat RODO | Błąd SQLite nie może przerywać głównego flow |
| 4. HistoryView + przycisk | Widok listy, usuwanie, nawigacja | Powrót do `ResultsGridView` gdy stan już wyczyszczony |
| 5. Testy | 13 testów jednostkowych | Izolacja między testami (tmp_path) |
| 6. Diagnozy informacyjne | Enum + UI + `diagnoses_json` + PDF | Migracja schematu na istniejących DB; RODO art. 9 |

**Prerequisites:** Fazy 1–5 ukończone.
**Estimated effort:** Phase 6 ~1 sesja

## Open Risks & Assumptions

- **Powrót z HistoryView**: `show_view(ResultsGridView)` wymaga aby `app_state.analysis_result`
  był nadal ustawiony — sprawdzić czy reset w `_on_new_study` nie jest wywoływany przed
  nawigacją do historii (obecnie nie jest, ale warto zabezpieczyć).
- **AGENTS.md**: zaktualizowany po fazach 1–5.
- **Diagnozy a RODO**: diagnozy to dane wrażliwe (art. 9) — sekcja opcjonalna,
  infobox o lokalnym zapisie; podstawa prawna po stronie placówki (poza scope MVP).

## Success Criteria (Summary)

- Po dwóch badaniach historia pokazuje dwa rekordy; po usunięciu jednego — jeden
- Komunikat RODO pojawia się dokładnie raz (przy pierwszym badaniu)
- `python -m pytest tests/unit/test_history.py -v` — 13 testów zielonych
