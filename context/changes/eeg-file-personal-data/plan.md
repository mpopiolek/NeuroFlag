# Dane osobowe w plikach EEG — Plan implementacji

## Overview

Uzupełnienie aplikacji o komunikację dotyczącą przetwarzania danych osobowych i zdrowotnych:
informacja w GUI o trybie offline i zakresie przetwarzania, skrócenie ekspozycji ścieżki pliku do samej nazwy,
rozszerzenie klauzuli w PDF oraz opcjonalne czyszczenie nagłówka EDF przed analizą.

## Current State Analysis

- `file_import.py:103` — pełna ścieżka pliku wyświetlana w UI (`str(path)`); ścieżka może zawierać ID pacjenta w nazwie folderu lub pliku
- `MetadataFormView`, `FileImportView`, `AppWindow` — brak jakiegokolwiek tekstu informującego o trybie offline ani o tym, co aplikacja przetwarza z pliku EEG
- `pdf_generator.py:46-52` — `DISCLAIMER_PL` zawiera wyłącznie klauzulę wyłączenia odpowiedzialności medycznej; brak informacji o offline i zakresie danych
- MNE-Python przy `read_raw_edf` / `read_raw_brainvision` ładuje do pamięci pola `subject_info`, `meas_date`, `experimenter` z nagłówka — dane te nie są używane w logice, ale są w RAM procesu podczas analizy
- Brak mechanizmu czyszczenia tych pól przed analizą

## Desired End State

Użytkownik widzi w `MetadataFormView` stały szary blok informacyjny informujący o lokalnym trybie pracy i zakresie przetwarzanych danych. Ścieżka wybranego pliku wyświetlana jest tylko jako nazwa pliku (`path.name`). Raport PDF zawiera zdanie potwierdzające lokalny, offline charakter analizy. W `FileImportView` dostępny jest checkbox pozwalający wyczyścić dane identyfikacyjne z nagłówka EDF przed analizą (domyślnie odznaczony). Po zaznaczeniu i wykonaniu analizy `raw.info` nie zawiera imienia, ID, daty nagrania.

### Key Discoveries

- `app/domain/pipeline.py:319-326` — `run()` przyjmuje `path`, `config`, `cancel_check`, `channel_overrides`, `step_delay_s`; dodanie nowego keyword-only param `anonymize_header: bool = False` nie łamie żadnego istniejącego wywołania
- `app/ui/views/analysis.py:111-117` — jedyne miejsce wywołania `pipeline.run()` z UI; tu trzeba przekazać flagę
- `app/ui/app_window.py:12-19` — `AppState` dataclass; dodanie `anonymize_header: bool = False` wystarczy do przekazania stanu między widokami
- `app/ui/views/metadata_form.py` — layout grid; blok informacyjny można dodać jako ostatni `row` przed przyciskiem „Dalej"
- `app/ui/views/file_import.py:49-55` — `_path_label` to `CTkLabel`; `str(path)` w wierszu 103 do zamiany na `path.name`
- `tests/unit/test_pipeline.py` — pattern tworzenia syntetycznego `mne.io.BaseRaw` jest gotowy do ponownego użycia

## What We're NOT Doing

- Persystencja decyzji (checkboxa anonimizacji) między sesjami aplikacji — tryb offline, bez pliku konfiguracyjnego
- Fizyczne usuwanie PII z pliku na dysku — wyłącznie czyszczenie `raw.info` w RAM
- Formal RODO compliance (DPIA, polityka prywatności producenta) — praca prawna poza repozytorium
- Tooltip z pełną ścieżką przy nazwie pliku — CTk nie ma natywnego tooltipa; basename jest wystarczający
- Zróżnicowanie informacji privacy per widok (MetadataForm + FileImport) — jeden blok w MetadataForm to wystarczający zakres MVP

## Implementation Approach

Trzy niezależne obszary implementowane sekwencyjnie od najprostszego:

1. **Tekst + basename** — czysto widokowe; zero ryzyka regresji w pipeline
2. **PDF** — izolowana zmiana stałej tekstowej
3. **Header anonymization** — jedyna zmiana z wpływem na pipeline; wymaga testu jednostkowego

## Phase 1: Informacja w GUI i nazwa pliku

### Overview

Dodanie statycznego bloku informacyjnego do `MetadataFormView` oraz zamiana pełnej ścieżki na basename w `FileImportView`.

### Changes Required

#### 1. Blok informacyjny w MetadataFormView

**File**: `app/ui/views/metadata_form.py`

**Intent**: Na dole formularza, po przycisku „Dalej →", wyświetl szary blok z jednozdaniową informacją o lokalnym trybie pracy i zakresie danych przetwarzanych przez aplikację.

**Contract**: Nowy `CTkFrame` z `fg_color` zbliżonym do tła (`#EBEBEB` / `#DCDCDC` w trybie light) zawierający `CTkLabel` z `wraplength=520` i `justify="left"`. Treść etykiety:

> „Analiza odbywa się wyłącznie na tym komputerze. Aplikacja nie wysyła żadnych danych do internetu. Do wyniku przesiewowego wykorzystywany jest sygnał EEG oraz znaczniki zadań; identyfikatory pacjenta zapisane w nagłówku pliku przez aparat EEG nie są wyświetlane ani zapisywane."

Blok umieszczony w `form.grid` jako ostatni wiersz (po `row=8` z przyciskiem), `columnspan=2`, `sticky="w"`, `pady=(16, 0)`.

#### 2. Basename ścieżki pliku

**File**: `app/ui/views/file_import.py`

**Intent**: Wyświetlaj tylko nazwę pliku, nie pełną ścieżkę, żeby ścieżka folderu (mogąca zawierać ID pacjenta) nie była widoczna w GUI.

**Contract**: Wiersz 103: `self._path_label.configure(text=str(path))` → `self._path_label.configure(text=path.name)`. Zmienna `self._selected_path` nadal przechowuje pełny `Path` do przekazania dalej.

### Success Criteria

#### Automated Verification

- `python -m pytest -q` — pełny pass, brak regresji
- `mypy app/ --strict` — 0 nowych błędów

#### Manual Verification

- Po wybraniu pliku EEG w UI etykieta pokazuje tylko nazwę pliku (bez ścieżki)
- Blok informacyjny widoczny w `MetadataFormView` — tekst nie przekracza szerokości okna
- Analiza nadal działa poprawnie (ścieżka przekazana prawidłowo)

**Implementation Note**: Po zakończeniu tej fazy i przejściu automated verification — poczekaj na potwierdzenie manualne przed przejściem do Phase 2.

---

## Phase 2: Rozszerzenie klauzuli PDF

### Overview

Dodanie zdania o lokalnym, offline charakterze analizy do istniejącego `DISCLAIMER_PL` w `pdf_generator.py`.

### Changes Required

#### 1. Rozszerzenie DISCLAIMER_PL

**File**: `app/reports/pdf_generator.py`

**Intent**: Informacja o trybie offline musi być widoczna nie tylko w aplikacji, ale też w wygenerowanym raporcie PDF — placówka może udostępniać raport rodzicom lub archiwizować.

**Contract**: Stała `DISCLAIMER_PL` (wiersze 46–52) — na początku tekstu dodaj:

> „Analiza przeprowadzona wyłącznie lokalnie; żadne dane nie zostały wysłane poza to urządzenie. Identyfikatory zapisane w nagłówku pliku EEG przez aparat nie są wyświetlane ani zapisywane w raporcie."

Połączone z istniejącym zdaniem spacją. Całość nadal wyświetlana w `style_small_italic` w sekcji „Klauzula odpowiedzialności".

#### 2. Test zawartości DISCLAIMER_PL

**File**: `tests/unit/test_pdf_generator.py`

**Intent**: Kryterium 2.2 weryfikuje konkretne słowa w `DISCLAIMER_PL` — bez backing testu jest nierunnable. Test formalnie zamienia tę weryfikację w krok automatyczny.

**Contract**: Nowa funkcja testowa:

```python
def test_disclaimer_contains_privacy_text() -> None:
    assert "lokalnie" in DISCLAIMER_PL
    assert "nagłówku" in DISCLAIMER_PL
```

### Success Criteria

#### Automated Verification

- `python -m pytest -q tests/unit/test_pdf_generator.py` — pass
- Sprawdź że `DISCLAIMER_PL` zawiera słowo „lokalnie" i „nagłówku"
- `mypy app/ --strict` — 0 nowych błędów

#### Manual Verification

- Wygeneruj raport PDF — sekcja „Klauzula odpowiedzialności" zawiera oba zdania (o offline i o nagłówku) bez wizualnych defektów (zawijanie, długość strony)

**Implementation Note**: Po automated i manual verification — przejdź do Phase 3.

---

## Phase 3: Opcjonalne czyszczenie nagłówka EDF

### Overview

Checkbox w `FileImportView` pozwala użytkownikowi wyczyścić dane identyfikacyjne z nagłówka EDF/BrainVision w RAM przed analizą. Flaga przekazywana jest przez `AppState` do `pipeline.run()`, który wywołuje `raw.anonymize()` po załadowaniu pliku.

### Changes Required

#### 1. Pole anonymize_header w AppState

**File**: `app/ui/app_window.py`

**Intent**: `AppState` jest jedynym punktem wymiany stanu między widokami — dodanie flagi tu pozwala `FileImportView` ustawić, a `AnalysisView` odczytać bez bezpośredniego powiązania widoków.

**Contract**: Do `@dataclass AppState` dodaj pole `anonymize_header: bool = False`.

#### 2. Checkbox anonimizacji w FileImportView

**File**: `app/ui/views/file_import.py`

**Intent**: Dać użytkownikowi kontrolę nad tym, czy pola identyfikacyjne z nagłówka pliku (imię, ID pacjenta, data nagrania) zostaną wyczyszczone z pamięci przed analizą — domyślnie odznaczony, żeby nie zaskakiwać.

**Contract**: Po `_path_label` (wiersz ~55) dodaj `ctk.CTkCheckBox` z tekstem `"Wyczyść dane identyfikacyjne z nagłówka pliku przed analizą"` i callback zapisujący `self._app_state.anonymize_header = bool(var.get())`. Checkbox dostępny zawsze (nie tylko po wyborze pliku). `BooleanVar` inicjalizowany z `self._app_state.anonymize_header` żeby stan przetrwał powrót „← Wróć".

> **Uwaga o persystencji:** stan checkboxa persystuje w obrębie sesji aplikacji (preferencja użytkownika na czas sesji). Reset następuje dopiero przy ponownym uruchomieniu aplikacji. Zachowanie intencjonalne — PRD zakłada jednego użytkownika na urządzenie; checkbox nie jest resetowany przez „Nowe badanie".

#### 3. Flaga anonymize_header w pipeline.run()

**File**: `app/domain/pipeline.py`

**Intent**: Pipeline jest odpowiedzialny za wczytanie pliku — to właściwe miejsce na czyszczenie, a nie w warstwie UI. Czyszczenie tuż po załadowaniu, przed jakąkolwiek dalszą obróbką sygnału.

**Contract**: Sygnatura `run()` rozszerzona o `anonymize_header: bool = False`. Po `raw = _load_raw(path)` (wiersz 330) dodaj:

```python
if anonymize_header:
    raw.anonymize(daysback=None, keep_his=False)
```

`mne.io.BaseRaw.anonymize()` zeruje `raw.info['subject_info']`, `raw.info['meas_date']`, `raw.info['experimenter']`, `raw.info['proj_name']` bez modyfikacji sygnału.

#### 4. Przekazanie flagi w AnalysisView

**File**: `app/ui/views/analysis.py`

**Intent**: `AnalysisView` wywołuje `pipeline.run()` — musi przekazać nową flagę z `AppState`.

**Contract**: W wywołaniu `pipeline.run(...)` (wiersz 111) dodaj keyword argument `anonymize_header=self._app_state.anonymize_header`.

#### 5. Test jednostkowy anonimizacji

**File**: `tests/unit/test_pipeline.py`

**Intent**: Zweryfikować, że flaga faktycznie czyści identyfikatory z `raw.info` i że domyślnie (False) ich nie rusza.

**Contract**: Dwa testy używające `_synthetic_raw_with_annotations` jako bazy (lub patch `_load_raw`). Test `test_anonymize_header_clears_subject_info`: ustaw `raw.info['subject_info'] = {'first_name': 'Jan'}` przed `run()`, sprawdź że po `run(..., anonymize_header=True)` `raw.info['subject_info']` jest `None` lub pusty. Test `test_anonymize_header_default_preserves_info`: sprawdź że domyślny wywołanie (False) nie modyfikuje `subject_info`.

Ponieważ `_load_raw` jest prywatną funkcją, użyj `unittest.mock.patch` na `app.domain.pipeline._load_raw` zwracającego przygotowany `raw` z ustawionym `subject_info`.

### Success Criteria

#### Automated Verification

- `python -m pytest -q tests/unit/test_pipeline.py` — oba nowe testy zielone
- `python -m pytest -q` — pełny suite pass
- `mypy app/ --strict` — 0 nowych błędów

#### Manual Verification

- Checkbox widoczny w `FileImportView`, domyślnie odznaczony
- Po zaznaczeniu i kliknięciu „Analizuj" — analiza kończy się sukcesem (wynik RAG bez regresji)
- Powrót „← Wróć" i powrót do importu — checkbox pamięta stan (BooleanVar z AppState)

**Implementation Note**: Po automated i manual verification — zmiana `eeg-file-personal-data` jest gotowa do archiwizacji.

---

## Testing Strategy

### Unit Tests

- `test_pipeline.py` — dwa nowe testy (`anonymize_header=True` czyści info, `False` nie rusza)
- `test_pdf_generator.py` — weryfikacja że nowy tekst w `DISCLAIMER_PL` pojawia się w wygenerowanym PDF

### Manual Testing Steps

1. Uruchom aplikację, wypełnij MetadataForm — sprawdź widoczność bloku informacyjnego
2. Przejdź do FileImportView — sprawdź że ścieżka wybranego pliku to tylko basename
3. Zaznacz checkbox anonimizacji, wykonaj analizę — wynik musi być poprawny
4. Zapisz PDF — sprawdź sekcję „Klauzula odpowiedzialności"

## Open Risks & Assumptions

- `mne.io.BaseRaw.anonymize()` jest dostępne w MNE 1.8.0 (wersja przypięta w `pyproject.toml`) — do weryfikacji przy implementacji
- Czyszczenie `meas_date` przez `anonymize()` może wpłynąć na metadane PDF (pole `date` dokumentu) jeśli kiedykolwiek byłoby pobierane z `raw.info` — aktualnie PDF używa `result.analyzed_at` (datetime analizy), nie daty pliku
- Anonimizacja nagłówka BrainVision (`.vhdr`) przez MNE — zachowanie `anonymize()` dla tego formatu powinno być potwierdzone testem

## References

- Research: `context/changes/eeg-file-personal-data/research.md`
- Kod pipeline: `app/domain/pipeline.py:319-357`
- Kod UI import: `app/ui/views/file_import.py:85-113`
- AppState: `app/ui/app_window.py:12-24`
- PDF generator: `app/reports/pdf_generator.py:46-52`

---

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Informacja w GUI i nazwa pliku

#### Automated

- [x] 1.1 `python -m pytest -q` — pełny pass, brak regresji — 0ab328e
- [x] 1.2 `mypy app/ --strict` — 0 nowych błędów — 0ab328e

#### Manual

- [ ] 1.3 Etykieta ścieżki pliku pokazuje tylko basename (bez ścieżki folderu)
- [ ] 1.4 Blok informacyjny widoczny w MetadataFormView, tekst zawijany poprawnie

### Phase 2: Rozszerzenie klauzuli PDF

#### Automated

- [x] 2.1 `python -m pytest -q tests/unit/test_pdf_generator.py` — pass
- [x] 2.2 DISCLAIMER_PL zawiera słowo „lokalnie" i „nagłówku"
- [x] 2.3 `mypy app/ --strict` — 0 nowych błędów

#### Manual

- [ ] 2.4 Wygenerowany PDF zawiera informację o offline w sekcji klauzuli

### Phase 3: Opcjonalne czyszczenie nagłówka EDF

#### Automated

- [ ] 3.1 `python -m pytest -q tests/unit/test_pipeline.py` — oba nowe testy zielone
- [ ] 3.2 `python -m pytest -q` — pełny suite pass
- [ ] 3.3 `mypy app/ --strict` — 0 nowych błędów

#### Manual

- [ ] 3.4 Checkbox widoczny w FileImportView, domyślnie odznaczony
- [ ] 3.5 Analiza z zaznaczonym checkboxem daje poprawny wynik RAG
- [ ] 3.6 Stan checkboxa przetrwa cykl „← Wróć" → powrót do importu
