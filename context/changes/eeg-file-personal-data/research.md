---
date: 2026-06-12T12:00:00+02:00
researcher: Cursor Agent
git_commit: 821258850343c6dad1298444fa7624ea80b30fa8
branch: coursor/dev-env-setup-2f65
repository: NeuroFlag
topic: "Czy pliki EEG (.edf / BrainVision) zawierają dane osobowe i jakie wymagania informacyjne wynikają dla aplikacji?"
tags: [research, codebase, privacy, RODO, edf, brainvision, personal-data]
status: complete
last_updated: 2026-06-12
last_updated_by: Cursor Agent
last_updated_note: "Dodano checklistę RODO przed release oraz follow-up o biofeedback w kontekście plików EEG"
---

# Research: Dane osobowe w plikach EEG (.edf / BrainVision)

**Date**: 2026-06-12  
**Researcher**: Cursor Agent  
**Git Commit**: `821258850343c6dad1298444fa7624ea80b30fa8`  
**Branch**: `coursor/dev-env-setup-2f65`  
**Repository**: NeuroFlag

## Research Question

Czy przetwarzane przez nas rozszerzenia plików zawierają dane osobowe? Jakie dane mogą zawierać? Czy wymaga to od nas jakiejś informacji, że nie są one przez aplikację dotykane?

## Summary

**Tak — pliki `.edf` i BrainVision (`.vhdr` + `.vmrk` + `.eeg`) mogą zawierać dane osobowe i dane wrażliwe (zdrowotne).** To wynika ze specyfikacji formatów i praktyki eksportu z aparatów EEG, a nie z decyzji NeuroFlag.

NeuroFlag **nie wyświetla ani nie zapisuje** identyfikatorów z nagłówka pliku (imię, PESEL, data urodzenia itd.), ale **MNE-Python wczytuje nagłówek do pamięci procesu** przy każdym odczycie pliku. Aplikacja **aktywnie przetwarza** sygnał EEG (dane biometryczne/zdrowotne) oraz tekst adnotacji/znaczników (np. OO/OZ/ZP). Dodatkowo użytkownik **ręcznie wprowadza** metrykę dziecka (wiek, płeć, diagnozy wykluczające), a w UI widoczna jest **pełna ścieżka pliku** — która często zawiera ID sesji lub pacjenta w nazwie.

**Czy trzeba informować użytkownika?** Z perspektywy prawnej (RODO) placówka jest administratorem danych; aplikacja powinna mieć **jasną informację o przetwarzaniu lokalnym** (offline, brak transmisji) oraz **transparentność co do zakresu przetwarzania** — zwłaszcza że nagłówki plików *mogą* zawierać PII, nawet jeśli aplikacja ich nie używa w logice biznesowej. W dokumentacji projektu (PRD, README) taki komunikat już istnieje częściowo; **w GUI aplikacji brakuje klauzuli prywatności / informacji o przetwarzaniu**. Formalna ocena RODO (podstawa prawna, Art. 9, DPIA, zgoda rodzica) **nie jest jeszcze udokumentowana** w repozytorium.

## Detailed Findings

### 1. Obsługiwane rozszerzenia plików

NeuroFlag akceptuje:

| Rozszerzenie | Opis | Pliki towarzyszące |
|---|---|---|
| `.edf` | European Data Format (EDF/EDF+) | samodzielny plik |
| `.vhdr` | BrainVision header | wymaga `.vmrk` + `.eeg` obok |

Źródło: `app/domain/eeg_file.py:6-7`, `context/foundation/prd.md:121`.

### 2. Jakie dane mogą zawierać pliki EEG

#### 2.1 Format EDF (`.edf`)

Nagłówek 256 bajtów (specyfikacja EDF/EDF+) zawiera m.in.:

| Pole | Rozmiar | Przykładowa treść (potencjalne dane osobowe) |
|---|---|---|
| Local patient identification | 80 znaków | ID pacjenta, imię, nazwisko, płeć, data urodzenia (często w jednym ciągu) |
| Local recording identification | 80 znaków | technik, szpital/placówka, notatki sesji |
| Start date / time | 8+8 znaków | data i godzina nagrania |
| Reserved (EDF+) | 44 znaki | dodatkowe metadane administracyjne |

EDF+ może dodatkowo kodować: kod pacjenta, płeć, datę urodzenia, imię, dane technika, sprzęt.

**Adnotacje** (kanał TAL): dowolny tekst opisowy — nazwy zadań (OO/OZ/ZP), ale też notatki kliniczne.

**Dane sygnału**: ciągły zapis aktywności mózgowej — **dane biometryczne / zdrowotne** w rozumieniu RODO (Art. 4(15), Art. 9).

#### 2.2 Format BrainVision (`.vhdr` + `.vmrk` + `.eeg`)

| Plik | Potencjalne dane osobowe |
|---|---|
| `.vhdr` | pole `Comment=` (notatki), opcjonalnie `PatientName`, `PatientID`, `RecordingDate`, `Investigator` w sekcji `[Common Infos]` (zależy od eksportera) |
| `.vmrk` | opisy markerów (`Description`) — tekst zadań lub notatki kliniczne |
| `.eeg` | wyłącznie binarny sygnał — brak nagłówka PII |

#### 2.3 Klasyfikacja wg RODO (orientacyjna, nie porada prawna)

| Kategoria | Przykłady w pliku EEG | Uwagi |
|---|---|---|
| Dane osobowe (Art. 4) | imię, ID pacjenta, data urodzenia, data nagrania, nazwa placówki w nagłówku | Mogą być w nagłówku EDF/BrainVision |
| Dane wrażliwe — zdrowotne (Art. 9) | sygnał EEG, diagnozy w adnotacjach, informacje kliniczne w nagłówku | Sygnał jest zawsze przetwarzany przez pipeline |
| Identyfikatory pośrednie | ID w nazwie pliku (`260116_000791_EEGok.edf`) | Widoczne w UI, nie w nagłówku |

### 3. Co NeuroFlag faktycznie „dotyka”

#### 3.1 Wczytywane z pliku EEG (przez MNE-Python)

```251:264:app/domain/pipeline.py
def _load_raw(path: Path) -> mne.io.BaseRaw:
    ...
        if suffix == ".edf":
            return mne.io.read_raw_edf(path, preload=True, verbose=False)
        if suffix == ".vhdr":
            return mne.io.read_raw_brainvision(path, preload=True, verbose=False)
```

MNE parsuje **cały nagłówek** do `raw.info`, w tym pola takie jak `subject_info`, `meas_date`, `experimenter`, `description` — **nawet gdy NeuroFlag ich nie używa**.

#### 3.2 Pola używane przez logikę aplikacji

| Dane z pliku | Gdzie używane | Cel |
|---|---|---|
| `raw.ch_names` | `eeg_file.py:54`, `pipeline.py:337` | walidacja / mapowanie kanałów C3, O1 |
| `raw.annotations` (description, onset, duration) | `pipeline.py:140-200` | wykrywanie segmentów OO/OZ/ZP |
| `raw.times[-1]` | `pipeline.py:189-216` | sprawdzenie minimalnej długości nagrania |
| Sygnał EEG (`get_data`, filtry) | `pipeline.py:291-315` | obliczenie amplitud µV (niewidocznych w UI) |

#### 3.3 Pola nagłówka **NIE** używane przez kod aplikacji

- `subject_info` (imię, nazwisko, ID, data urodzenia, płeć z pliku)
- `meas_date` (data nagrania)
- `experimenter`, `description`, `proj_name`

**Wiek i płeć do analizy pochodzą z formularza**, nie z nagłówka pliku:

```31:35:app/domain/types.py
class PatientMetadata:
    age: int
    sex: Sex
    exclusions: frozenset[ExclusionDiagnosis] = field(default_factory=frozenset)
```

#### 3.4 Dane wprowadzane ręcznie (poza plikiem EEG)

Formularz metryki (`metadata_form.py`): wiek 6–10, płeć (Z/M), trzy diagnozy wykluczające (uraz mózgu, niepełnosprawność intelektualna, padaczka). Przechowywane wyłącznie w RAM (`AppState.metadata`).

#### 3.5 Ekspozycja pośrednia

| Ryzyko | Lokalizacja | Opis |
|---|---|---|
| Pełna ścieżka pliku w UI | `file_import.py:103` | Nazwa pliku może zawierać ID pacjenta |
| Adnotacje w dev probe | `tests/fixtures/probe_pipeline.py:36-57` | Wypisuje opisy adnotacji na stdout (nie GUI) |
| Błędy kanałów | `channels.py:40-45` | Listuje nazwy kanałów z pliku |

#### 3.6 Persystencja i transmisja

| Aspekt | Stan |
|---|---|
| Zapis na dysk przez aplikację | Brak (poza planowanym PDF w S-03) |
| Baza danych | Brak |
| Połączenia sieciowe | Brak w kodzie `app/` |
| Telemetria / logi | Brak modułu logowania w aplikacji |
| Sesja | RAM do momentu „Nowe badanie” (`results_grid.py:146-149`) |

### 4. Czy wymaga to informacji dla użytkownika?

#### 4.1 Stan obecny w projekcie

**W dokumentacji (poza aplikacją):**

- README: „Działa w trybie w pełni offline — żadne dane nie opuszczają urządzenia” + disclaimer medyczny
- PRD guardrails: dane dziecka nie opuszczają urządzenia; brak połączeń sieciowych
- `distribution.md`: smoke-test weryfikacji braku ruchu sieciowego

**W GUI aplikacji:**

- Brak klauzuli RODO / informacji o przetwarzaniu
- Brak komunikatu „nagłówki pliku mogą zawierać dane identyfikujące — aplikacja ich nie wyświetla”
- Brak klauzuli odpowiedzialności (planowana w PDF, S-03)

#### 4.2 Rekomendacja merytoryczna (do decyzji produktowej / prawnej)

| Obszar | Rekomendacja |
|---|---|
| **Informacja o trybie offline** | Tak — potwierdza główną wartość produktu i wymóg RODO z PRD. Może być w instrukcji PDF, ekranie startowym lub stopce. |
| **Zakres przetwarzania pliku** | Warto jasno napisać: aplikacja analizuje **sygnał EEG** i **znaczniki zadań**; **nie wyświetla** danych identyfikacyjnych z nagłówka pliku (jeśli eksporter je umieścił). |
| **Metryka dziecka** | Formularz zbiera wiek/płeć/diagnozy — użytkownik powinien wiedzieć, że trafiają do raportu PDF (gdy S-03) i nie są wysyłane poza urządzenie. |
| **Odpowiedzialność placówki** | PRD przypisuje ochronę fizyczną urządzenia placówce; instrukcja powinna wspomnieć o bezpiecznym przechowywaniu plików źródłowych i raportów PDF. |
| **Formalna zgodność RODO** | Wymaga pracy prawnej poza repozytorium: podstawa prawna (Art. 6/9), ewentualna DPIA, rola administratora (placówka) vs. narzędzie (NeuroFlag jako processor lub narzędzie w rękach administratora), zgoda rodzica/opiekuna. **Nie zastępuje to porady prawnej.** |

#### 4.3 Czy trzeba mówić „aplikacja nie dotyka danych osobowych w pliku”?

**Nie w takiej absolutnej formie** — byłoby to **nieprawdziwe**:

1. Aplikacja **czyta cały plik** (nagłówek trafia do pamięci MNE).
2. Aplikacja **przetwarza sygnał EEG** — to dane zdrowotne/biometryczne.
3. Aplikacja **czyta tekst adnotacji** (segmentacja zadań).

**Prawidłowy komunikat** powinien brzmieć w stylu:

> „Analiza odbywa się wyłącznie na Twoim komputerze. Aplikacja nie wysyła danych do internetu. Do wyniku przesiewowego wykorzystywany jest sygnał EEG oraz znaczniki zadań. Identyfikatory pacjenta zapisane w nagłówku pliku przez aparat EEG nie są wyświetlane ani zapisywane w raporcie.”

## Code References

- `app/domain/eeg_file.py:6-7` — obsługiwane rozszerzenia `.edf`, `.vhdr`
- `app/domain/eeg_file.py:39-56` — odczyt listy kanałów z nagłówka
- `app/domain/pipeline.py:251-264` — pełne wczytanie pliku (`preload=True`)
- `app/domain/pipeline.py:140-200` — wykorzystanie adnotacji OO/OZ/ZP
- `app/domain/types.py:31-35` — `PatientMetadata` (wiek, płeć, wykluczenia)
- `app/ui/views/metadata_form.py:127-137` — zapis metryki do `AppState`
- `app/ui/views/file_import.py:103` — wyświetlenie pełnej ścieżki pliku
- `app/ui/app_window.py:12-24` — sesyjny stan w RAM, bez persystencji
- `app/ui/views/results_grid.py:146-149` — reset sesji („Nowe badanie”)
- `tests/fixtures/generate_test_edfs.py:49-50` — syntetyczne pliki testowe bez PII w nagłówku

## Architecture Insights

- **Separacja źródeł danych**: metryka dziecka (formularz) vs. sygnał (plik) vs. normy (`norms.json`) — tylko sygnał i adnotacje pochodzą z pliku EEG.
- **MNE jako black box nagłówka**: każde `read_raw_*` ładuje metadane pacjenta do `raw.info`, ale pipeline ich nie konsumuje — to „cień PII” w pamięci procesu.
- **Minimalizacja ekspozycji w UI**: surowe µV ukryte (tylko kolory RAG) — zgodnie z regułą domenową z AGENTS.md.
- **Brak warstwy compliance**: architektura offline spełnia wymóg „dane nie opuszczają urządzenia”, ale nie zastępuje dokumentacji RODO dla operatora (placówki).

## Historical Context (from prior changes)

- `context/foundation/prd.md:36,72,123` — RODO i prywatność jako powód architektury desktop/offline
- `context/foundation/prd.md:190,193` — chmura i statystyki badawcze wykluczone z MVP (wymóg audytu RODO)
- `context/foundation/roadmap.md:145-149` — parked: centralna baza pacjentów, statystyki neuroatypowości
- `context/archive/2026-06-01-metadata-and-import/plan.md` — AppState tylko w pamięci; walidacja nagłówka MNE bez ekstrakcji PII
- `context/changes/eeg-pipeline-and-results/plan-brief.md` — wsparcie bez wycieku danych wrażliwych (brak µV w UI błędów)
- `idea-notes.md:21` — eksport statystyk e-mailem odłożony do audytu RODO

## Related Research

- `context/changes/eeg-pipeline-and-results/research.md` — pipeline EEG, segmentacja, kanały

## Open Questions

1. **Klasyfikacja prawna**: czy NeuroFlag jest narzędziem używanym przez administratora (placówkę), czy wymaga osobnej polityki prywatności producenta?
2. **Nagłówki EDF z PII**: czy przed analizą należy oferować anonimizację nagłówka (strip `subject_info`) — obecnie nie zaimplementowane?
3. **Wyświetlanie ścieżki**: czy UI powinno pokazywać tylko `basename` zamiast pełnej ścieżki?
4. **PDF (S-03)**: jakie dokładnie pola metryki trafią do raportu i czy wymaga to klauzuli informacyjnej dla rodzica?
5. **Diagnozy w formularzu**: czy lista wykluczeń + przyszłe rozszerzenia (ASD/ADHD z PRD) kwalifikują się jako Art. 9 — brak analizy w repo.
6. **Retencja**: brak polityki usuwania danych sesji / plików PDF na współdzielonych PC w placówce.

---

## Follow-up Research 2026-06-12

### Pytanie użytkownika

Checklist przed release (RODO/prywatność) oraz wyjaśnienie słowa „biofeedback” w rozmowie z ekspertem — czy warto dopytać?

### Biofeedback — czym to może być w tym kontekście

W dokumentacji NeuroFlag („EEG/Biofeedback”) **biofeedback nie jest osobnym formatem pliku** — chodzi o **kategorię sprzętu/oprogramowania**, z którego placówki eksportują te same pliki `.edf` / BrainVision.

| Pojęcie | Co to jest | Związek z NeuroFlag |
|---|---|---|
| **EEG (elektroencefalografia)** | Pomiar aktywności mózgu elektrodami; aparat + oprogramowanie zapisuje sygnał | NeuroFlag analizuje taki zapis |
| **Biofeedback / neurofeedback** | Metoda treningowa: uczeń widzi na ekranie „feedback” (np. gra, dźwięk) zależny od fal mózgu i uczy się je modulować | To **procedura terapeutyczna**, nie format danych |
| **Urządzenie „EEG/Biofeedback”** | Często ten sam amplifier EEG + software do neurofeedbacku (np. w szkołach, poradniach) | Placówka ma taki sprzęt → eksportuje `.edf` → NeuroFlag ma to **przeczytać** |

**Typowe znaczenia słowa „biofeedback” u eksperta:**

1. **Sprzęt w placówce** — „mamy aparat do biofeedbacku” = amplifier EEG używany też (lub głównie) do treningu neurofeedback, nie do klinicznego EEG szpitalnego.
2. **Protokół nagrania** — sesja neurofeedback (np. 20× trening po 30 min) vs. **protokół przesiewowy** NeuroFlag (OO → OZ → ZP, min. 8 min). To **różne procedury** na tym samym sprzęcie.
3. **Oprogramowanie producenta** — np. BioGraph, Thought Technology, Mitsar, BrainAvatar itd. — każde inaczej nazywa znaczniki, kanały, eksport.
4. **Szersze biofeedback** — czasem obejmuje też HRV, EMG, temperaturę; jeśli ekspert mówi ogólnie, warto doprecyzować czy chodzi **wyłącznie o EEG**.

**Dla NeuroFlag kluczowe nie jest słowo „biofeedback”, lecz:**

- czy nagranie ma protokół **OO/OZ/ZP** (lub ≥8 min bez znaczników → fallback);
- czy są kanały **C3 i O1** (system 10–20);
- w jakim **formacie** wychodzi eksport (`.edf` vs BrainVision);
- jak **nazywane są znaczniki** w software aparatu (lista w `docs/EEG-segmentacja.md`).

W PRD sukces kryterium brz brzmi: *„pliki z minimum 3 różnych, popularnych aparatów EEG/Biofeedback dostępnych na rynku polskim”* — czyli produkt **zakłada** różnorodność producentów sprzętu szkolnego/neurofeedbackowego, nie jeden kliniczny EEG.

### Czy warto dopytać eksperta?

**Tak — warto**, bo „biofeedback” samo w sobie nie mówi, czy chodzi o sprzęt, protokół terapeutyczny czy konkretną markę. Bez doprecyzowania ryzykujecie źle zinterpretowane wymagania (np. wsparcie sesji treningowych zamiast nagrań przesiewowych).

**Pytania do eksperta (propozycja):**

| # | Pytanie | Po co |
|---|---|---|
| 1 | **Jakie konkretnie aparaty / programy** mają placówki docelowe? (marka, model, wersja software) | Lista urządzeń do testów manualnych (wymóg PRD: min. 3) |
| 2 | Czy „biofeedback” u Was oznacza **ten sam sprzęt co EEG**, czy osobny zestaw? | Czy NeuroFlag ma obsługiwać tylko EEG, czy też inne modality |
| 3 | Czy badanie przesiewowe NeuroFlag to **osobny protokół nagrania**, czy plik z **zwykłej sesji neurofeedback**? | Sesje treningowe często nie mają OO/OZ/ZP → fallback lub błąd |
| 4 | **Jak operator zapisuje znaczniki** OO, OZ, ZP w danym programie? (dokładne etykiety z ekranu) | Rozszerzenie `_TASK_KEYWORDS` w pipeline |
| 5 | W jakim **formacie eksportujecie** pliki? (`.edf`, BrainVision, coś innego?) | Potwierdzenie zakresu MVP |
| 6 | Czy eksport zawiera **nazwę/ID dziecka w nagłówku** lub w nazwie pliku? | Prywatność + ewentualna anonimizacja przed analizą |
| 7 | Czy w szkołach nagrywacie **zawsze C3 i O1**, czy inny układ elektrod? | Mapowanie kanałów / picker |
| 8 | Czy pliki z biofeedbacku mają **inną częstotliwość próbkowania / filtry** niż kliniczne EEG? | Wpływ na pipeline (filtrowanie 50 Hz itd.) |

**Czego nie trzeba pytać:** czy biofeedback to „dane osobowe” — to metoda/sprzęt; dane osobowe dotyczą **zawartości pliku i metryki dziecka**, nie nazwy metody.

### Checklist przed release — prywatność / RODO (orientacyjna)

> Nie zastępuje porady prawnej. Do wypełnienia przez produkt + placówkę / prawnika.

#### A. Architektura aplikacji (stan NeuroFlag)

- [ ] Potwierdzone: **brak połączeń sieciowych** w runtime (smoke-test z `distribution.md`)
- [ ] Potwierdzone: **brak telemetrii, crash reportingu, logów z danymi pacjenta**
- [ ] Potwierdzone: **brak bazy danych / automatycznego zapisu sesji** (poza PDF wybranym przez użytkownika)
- [ ] Surowe µV **niewidoczne** w UI i raporcie PDF
- [ ] Komunikaty błędów **nie ujawniają** wartości sygnału ani pełnej zawartości nagłówka

#### B. Informacja dla użytkownika (instrukcja / UI)

- [ ] Tekst: analiza **wyłącznie lokalna**, dane **nie są wysyłane do internetu**
- [ ] Tekst: do wyniku wykorzystywany jest **sygnał EEG i znaczniki zadań**
- [ ] Tekst: identyfikatory z **nagłówka pliku** (jeśli aparat je zapisał) **nie są wyświetlane ani zapisywane w raporcie**
- [ ] Disclaimer: wynik to **narzędzie przesiewowe**, nie diagnoza medyczna (README + PDF)
- [ ] Klauzula **ograniczenia odpowiedzialności** w PDF (S-03)
- [ ] Informacja: **placówka** odpowiada za fizyczny dostęp do komputera i plików źródłowych

#### C. Pliki EEG od aparatów / biofeedbacku

- [ ] Zmapowane **min. 3 urządzenia** docelowe (PRD) — eksport testowy w repozytorium QA
- [ ] Wiadomo, czy eksporty zawierają **PII w nagłówku** — procedura dla operatora (anonimizacja przed analizą?)
- [ ] UI: rozważyć pokazywanie **samej nazwy pliku** zamiast pełnej ścieżki
- [ ] Instrukcja: jak **bezpiecznie przechowywać** pliki `.edf` i raporty PDF na PC placówki

#### D. Metryka dziecka (formularz + PDF)

- [ ] Udokumentowane: jakie pola trafiają do **raportu PDF** (wiek, płeć — bez imienia?)
- [ ] Decyzja prawna: czy **diagnozy wykluczające** to dane wrażliwe Art. 9 — podstawa prawna u administratora (placówki)
- [ ] Procedura: **zgoda rodzica/opiekuna** na badanie przesiewowe (poza aplikacją — placówka)

#### E. Organizacyjne (poza kodem)

- [ ] Rola: **administrator danych = placówka**; rola producenta NeuroFlag (narzędzie vs processor) — ustalona
- [ ] Ewentualna **DPIA** dla badania przesiewowego EEG u dzieci 6–10 lat
- [ ] Polityka **retencji i usuwania** plików źródłowych i PDF
- [ ] Szkolenie operatora: nie analizować plików z **identyfikatorami w nazwie** na współdzielonym ekranie

#### F. Odłożone (nie MVP, ale z RODO w PRD)

- [ ] Statystyki badawcze / eksport e-mail — **wymaga audytu RODO** (nie implementować bez)
- [ ] Centralna baza pacjentów / chmura — **wykluczone** z MVP
