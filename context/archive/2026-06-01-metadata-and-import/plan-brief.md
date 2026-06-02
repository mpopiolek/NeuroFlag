# S-01: Formularz metryki dziecka + import pliku EEG — Plan Brief

> Full plan: `context/changes/metadata-and-import/plan.md`

## What & Why

S-01 buduje pierwszą warstwę interfejsu użytkownika NeuroFlag: formularz metryki dziecka
i widok importu pliku EEG. Bez tego nie ma wejścia do pipeline'u — pedagog nie może
rozpocząć analizy. S-01 zamyka lukę między gotowym fundamentem domenowym (F-01) a przetwarzaniem
sygnału (S-02).

## Starting Point

F-01 dostarczył typy domenowe (`PatientMetadata`, `ExclusionDiagnosis`, `Sex`, `NormsConfig`),
loader norm i pusty stub CTk (800×600, brak widoków). Nie istnieje żaden widok UI,
żadna nawigacja, żaden moduł walidacji pliku EEG.

## Desired End State

Pedagog uruchamia aplikację, widzi formularz z polami wiek/płeć/diagnozy, wypełnia go
i przechodzi do widoku importu. Po wyborze i walidacji pliku .edf lub .vhdr przycisk
'Analizuj' staje się aktywny — `AppState` zawiera `PatientMetadata` + ścieżkę pliku,
gotowe do przekazania do S-02.

## Key Decisions Made

| Decyzja | Wybór | Dlaczego | Źródło |
|---|---|---|---|
| Nawigacja między widokami | destroy + create on demand | Czysty stan przy każdym przejściu; brak state leak | Plan |
| Kontener stanu aplikacji | `@dataclass AppState` (mutowalny) | Typowany, zgodny z konwencją dataclass; widoki zapisują do niego wyniki | Plan |
| Struktura widoków | Dwa oddzielne (MetadataFormView → FileImportView) | Zgodne z AGENTS.md; każdy widok ma jedną odpowiedzialność | Plan |
| Input wieku | CTkOptionMenu (lista 6–10) | Zero walidacji — błędna wartość nieosiągalna | Plan |
| Blokada przy wykluczeniu | Etykieta ostrzegawcza + disabled 'Dalej →' | Natychmiastowy feedback; brak dodatkowych okien | Plan |
| Walidacja pliku EEG | MNE header load (preload=False) w wątku tła | Wczesna detekcja uszkodzonego pliku; nie zamraża UI | Plan |
| BrainVision multi-file | Użytkownik wybiera tylko .vhdr; app szuka .vmrk/.eeg | Jeden klik; spójne z API MNE | Plan |
| Drag & drop | Pominięty w S-01 | Bonus wg PRD; tkinterdnd2 ryzykuje regresje PyInstaller | Plan |
| Testy | Logika domenowa + walidator pliku (mock MNE) | Pokrywa dwa kluczowe punkty awarii bez potrzeby display | Plan |

## Scope

**In scope:**
- `app/ui/app_window.py` — `AppState` + `AppWindow` z nawigacją destroy+create
- `app/ui/views/metadata_form.py` — formularz metryki z blokadą wykluczeń
- `app/domain/eeg_file.py` — domenowy walidator pliku EEG (testowalny bez CTk)
- `app/ui/views/file_import.py` — widok importu z walidacją w wątku tła
- `tests/unit/test_eeg_file.py` — testy walidatora (mock MNE)
- Uzupełnienie `tests/unit/test_types.py` — scenariusze `is_excluded()`
- Refaktor `app/main.py` — `AppWindow` zamiast anonimowego `ctk.CTk()`

**Out of scope:**
- Analiza sygnału EEG (S-02), siatka wyników, raport PDF (S-03)
- Drag & drop (backlog)
- Podmiana norms.json przez UI (S-04)
- Walidacja zawartości EEG (czy kanały C3/O1 istnieją — to pipeline S-02)
- Hasło startowe (FR-009, nice-to-have)
- Persystencja stanu między sesjami aplikacji

## Architecture / Approach

```
app/main.py
  └─ AppWindow (CTk)          ← nowe centrum aplikacji
       ├─ AppState             ← typowany stan (metadata, eeg_path)
       ├─ MetadataFormView     ← Phase 2: formularz, → AppState.metadata
       │    [Dalej →]
       └─ FileImportView       ← Phase 3: import + walidacja, → AppState.eeg_path
            [Analizuj]         ← stub; pełna nawigacja w S-02
```

`eeg_file.py` (domena) ←używany przez→ `file_import.py` (UI) ←testowany przez→ `test_eeg_file.py`

## Phases at a Glance

| Phase | Co dostarcza | Główne ryzyko |
|---|---|---|
| 1. AppWindow shell | Działające okno CTk z typowanym AppState i nawigacją | Refaktor main.py może zepsuć `--smoke-test` |
| 2. MetadataFormView | Formularz z blokadą wykluczeń, budowanie PatientMetadata | Poprawna obsługa trace_add na BooleanVar |
| 3. EEG validator + FileImportView | Dialog pliku, walidacja w wątku tła, status UI | CTk.after() — jedyna bezpieczna metoda aktualizacji UI z wątku |
| 4. Testy jednostkowe | Pokrycie walidatora + is_excluded(); mypy clean | Poprawne mockowanie mne.io bez pełnej instalacji MNE w CI |

**Prerequisites:** F-01 ukończony i zarchiwizowany (status: implemented ✅)
**Estimated effort:** ~2–3 sesje implementacyjne; 4 fazy, liniowe zależności

## Open Risks & Assumptions

- CTk 5.2.2 nie posiada natywnego Spinbox — `CTkOptionMenu` jest jedyną wbudowaną alternatywą
  dla ograniczonego zakresu wartości; jeśli okaże się niewystarczający, można rozważyć
  `tkinter.Spinbox` osadzony w CTkFrame (bez zmiany planowanego API)
- MNE `read_raw_brainvision(preload=False)` wczytuje tylko nagłówek — zakładamy, że to wystarczy
  do wykrycia uszkodzonego pliku; głęboka walidacja struktury kanałów należy do S-02
- Threading w CTk: `self.after(0, callback)` jest standardowym idiomem; nie testujemy
  race condition w S-01 (file dialog jest blokujący, więc wątek walidacji nie może zacząć
  działać zanim plik nie zostanie wybrany)

## Success Criteria (Summary)

- `pytest -q` zielony, `mypy app/ --strict` bez błędów po każdej fazie
- Pedagog może wypełnić formularz, wczytać plik .edf i zobaczyć aktywny przycisk 'Analizuj'
  — bez konfiguracji sieciowej, bez crash'u aplikacji
- Zaznaczenie wykluczenia klinicznego skutecznie blokuje przejście do importu pliku
