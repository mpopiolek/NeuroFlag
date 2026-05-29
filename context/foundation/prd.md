---
project: "NeuroFlag"
version: 1
status: draft
created: 2026-05-29
context_type: brownfield
product_type: desktop
target_scale:
  users: small
  qps: n/a
  data_volume: small
timeline_budget:
  delivery_weeks: 8
  hard_deadline: null
  after_hours_only: true
---

## Current System Overview

**Cel systemu:** Szkielet aplikacji webowej do analizy plików EDF z sygnałami mózgowymi.

**Architektura:** Serwis monolityczny, stan w pamięci (bez bazy danych, ~3 commity).

**Stos technologiczny:** Python 3.x, FastAPI, MNE-Python (analiza EEG), Angular (frontend), serwuje HTML/JS pod `/`.

**Baza użytkowników:** Brak rzeczywistych użytkowników — wczesny prototyp.

**Kluczowa funkcjonalność:** Wgrywanie pliku EDF, podstawowe przetwarzanie sygnału. Brak wdrożonego flow raportu ani silnika norm.

---

## Problem Statement & Motivation

Pedagodzy i psycholodzy pracujący w polskich placówkach edukacyjnych mają dostęp do aparatów EEG/Biofeedback, ale nie dysponują narzędziem do szybkiej analizy przesiewowej sygnału mózgowego dzieci — bez wysyłania danych do sieci i bez konieczności angażowania specjalistów klinicznych na etapie wstępnym.

Obecny prototyp webowy nie rozwiązuje tego problemu: nie posiada interfejsu użytkownika, silnika norm, generowania raportów ani możliwości pracy w trybie offline. Architektura oparta na serwerze webowym jest ponadto niezgodna z wymaganiem prywatności (dane dziecka nie mogą opuszczać urządzenia). Zmiana jest uzasadniona teraz, gdyż: (1) empiryczna baza norm dla 200 dzieci (wiek 6–10 lat) jest gotowa i zwalidowana przez eksperta domenowego, (2) placówki edukacyjne dysponują sprzętem EEG, lecz brak kompatybilnego oprogramowania przesiewowego, (3) wymogi RODO i brak łączności internetowej w placówkach wykluczają rozwiązania chmurowe.

Obecny stan zastępczy: brak — pedagodzy nie mają żadnego narzędzia do analizy EEG na miejscu; przesiew wymaga pełnej wizyty u specjalisty klinicznego.

---

## User & Persona

### Primary persona

**Pedagog specjalny / pedagog szkolny**

Pracuje w placówce edukacyjnej lub poradni psychologiczno-pedagogicznej. Ma dostęp do aparatu EEG lub urządzenia Biofeedback, eksportuje z niego pliki .edf. Nie jest lekarzem — jego/jej celem jest określenie, czy dziecko wymaga skierowania na pełną diagnozę wielospecjalistyczną, nie postawienie diagnozy klinicznej. Sięga po NeuroFlag w momencie, gdy chce szybko ocenić duży zestaw dzieci (np. cały rocznik szkolny) bez angażowania specjalistów na wstępnym etapie.

Kluczowy moment: otwiera aplikację, wypełnia metrykę dziecka (wiek, płeć, diagnozy), przeciąga plik .edf lub .vhdr, klika „Analizuj" i otrzymuje wynik w trzech kolorach (czerwony/żółty/zielony) z jedną z trzech kategorii: Wskazanie do diagnozy / Uważna obserwacja / Brak wskazań — bez konfiguracji, bez sieci, bez szkolenia ponad instrukcję PDF.

### Secondary persona

**Psycholog kliniczny / diagnosta**

Wyższa wiedza kliniczna, pracuje w gabinecie lub poradni. Korzysta z narzędzia jako dodatkowego kontekstu ilościowego przed właściwą diagnozą. Może być też administratorem: aktualizuje bazę norm przez podmianę pliku konfiguracyjnego norm.

---

## Success Criteria

### Primary
- Użytkownik może wypełnić metrykę dziecka, wczytać plik .edf lub .vhdr i otrzymać wynik w jednej z trzech kategorii (Wskazanie / Uważna obserwacja / Brak wskazań) z wizualizacją kolorową — cały flow w jednej sesji, bez konfiguracji sieciowej.
- Procedura analizy i generowania raportu trwa ≤ 10 minut na standardowym komputerze biurowym.

### Secondary
- Aplikacja poprawnie wykrywa znaczniki zadań (OO/OZ/ZP) w plikach z minimum 3 różnych, popularnych aparatów EEG/Biofeedback dostępnych na rynku polskim; jeśli brak znaczników — dzieli nagranie co 3 minuty.

### Guardrails
- Użytkownik (pedagog, psycholog) uruchamia i obsługuje aplikację wyłącznie na podstawie dołączonej instrukcji PDF — bez dodatkowych szkoleń.
- Cały proces analizy i zapisu danych odbywa się lokalnie bez wywoływania ostrzeżeń bezpieczeństwa systemu operacyjnego (lub z jasno opisanym obejściem w instrukcji).
- Dane dziecka nigdy nie opuszczają urządzenia (żadne połączenia sieciowe w trakcie pracy aplikacji).

---

## User Stories

### US-01: Pedagog przeprowadza badanie przesiewowe dziecka

- **Given** pedagog otworzył aplikację NeuroFlag na lokalnym komputerze z systemem Windows
- **When** wypełnia metrykę dziecka (wiek, płeć, diagnozy), wczytuje plik .edf lub .vhdr wyeksportowany z aparatu EEG i klika „Analizuj"
- **Then** aplikacja przetwarza plik lokalnie, wyświetla siatkę 10 kolorowych komórek z kategorią wynikową (Wskazanie / Uważna obserwacja / Brak wskazań) oraz generuje raport PDF gotowy do zapisu

#### Acceptance Criteria
- Cały flow (metryka → import → analiza → siatka → PDF) kończy się w ≤ 10 minut
- Jeśli zaznaczono wykluczające diagnozy (uraz/uszkodzenie mózgu, niepełnosprawność intelektualna, padaczka) — aplikacja wyświetla ostrzeżenie i blokuje analizę
- Jeśli plik jest nieobsługiwany lub uszkodzony, użytkownik widzi czytelny komunikat błędu (nie crash)
- Raport PDF zawiera: metrykę dziecka, datę badania, siatkę kolorową, kategorię wynikową i klauzulę ograniczenia odpowiedzialności
- Surowe wartości µV nie są widoczne nigdzie w UI ani w raporcie

---

## Scope of Change

- [new] Formularz metryki dziecka (wiek 6–10 lat, płeć, lista diagnoz z wielokrotnym wyborem) z wyświetlaniem ostrzeżenia i blokowaniem analizy dla grup klinicznych wykluczonych z badania normatywnego: uraz/uszkodzenie mózgu, niepełnosprawność intelektualna, padaczka (FR-010)
- [new] Import pliku EEG w formacie .edf lub BrainVision (.vhdr + .vmrk + .eeg) — przycisk „Wczytaj plik" jako akcja główna, drag & drop jako ułatwienie (FR-001)
  > Socrates: Kontrargument rozważony: „pedagodzy mogą nie znać drag & drop". Rozwiązanie: przycisk jako akcja główna, drag & drop jako ułatwienie dla zaawansowanych.
- [new] Automatyczny pipeline przetwarzania sygnału: wykrycie znaczników zadań OO/OZ/ZP (fallback: podział nagrania co 3 minuty), selekcja kanałów C3 i O1 (system 10-20) z wykluczeniem kanałów EOG/ECG/EMG, usunięcie artefaktów (zakłócenia sieciowe, ruchy, mrugania, napięcia mięśni, artefakty padaczkowe), obliczenie średniej amplitudy [µV] dla 10 kombinacji lokalizacja×zadanie×pasmo (FR-002)
  > Socrates: Kontrargument rozważony: automatyczne usuwanie artefaktów może zniekształcić sygnał bez wiedzy użytkownika. Decyzja: FR stoi — w v2.0 można dodać raport jakości artefaktów.
- [new] Porównanie 10 wartości µV z bazą norm i klasyfikacja do jednej z trzech kategorii wynikowych (FR-003)
  > Socrates: Kontrargument rozważony: „wbudowana" baza norm sugeruje brak możliwości aktualizacji. Rozwiązanie: baza norm zawsze nadpisywalna przez podmianę pliku konfiguracyjnego.
- [new] Wizualizacja wyników jako siatka 10 kolorowych komórek (🔴/🟡/🟢) z kategorią wynikową i opisem słownym; surowe wartości µV niewidoczne dla użytkownika (FR-004)
  > Socrates: Kontrargument rozważony: „czy pedagog zrozumie siatkę kolorów?" Decyzja: FR stoi — trzy kolory są intuicyjne; legenda i opis w instrukcji PDF. Ekspert domenowy potwierdził: surowe µV NIE mogą być widoczne dla użytkownika.
- [new] Generowanie raportu PDF z metryką dziecka, datą badania, siatką kolorową, kategorią wynikową i klauzulą ograniczenia odpowiedzialności; bez surowych wartości µV (FR-005)
  > Socrates: Kontrargument rozważony: ryzyko odpowiedzialności prawnej jeśli raport traktowany jako dokument medyczny. Decyzja: FR stoi — raport to „narzędzie przesiewowe", nie diagnoza; klauzula wchodzi do raportu.
- [new] Zapis wygenerowanego raportu PDF na dysk lokalny (FR-006)
- [new] Podmiana domyślnej bazy norm przez ręczną wymianę pliku konfiguracyjnego w określonym folderze aplikacji (FR-008)
  > Socrates: Kontrargument rozważony: walidacja wgranego pliku przez UI to duży zakres. Decyzja: podmiana ręczna bez UI formularza — mniejszy scope, prostsze wdrożenie. UI formularz do v2.0.
- [new] Opcjonalne hasło startowe chroniące dostęp do aplikacji (FR-009, nice-to-have)
  > Socrates: Kontrargument rozważony: „hasło aplikacji bez szyfrowania plików = iluzja bezpieczeństwa". Decyzja: FR stoi jako nice-to-have — dodaje warstwę psychologiczną ochrony; pełne szyfrowanie plików to v2.0.
- [removed] Bezpośredni druk z aplikacji — użytkownik drukuje samodzielnie z systemowej przeglądarki PDF
- [removed] Interfejs webowy i serwis HTTP — zastąpione natywną aplikacją desktopową
- [preserved] Nic z kodu istniejącego prototypu nie jest przenoszone. Wiedza dziedzinowa o formacie EDF i przetwarzaniu sygnałów mózgowych (zbudowana podczas tworzenia prototypu) jest zachowywana.

---

## Constraints & Compatibility

**Brak zobowiązań do zachowania kodu:** Prototyp webowy nie ma użytkowników produkcyjnych ani opublikowanych kontraktów API. Migracja danych nie jest wymagana (brak persystentnych danych w prototypie).

**Formaty danych wejściowych:** `.edf` oraz BrainVision (`.vhdr` + `.vmrk` + `.eeg`) — oba rekomendowane przez standard BIDS jako formaty EEG. Formaty .bdf i .set odłożone do v2.0.

**Środowisko docelowe:** 64-bitowy system Windows 10 lub nowszy, praca w trybie offline (brak wychodzącego ruchu sieciowego podczas pracy aplikacji).

**Format pliku konfiguracyjnego norm:** Plik `norms.json` dostarczany z aplikacją, nadpisywalny ręcznie przez użytkownika. Zawiera: 10 par wartości norm (Średnia Z, Średnia K) dla kombinacji lokalizacja×zadanie×pasmo, konfigurowalną częstotliwość zakłóceń sieciowych (domyślnie 50 Hz), zakresy częstotliwości pasm Delta/Theta/Beta1/Beta2 oraz parametr `recommendation_threshold` (domyślnie 3).

**Brak wymagań zgodności wstecznej:** Zmiana jest pełnym zastąpieniem prototypu; żadne istniejące integracje, dane ani kontrakty nie muszą być zachowane.

---

## Business Logic Changes

Poprzedni system nie zawierał logiki domenowej. Poniżej opisana jest nowa logika wprowadzana w tej zmianie.

**Reguła domenowa:** Wynik przesiewowy dla dziecka jest wyznaczany przez porównanie 10 wartości amplitudy sygnału mózgowego (µV), zmierzonych w określonych warunkach zadaniowych i pasmach częstotliwości, z empiryczną bazą norm grupy dzieci bez zaburzeń (N=200, wiek 6–10 lat) oraz grupy z zaburzeniami, co skutkuje jedną z trzech kategorii decyzyjnych: Wskazanie do dalszej diagnozy, Uważna obserwacja lub Brak wskazań.

**Dane wejściowe (domenowe):** Plik EEG zawierający ciągłe nagranie z trzema warunkami zadaniowymi: OO (oczy otwarte), OZ (oczy zamknięte), ZP (zadanie pamięciowe/obliczenia) oraz metryka dziecka (wiek, płeć, diagnozy).

**Pipeline przetwarzania (kolejność kroków):**
1. Wykrycie znaczników OO/OZ/ZP w pliku; jeśli brak — podział nagrania co 3 minuty
2. Selekcja kanałów C3 i O1 (system 10-20); wykluczenie kanałów EOG/ECG/EMG
3. Usunięcie artefaktów: zakłócenia sieciowe przy konfigurowalnej częstotliwości (domyślnie 50 Hz), artefakty ruchowe, mrugania, napięcia mięśni, artefakty padaczkowe
4. Obliczenie średniej amplitudy [µV] dla każdego z 10 okien analizy: lokalizacja × warunek zadaniowy × pasmo częstotliwości

**Macierz norm (10 kombinacji) — wartości z badania 200 dzieci (wiek 6–10 lat), potwierdzone przez eksperta domenowego 2026-05-29:**

| # | Lokalizacja | Warunek | Pasmo | Średnia Z (zaburzenia) | Średnia K (kontrolna) |
|---|---|---|---|---|---|
| 1 | C3 | OZ | Theta | 30,35 µV | 35,44 µV |
| 2 | C3 | ZP | Theta | 20,32 µV | 25,25 µV |
| 3 | C3 | ZP | Beta1 | 5,26 µV | 6,56 µV |
| 4 | C3 | OO | Beta2 | 5,18 µV | 6,29 µV |
| 5 | O1 | OO | Delta | 25,5 µV | 28,63 µV |
| 6 | O1 | OO | Theta | 18,23 µV | 21,95 µV |
| 7 | O1 | OZ | Theta | 27,02 µV | 42,18 µV |
| 8 | O1 | ZP | Theta | 18,04 µV | 26,39 µV |
| 9 | O1 | OO | Beta2 | 3,51 µV | 5,36 µV |
| 10 | O1 | ZP | Beta2 | 6,22 µV | 7,95 µV |

**Kolorowanie każdej z 10 wartości (a = obliczona średnia amplituda):**
- 🔴 Czerwony: a ≤ Średnia Z → wynik jak u dzieci z zaburzeniami
- 🟡 Żółty: Średnia Z < a < Średnia K → strefa nieokreślona
- 🟢 Zielony: a ≥ Średnia K → wynik jak u dzieci bez zaburzeń

**Algorytm trójstanowy (na podstawie rozkładu 10 wartości):**
- **WSKAZANIE DO DALSZEJ DIAGNOZY:** wszystkie 10 wartości czerwone LUB ≥5 czerwonych i ≤3 zielonych
- **BRAK WSKAZAŃ:** wszystkie 10 wartości zielone LUB ≥4 zielonych i ≤3 czerwonych
- **UWAŻNA OBSERWACJA:** wszystkie pozostałe kombinacje

**Wynik dla użytkownika:** siatka 10 kolorowych komórek + nazwa kategorii + krótki opis słowny. Surowe wartości µV niewidoczne dla użytkownika.

---

## Access Control Changes

**Zmiana:** Prototyp webowy nie posiadał mechanizmu uwierzytelniania. Nowa aplikacja desktopowa wprowadza opcjonalne hasło startowe jako warstwę ochrony fizycznego dostępu do urządzenia.

**Nowy model dostępu:**
- Jeden użytkownik na urządzenie, jedna rola
- Brak rozdziału uprawnień — każdy użytkownik może zarówno przeprowadzać analizy, jak i aktualizować bazę norm przez podmianę pliku konfiguracyjnego
- Opcjonalne hasło startowe (nice-to-have, FR-009): jeśli ustawione w konfiguracji, aplikacja wymaga podania hasła przy uruchomieniu; jeśli nie ustawione, aplikacja uruchamia się bez zabezpieczenia
- Dane nigdy nie opuszczają urządzenia — ochrona fizycznego dostępu do komputera leży po stronie placówki

---

## Non-Goals

- **Brak nagrywania sygnału EEG na żywo** — aplikacja nie integruje się ze sprzętem w czasie rzeczywistym; tylko import pliku .edf po fakcie.
- **Brak porównywania historycznych badań dziecka w czasie** — trendy i postępy terapii to v2.0; MVP = analiza jednorazowego pliku.
- **Brak centralnej bazy pacjentów w chmurze ani kont użytkowników (SaaS)** — aplikacja jest w 100% lokalna; żadne dane nie trafiają na serwer.
- **Brak asystenta generującego opisy kliniczne** — automatyczne opisy prozą (dla lekarza / rodzica) to v2.0; MVP = reguła progowa + wykres kolorowy.
- **Brak automatycznego pobierania norm z serwera** — normy podmieniane ręcznie przez użytkownika; brak zależności sieciowej.
- **Brak gromadzenia statystyk neuroatypowości do celów badawczych** — funkcja wymaga audytu RODO i jest odłożona; MVP nie loguje żadnych zagregowanych danych.
- **Brak rosnącej lokalnej bazy norm** — mechanizm budowania własnych norm placówki z każdym wgranym badaniem planowany w v2.0; MVP korzysta ze statycznego pliku konfiguracyjnego norm.
- **Brak zróżnicowania norm wiekowo** — jednolity zestaw norm dla grupy 6–10 lat w MVP; interpolacja wiekowa w v2.0.

---

## Open Questions

1. **Jakie są dokładne zakresy częstotliwości pasm?** — Delta, Theta, Beta1, Beta2 — standardowe zakresy (np. Delta: 0,5–4 Hz, Theta: 4–8 Hz, Beta1: 12–18 Hz, Beta2: 18–30 Hz) czy specyficzne dla badania normatywnego? Właściciel: ekspert domenowy. Wpływa na: krok 4 pipeline przetwarzania sygnału (obliczanie średniej amplitudy per pasmo). Do potwierdzenia przed implementacją. Block: częściowy (implementacja możliwa z szacunkowymi wartościami standardowymi, lecz wyniki mogą odbiegać od normy referencyjnej).
