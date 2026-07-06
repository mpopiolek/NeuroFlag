---
project: "NeuroFlag"
version: 1
status: draft
created: 2026-05-30
updated: 2026-06-26
prd_version: 1
main_goal: low-complexity
top_blocker: decisions
---

# Roadmap: NeuroFlag

> Derived from `context/foundation/prd.md` (v1) + auto-researched codebase baseline.
> Edit-in-place; archive when superseded.
> Slices below are listed in dependency order. The "At a glance" table is the index.

## Vision recap

NeuroFlag to aplikacja desktopowa dla Windows, która pozwala pedagogom szkolnym i specjalnym przeprowadzać przesiewową analizę sygnału EEG dziecka (wiek 6–10 lat) bez wysyłania danych do sieci i bez angażowania specjalistów klinicznych na etapie wstępnym. Pedagog wczytuje wyeksportowany plik `.edf` lub `.vhdr`, wypełnia metrykę dziecka i w kilka minut otrzymuje wynik w jednej z trzech kategorii decyzyjnych — Wskazanie do dalszej diagnozy / Uważna obserwacja / Brak wskazań — wizualizowany jako siatka 10 kolorowych komórek. Rdzeń produktu to empiryczna baza norm wyprowadzona z badania 200 dzieci (6–10 lat), która pozwala porównać sygnał konkretnego dziecka z grupą referencyjną bez udziału lekarza.

## North star

**S-03: pedagog może wygenerować i zapisać raport PDF z pełnym wynikiem badania** — S-03 zamyka łańcuch S-01 → S-02 → S-03, czyli pełne US-01 end-to-end; dostarczenie S-03 oznacza, że hipoteza produktu (przekonanie, że pedagog bez wiedzy klinicznej może — wyłącznie na podstawie pliku EEG i bazy norm — uzyskać wiarygodną przesiewową ocenę dziecka) jest weryfikowalna przez prawdziwego użytkownika lub eksperta domenowego.

> Gwiazda przewodnia — pierwszy łańcuch roadmapy, którego pomyślne dostarczenie udowadnia, że rdzeń hipotezy produktu działa — umieszczony tak wcześnie, jak pozwalają zależności, bo wszystko inne ma znaczenie tylko wtedy, gdy to działa. Tutaj oznacza to: cały flow US-01 jest ukończony i można go pokazać pedagogowi w terenie.

## At a glance

| ID   | Change ID                  | Outcome (użytkownik może …)                                                                          | Prerequisites | PRD refs                      | Status   |
|------|----------------------------|------------------------------------------------------------------------------------------------------|---------------|-------------------------------|----------|
| F-01 | project-foundation         | (foundation) środowisko gotowe: pyproject.toml z przypiętymi zależnościami, norms.json z 10 normami, typy domenowe w app/domain/types.py | —             | FR-008                        | ready    |
| S-01 | metadata-and-import        | wypełnić metrykę dziecka (z wykluczeniami klinicznymi) i wczytać plik .edf lub .vhdr gotowy do analizy | F-01          | FR-001, FR-010, US-01         | done     |
| S-02 | eeg-pipeline-and-results   | uruchomić analizę i zobaczyć siatkę 10 kolorowych komórek z kategorią wynikową                       | S-01          | FR-002, FR-003, FR-004, US-01 | done     |
| S-03 | pdf-report-and-save        | wygenerować raport PDF i zapisać go na dysk lokalny                                                  | S-02          | FR-005, FR-006, US-01         | done     |
| S-04 | norms-replacement          | zastąpić plik norms.json własnym plikiem i mieć pewność, że aplikacja wczytuje nowe normy i waliduje schemat | F-01          | FR-008                        | done |

## Streams

Navigation aid — groups items that share a Prerequisites chain. Canonical ordering still lives in the dependency graph below; this table is the proposed reading order across parallel tracks.

| Stream | Theme                   | Chain                               | Note                                                                                          |
|--------|-------------------------|-------------------------------------|-----------------------------------------------------------------------------------------------|
| A      | Główny flow badania     | `F-01` → `S-01` → `S-02` → `S-03`  | Łańcuch krytyczny ku gwieździe przewodniej; cel `low-complexity` — zero opcjonalnych elementów w tym torze. |
| B      | Konfiguracja norm       | `S-04`                              | Rozgałęzia się od F-01 (Stream A); może być realizowany równolegle z S-01 po ukończeniu F-01. |

## Baseline

What's already in place in the codebase as of 2026-05-30 (auto-researched + user-confirmed).
Foundations below assume these are present and do NOT re-scaffold them.

- **Frontend (GUI desktopowy):** absent — brak CustomTkinter/Flet w `app/`; `app/ui/` nie istnieje; tylko HTML/JS w `app/static/` (stary prototyp FastAPI)
- **Logika domenowa (desktop):** absent — `app/domain/` nie istnieje; `app/main.py` to FastAPI prototype zastępowany w całości; pipeline EEG niezaimplementowany
- **Dane (norms.json):** partial — `norms.json` brak na dysku; zaplanowany w `neuroflag.spec:66` i `README.md:64`, schemat niezdefiniowany
- **Auth (hasło startowe):** absent — FR-009 (nice-to-have) niezaimplementowany; endpointy FastAPI są otwarte
- **Deploy / infra:** partial — `neuroflag.spec` istnieje (PyInstaller config); CI/CD w `.github/workflows/python-app.yml` (Windows build, smoke-test, artifact upload); `run.ps1` to legacy uvicorn
- **Observability:** absent — brak logging library w `app/`; brak Sentry/Datadog

## Foundations

### F-01: Fundament projektu desktopowego

- **Outcome:** (foundation) środowisko projektu gotowe: `pyproject.toml` z przypiętymi zależnościami (`customtkinter==5.2.2`, MNE-Python, ReportLab, pytest, mypy), stary kod FastAPI usunięty, `norms.json` z 10 kombinacjami norm z Business Logic (Średnia Z i K, zakresy pasm, `power_line_frequency: 50`, `recommendation_threshold: 3`), typy domenowe `PatientMetadata` / `NormsConfig` / `AnalysisResult` w `app/domain/types.py`.
- **Change ID:** project-foundation
- **PRD refs:** FR-008 (format i ścieżka norms.json definiowane tutaj)
- **Unlocks:** S-01 (potrzebuje GUI toolkit + types.py + struktury app/), S-02 (potrzebuje NormsConfig z norms.json + AnalysisResult), S-04 (potrzebuje ustalonego schematu norms.json)
- **Prerequisites:** —
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Decyzja GUI blokuje cały fundament — im szybciej podjęta, tym wcześniej F-01 przechodzi do statusu `ready`. Typy domenowe w `types.py` to kontrakt całego projektu: zmiana sygnatury po ukończeniu S-01/S-02 generuje falę poprawek we wszystkich modułach.
- **Status:** ready

## Slices

### S-01: Formularz metryki + import pliku EEG

- **Outcome:** użytkownik może otworzyć aplikację, wypełnić metrykę dziecka (wiek 6–10 lat, płeć, diagnozy), zobaczyć ostrzeżenie i blokadę analizy dla wykluczonych grup klinicznych (uraz/uszkodzenie mózgu, niepełnosprawność intelektualna, padaczka) oraz wczytać plik `.edf` lub `.vhdr` przyciskiem „Wczytaj plik" (drag & drop jako bonus) z wyraźnym komunikatem błędu jeśli plik jest nieobsługiwany lub uszkodzony.
- **Change ID:** metadata-and-import
- **PRD refs:** FR-001, FR-010, US-01
- **Prerequisites:** F-01
- **Parallel with:** S-04
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Decyzja GUI (CustomTkinter 5.2.2) jest zamknięta — architektura widoków jest określona. Główne ryzyko to poprawna struktura nawigacji CTk (widoki jako ramki przełączane w CTkFrame) zgodna z układem z AGENTS.md.
- **Status:** done

### S-02: Pipeline EEG + klasyfikacja + siatka wyników

- **Outcome:** użytkownik może kliknąć „Analizuj" i zobaczyć siatkę 10 kolorowych komórek (🔴/🟡/🟢) z kategorią wynikową (Wskazanie do dalszej diagnozy / Uważna obserwacja / Brak wskazań) i krótkim opisem słownym; surowe wartości µV są niewidoczne w UI.
- **Change ID:** eeg-pipeline-and-results
- **PRD refs:** FR-002, FR-003, FR-004, US-01
- **Prerequisites:** S-01
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Najwyższe ryzyko techniczne w projekcie: MNE-Python pipeline (wykrycie znaczników OO/OZ/ZP lub fallback co 3 minuty, selekcja C3/O1, usunięcie artefaktów ICA/progowych, obliczenie 10 wartości µV) + algorytm trójstanowy. Zakresy pasm potwierdzone (Delta 0,5–4 Hz, Theta 4–8 Hz, Beta1 15–18 Hz, Beta2 18–25 Hz) — implementacja może ruszać.
- **Status:** done

### S-03: Raport PDF i zapis na dysk

- **Outcome:** użytkownik może wygenerować raport PDF i zapisać go w wybranej lokalizacji na dysku lokalnym; surowe wartości µV nie są w raporcie. Struktura raportu (potwierdzona przez eksperta domenowego): (1) tekst wstępny — data badania, metryka dziecka, wniosek słowny w formie „Analiza wyników wskazuje na [kategoria + opis]"; (2) siatka kolorowa 10 komórek (RAG) z kategorią wynikową; (3) stała sekcja „Co obserwować" — tabela/lista kontrolna oparta na aktualnej wiedzy, niezmieniana między badaniami, skierowana do pedagoga/rodzica; (4) klauzula ograniczenia odpowiedzialności.
- **Change ID:** pdf-report-and-save
- **PRD refs:** FR-005, FR-006, US-01
- **Prerequisites:** S-02
- **Parallel with:** —
- **Blockers:** —
- **Unknowns:** —
- **Risk:** ReportLab jest sprawdzony i obecny w stosie; główne ryzyko to wierna rastoryzacja siatki kolorowej (RAG) w PDF — kolory muszą odpowiadać wytycznej eksperta domenowego (czerwony = a ≤ Z, żółty = Z < a < K, zielony = a ≥ K).
- **Status:** done

### S-04: Wymiana bazy norm

- **Outcome:** użytkownik może zastąpić plik `norms.json` w folderze aplikacji własnym plikiem konfiguracyjnym i mieć pewność, że aplikacja: (a) wczytuje nowe normy przy kolejnym uruchomieniu, (b) wyświetla czytelny komunikat błędu jeśli plik jest niezgodny ze schematem (brakujące pola, złe typy).
- **Change ID:** norms-replacement
- **PRD refs:** FR-008
- **Prerequisites:** F-01
- **Parallel with:** S-01
- **Blockers:** —
- **Unknowns:** —
- **Risk:** Minimalne ryzyko techniczne (statyczny JSON + walidacja schematu); główne ryzyko to dokumentacja — bez UI formularza użytkownik musi znać dokładny format pliku; brak jasnej instrukcji = frustracja przy podmiance przez psychologa-administratora.
- **Status:** done

## Backlog Handoff

| Roadmap ID | Change ID                | Suggested issue title                                                     | Ready for `/10x-plan` | Notes                                                  |
|------------|--------------------------|---------------------------------------------------------------------------|----------------------|--------------------------------------------------------|
| F-01       | project-foundation       | [Foundation] Środowisko desktopowe: pyproject.toml + norms.json + typy   | yes                  | Uruchom `/10x-plan project-foundation`                 |
| S-01       | metadata-and-import      | [S-01] Formularz metryki dziecka + import pliku EEG (.edf / .vhdr)        | no                   | Ready po ukończeniu F-01                               |
| S-02       | eeg-pipeline-and-results | [S-02] Pipeline EEG (MNE) + klasyfikacja trójstanowa + siatka kolorowa    | no                   | Ready po ukończeniu S-01                               |
| S-03       | pdf-report-and-save      | [S-03] Generowanie raportu PDF + zapis lokalny (ReportLab)                | no                   | Ready po ukończeniu S-02                               |
| S-04       | norms-replacement        | [S-04] Podmiana i walidacja schematu norms.json                           | no                   | Ready po ukończeniu F-01; równoległy z S-01            |

## Open Roadmap Questions

~~1. Zakresy pasm Delta/Theta/Beta1/Beta2?~~ — **ZAMKNIĘTE 2026-05-30.** Potwierdzone przez eksperta domenowego: Delta 0,5–4 Hz, Theta 4–8 Hz, Beta1 **15–18 Hz**, Beta2 **18–25 Hz**. Uwaga: Beta1 zaczyna się od 15 Hz (nie 12 Hz), Beta2 kończy na 25 Hz (nie 30 Hz). Alpha (8–13 Hz) i SMR (12–15 Hz) istnieją w aparacie, ale nie wchodzą do macierzy norm. S-02 odblokowany.

~~2. CustomTkinter vs Flet?~~ — **ZAMKNIĘTE 2026-05-30.** Wybrano CustomTkinter 5.2.2. F-01 odblokowany.

## Parked

- **Opcjonalne hasło startowe (FR-009, nice-to-have)** — Why parked: cel roadmapy `low-complexity`; warstwa ochrony bez szyfrowania plików odłożona na po MVP.
- **Bezpośredni druk z aplikacji (FR-007, usunięty)** — Why parked: PRD §Scope of Change (removed); użytkownik drukuje z systemowej przeglądarki PDF.
- **Nagrywanie EEG na żywo** — Why parked: PRD §Non-Goals; tylko import pliku po fakcie.
- **Porównywanie badań dziecka w czasie (trendy terapii)** — Why parked: PRD §Non-Goals; v2.0.
- **Centralna baza pacjentów / konta użytkowników SaaS** — Why parked: PRD §Non-Goals; 100% lokalne, wymaganie RODO.
- **Asystent LLM do opisów klinicznych** — Why parked: PRD §Non-Goals; v2.0.
- **Automatyczne pobieranie norm z serwera** — Why parked: PRD §Non-Goals; brak zależności sieciowej.
- **Statystyki neuroatypowości do celów badawczych** — Why parked: PRD §Non-Goals; wymaga audytu RODO.
- **Rosnąca lokalna baza norm (uczenie z każdego badania)** — Why parked: PRD §Non-Goals; v2.0.
- **Zróżnicowanie norm wiekowo (interpolacja 6–10 lat)** — Why parked: PRD §Non-Goals; v2.0.
- **Formularz GUI do wprowadzania norm (psycholog-administrator, bez edycji JSON)** — Why parked: S-04 (FR-008) dostarcza ręczną podmianę `norms.json` + walidację CLI/docs; widok CTk wymaga S-01 (`AppWindow`) i znacząco poszerza scope MVP — odłożone na v2.0 / osobny slice po S-01.
- **Formaty .bdf i .set** — Why parked: PRD §Constraints; v2.0.

## Done
- **S-04: zastapic plik norms.json wlasnym plikiem i miec pewnosc, ze aplikacja wczytuje nowe normy i waliduje schemat** — Archived 2026-06-21 -> context/archive/2026-06-01-norms-replacement/. Lesson: —.

(Empty on first generation. `/10x-archive` appends an entry here — and flips that item's `Status` to `done` — when a change whose `Change ID` matches the item is archived. Format:)

- **S-01: użytkownik może otworzyć aplikację, wypełnić metrykę dziecka (wiek 6–10 lat, płeć, diagnozy), zobaczyć ostrzeżenie i blokadę analizy dla wykluczonych grup klinicznych (uraz/uszkodzenie mózgu, niepełnosprawność intelektualna, padaczka) oraz wczytać plik `.edf` lub `.vhdr` przyciskiem „Wczytaj plik" (drag & drop jako bonus) z wyraźnym komunikatem błędu jeśli plik jest nieobsługiwany lub uszkodzony.** — Archived 2026-06-02 → `context/archive/2026-06-01-metadata-and-import/`. Lesson: —.
- **S-02: użytkownik może uruchomić analizę i zobaczyć siatkę 10 kolorowych komórek z kategorią wynikową** — Archived 2026-06-21 → `context/archive/2026-06-03-eeg-pipeline-and-results/`. Lesson: —.
- **S-03: wygenerować raport PDF i zapisać go na dysk lokalny** — Archived 2026-06-26 → `context/archive/2026-06-22-pdf-report-and-save/`. Lesson: —.
