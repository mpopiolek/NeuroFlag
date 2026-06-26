# Dane osobowe w plikach EEG — Plan Brief

> Pełny plan: `context/changes/eeg-file-personal-data/plan.md`
> Research: `context/changes/eeg-file-personal-data/research.md`

## What & Why

Pliki EEG (`.edf`, BrainVision) **mogą zawierać dane osobowe i zdrowotne** — imię, ID pacjenta, datę nagrania w nagłówku oraz sygnał biometryczny. Aplikacja nie wyświetla tych danych, ale MNE-Python ładuje je do RAM. Brak komunikacji w GUI o trybie offline i zakresie przetwarzania to luka compliance; pełna ścieżka pliku w UI może ujawniać ID pacjenta. Zmiana domyka te braki i dodaje opcję czyszczenia nagłówka przed analizą.

## Starting Point

Aplikacja ma działający pipeline EEG i generuje PDF z klauzulą odpowiedzialności medycznej. W `FileImportView` wyświetlana jest pełna ścieżka (`str(path)`). W żadnym widoku GUI nie ma tekstu o trybie offline ani zakresie przetwarzania. Flagę anonimizacji nagłówka w `pipeline.run()` i `AppState` trzeba zbudować od zera.

## Desired End State

Użytkownik widzi w pierwszym ekranie aplikacji stały blok informacyjny: „Analiza odbywa się wyłącznie na tym komputerze…". Ścieżka pliku pokazuje tylko basename. PDF zawiera zdanie o lokalnym trybie. Opcjonalny checkbox „Wyczyść dane identyfikacyjne z nagłówka…" pozwala wyczyścić `subject_info` / `meas_date` z `raw.info` przed analizą.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|---|---|---|---|
| Gdzie wyświetlać informację privacy | Statyczny blok w MetadataFormView | Widoczny przed każdym badaniem, bez persystencji, minimalna implementacja | Plan |
| Ścieżka pliku w UI | Tylko basename (`path.name`) | Usuwa ekspozycję folderu z potencjalnym ID pacjenta jedną linią kodu | Research + Plan |
| Informacja privacy w PDF | Rozszerzyć istniejący DISCLAIMER_PL | Jeden punkt edycji, czytelne dla użytkownika bez nowej sekcji | Plan |
| Anonimizacja nagłówka | Checkbox w FileImportView, domyślnie odznaczony | Daje kontrolę użytkownikowi bez wymuszania; `raw.anonymize()` gotowe w MNE | Research (OpenQ #2) + Plan |
| Persystencja checkboxa | Brak (reset przy nowym uruchomieniu) | Aplikacja offline, brak pliku konfiguracyjnego użytkownika | Plan |
| DPIA / polityka prywatności producenta | Poza zakresem | Praca prawna po stronie placówki jako administratora danych | Research |

## Scope

**In scope:**
- Blok informacyjny w `MetadataFormView`
- `path.name` zamiast `str(path)` w `FileImportView`
- Rozszerzenie `DISCLAIMER_PL` w `pdf_generator.py`
- `anonymize_header` flag w `AppState`, `pipeline.run()`, `AnalysisView`
- Checkbox w `FileImportView`
- 2 testy jednostkowe dla flagi anonimizacji

**Out of scope:**
- Fizyczne usuwanie PII z pliku na dysku
- Tooltip z pełną ścieżką (brak natywnego tooltipa w CTk)
- Jednorazowy modal powitalny z persystencją
- DPIA, polityka prywatności, klasyfikacja prawna RODO

## Architecture / Approach

Trzy niezależne obszary bez wzajemnych zależności:
- **Widok** — tekst + basename (MetadataFormView, FileImportView)
- **PDF** — zmiana stałej tekstowej (pdf_generator.py)
- **Pipeline** — nowy keyword-arg `anonymize_header` przekazywany przez `AppState` → `AnalysisView` → `pipeline.run()` → `raw.anonymize()`

Dane przepływają: `FileImportView.checkbox` → `AppState.anonymize_header` → `AnalysisView._worker` → `pipeline.run(anonymize_header=…)` → `raw.anonymize()` po `_load_raw()`.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Informacja w GUI + basename | Blok privacy w MetadataForm; basename ścieżki | Zero — czysto widokowe |
| 2. Rozszerzenie klauzuli PDF | Zdanie o offline w DISCLAIMER_PL | Długość tekstu — weryfikacja wizualna PDF |
| 3. Anonimizacja nagłówka EDF | Checkbox + pipeline flag + 2 testy | `raw.anonymize()` dostępność w MNE 1.8.0 — do weryfikacji |

**Prerequisites:** Brak — zmiany niezależne od innych bieżących zmian.
**Estimated effort:** ~1–2 sesje; 3 fazy, łącznie ~8–12 plików.

## Open Risks & Assumptions

- `mne.io.BaseRaw.anonymize()` jest API publicznym w MNE 1.8.0 — wymaga weryfikacji przy implementacji Phase 3
- Czyszczenie `meas_date` przez `anonymize()` nie wpływa na PDF (używa `result.analyzed_at`, nie daty pliku) — założenie potwierdzone code-review pipeline
- DISCLAIMER_PL po rozszerzeniu może wymagać weryfikacji eksperta domenowego przed wdrożeniem produkcyjnym (TODO w kodzie)

## Success Criteria (Summary)

- Użytkownik otwierający aplikację widzi informację o lokalnym trybie pracy przed pierwszym badaniem
- Ścieżka pliku EEG w UI nie ujawnia struktury katalogów placówki
- Raport PDF potwierdza offline charakter analizy w sekcji klauzuli
