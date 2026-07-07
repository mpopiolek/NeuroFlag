# Odczyt inicjałów i roku urodzenia z DigiTrack — Plan

## Cel

Po wczytaniu pliku `.EEG` (DigiTrack) w ekranie importu automatycznie wypełnić pola
**Inicjały** i **Rok urodzenia** — tak jak dziś dla `.edf`.

## Źródło danych

Blok PII w nagłówku binarnym (offset `0x00C4`, pola rozdzielone `\x00`):

| Indeks | Przykład | Użycie |
|---|---|---|
| 0 | `03.04.25` | data badania — ignorowana |
| 1 | `5` | nieznany kod — ignorowany |
| 2 | `13.39.54` | godzina — ignorowana |
| 3 | `X M 06-JUL-1996 Michal_KUCZYNSKI` | **płeć, DOB, imię_nazwisko** |

Reguły parsowania pola 3:
- Ostatni token z `_` → inicjały: pierwsza litera części przed `_` + pierwsza litera po `_`
- Token z 4-cyfrowym rokiem na końcu (np. `06-JUL-1996`) → rok urodzenia

## Zakres

- `app/domain/eeg_file.py` — parser + gałąź w `read_patient_header_info()`
- `tests/unit/test_eeg_file.py` — testy jednostkowe (syntetyczne nagłówki)
- Aktualizacja komentarza w `file_import.py`

**Poza zakresem:** BrainVision, data badania, pełne imię/nazwisko w UI.

## Progress

| # | Faza | Status |
|---|---|---|
| 1 | Parser PII DigiTrack + integracja w `read_patient_header_info` | done |
| 2 | Testy jednostkowe | done |
| 3 | Weryfikacja (`pytest`, `mypy`) | done |
