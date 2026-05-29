---
project: "NeuroFlag"
context_type: brownfield
created: 2026-05-23
updated: 2026-05-29
checkpoint:
  current_phase: 7
  phases_completed: [1, 2, 3, 4, 5, 6]
  frs_drafted: 10
  gray_areas_resolved:
    - topic: "preservation of existing prototype"
      decision: "Nic nie jest przenoszone. Aplikacja desktopowa to czysty start; prototyp webowy (FastAPI) służy jako wiedza dziedzinowa, nie jako baza kodu."
    - topic: "primary persona"
      decision: "Pedagog szkolny/specjalny (primary); psycholog kliniczny (secondary). Pedagog jest twardszym ograniczeniem — jeśli obsłuży bez szkolenia, psycholog tym bardziej."
    - topic: "insight: dlaczego to nie istnieje"
      decision: "Kombinacja trzech barier: (1) istniejące narzędzia wymagają wysyłania danych medycznych do sieci; (2) każdy producent EEG ma własne oprogramowanie bez wspólnych norm; (3) brak publicznie dostępnej, wiarygodnej bazy norm dla dzieci w konkretnej grupie wiekowej."
    - topic: "liczba elektrod i wartości analitycznych"
      decision: "2 lokalizacje (C3 i O1), 10 kombinacji lokalizacja×zadanie×pasmo — nie 5 elektrod i 25 wartości jak zakładano pierwotnie. Potwierdzone przez eksperta domenowego 2026-05-29."
    - topic: "wynik rekomendacji"
      decision: "Trzy stany: Wskazanie do dalszej diagnozy / Brak wskazań / Uważna obserwacja — nie binarne TAK/NIE. Algorytm oparty na granicach Z (zaburzenia) i K (kontrolna). Potwierdzone przez eksperta domenowego 2026-05-29."
    - topic: "protokół nagrania i wybór segmentu"
      decision: "Jeden plik ciągły ze znacznikami OO/OZ/ZP. Jeśli brak znaczników — podział co 3 minuty. Potwierdzone przez eksperta domenowego 2026-05-29."
    - topic: "jednostka wartości"
      decision: "µV (mikrowolty) — potwierdzone przez eksperta domenowego 2026-05-29."
    - topic: "widoczność surowych wartości dla użytkownika"
      decision: "Surowe wartości µV NIE są widoczne dla użytkownika. Użytkownik widzi wyłącznie kolory (czerwony/żółty/zielony) i kategorię wyniku."
    - topic: "metryczka pacjenta i kryteria wykluczenia"
      decision: "Aplikacja zbiera metrykę (wiek, płeć, diagnozy) i ostrzega przed użyciem dla dzieci z urazem mózgu, niepełnosprawnością intelektualną lub padaczką — te grupy były wykluczone z badania normatywnego."
    - topic: "uczenie maszynowe i rosnąca baza norm"
      decision: "Funkcja lokalnej bazy wyników budowanej z każdym badaniem (własne normy placówki) odłożona do v2.0. MVP korzysta wyłącznie ze statycznego pliku norms.json."
  quality_check_status: pending
---

## Current System

**Cel systemu:** Szkielet aplikacji webowej FastAPI (Python) do analizy plików EDF z sygnałami mózgowymi.

**Architektura:** Single-service, monolityczna, stan w pamięci (bez bazy danych).

**Stos technologiczny:** Python 3.x, FastAPI, MNE-Python (analiza EEG), Angular (frontend), serwuje HTML/JS pod `/`.

**Baza użytkowników:** Brak rzeczywistych użytkowników — wczesny prototyp (~3 commity: szkielet aplikacji).

**Kluczowa funkcjonalność:** Upload pliku EDF, podstawowe przetwarzanie sygnału, brak wdrożonego flow raportu.

**Co zostaje:** Nic z kodu. Wiedza dziedzinowa o formacie EDF i przetwarzaniu sygnałów MNE-Python jest zachowywana.

---

## Vision & Problem Statement

Tradycyjna diagnostyka neurorozwojowa dzieci jest żmudna, kosztowna i wymaga wysoko wyspecjalizowanej kadry. Brakuje szybkiego narzędzia przesiewowego, które pozwoliłoby na przebadanie dużej liczby dzieci przy użyciu sprzętu EEG/Biofeedback już dostępnego w placówkach edukacyjnych — bez wysyłania danych medycznych do sieci.

Insight: trzy bariery blokują powstanie takiego narzędzia jednocześnie — wymóg łączności sieciowej (RODO, brak internetu w placówkach), brak standaryzacji między producentami sprzętu EEG oraz brak publicznie dostępnej bazy norm odniesienia dla dzieci w konkretnych grupach wiekowych. NeuroFlag adresuje wszystkie trzy przez lokalność (100% offline), obsługę otwartego formatu .edf (wspólny mianownik dla wielu aparatów) oraz własną bazę norm opartą na badaniu 200 osób (6–10 lat).

---

## User & Persona

### Primary persona

**Pedagog specjalny / pedagog szkolny**

Pracuje w placówce edukacyjnej lub poradni psychologiczno-pedagogicznej. Ma dostęp do aparatu EEG lub urządzenia Biofeedback, eksportuje z niego pliki .edf. Nie jest lekarzem — jego/jej celem jest określenie, czy dziecko wymaga skierowania na pełną diagnozę wielospecjalistyczną, nie postawienie diagnozy klinicznej. Sięga po NeuroFlag w momencie, gdy chce szybko ocenić duży zestaw dzieci (np. cały rocznik szkolny) bez angażowania specjalistów na wstępnym etapie.

Kluczowy moment: otwiera aplikację, wypełnia metrykę dziecka (wiek, płeć, diagnozy), przeciąga plik .edf lub .vhdr, klika „Analizuj" i otrzymuje wynik w trzech kolorach (czerwony/żółty/zielony) z jedną z trzech kategorii: Wskazanie do diagnozy / Uważna obserwacja / Brak wskazań — bez konfiguracji, bez sieci, bez szkolenia ponad instrukcję PDF.

### Secondary persona

**Psycholog kliniczny / diagnosta**

Wyższa wiedza kliniczna, pracuje w gabinecie lub poradni. Korzysta z narzędzia jako dodatkowego kontekstu ilościowego przed właściwą diagnozą. Może być też administratorem: aktualizuje bazę norm przez formularz konfiguracyjny.

---

## Access Control

Jeden użytkownik na urządzenie, jedna rola. Brak rozdział uprawnień — każdy użytkownik może zarówno przeprowadzać analizy, jak i aktualizować bazę norm.

**Zabezpieczenie:** Opcjonalne hasło startowe (ustawiane w konfiguracji). Jeśli nie ustawione, aplikacja uruchamia się bez zabezpieczenia. Dane nigdy nie opuszczają urządzenia — ochrona fizycznego dostępu do komputera leży po stronie placówki.

Zmiana względem obecnego systemu: brak (web prototype nie miał auth). Nowa decyzja dla produktu desktopowego: opcjonalny PIN lokalny.

---

## Success Criteria

### Primary
- Użytkownik może wypełnić metrykę dziecka, wczytać plik .edf lub .vhdr i otrzymać wynik w jednej z trzech kategorii (Wskazanie / Uważna obserwacja / Brak wskazań) z wizualizacją kolorową — cały flow w jednej sesji, bez konfiguracji sieciowej.
- Procedura analizy i generowania raportu trwa ≤ 10 minut na standardowym komputerze biurowym.

### Secondary
- Aplikacja poprawnie wykrywa znaczniki zadań (OO/OZ/ZP) w plikach z minimum 3 różnych, popularnych aparatów EEG/Biofeedback dostępnych na rynku polskim; jeśli brak znaczników — dzieli nagranie co 3 minuty.

### Guardrails
- Użytkownik (pedagog, psycholog) uruchamia i obsługuje aplikację wyłącznie na podstawie dołączonej instrukcji PDF — bez dodatkowych szkoleń.
- Cały proces analizy i zapisu danych odbywa się lokalnie bez wywoływania błędów bezpieczeństwa Windows.
- Dane dziecka nigdy nie opuszczają urządzenia (żadne połączenia sieciowe w trakcie pracy aplikacji).

---

## Functional Requirements

### Import i analiza

- FR-001: Użytkownik może wczytać plik w formacie .edf lub BrainVision (.vhdr) przyciskiem „Wczytaj plik" (akcja główna) lub metodą drag & drop (bonus). Oba formaty są rekomendowane przez standard BIDS jako jedyne dwa zalecane formaty EEG. Priority: must-have
  > Socrates: Kontrargument rozważony: „pedagodzy mogą nie znać drag & drop". Rozwiązanie: przycisk jako akcja główna, drag & drop jako ułatwienie dla zaawansowanych.
  > Zmiana 2026-05-24: rozszerzono MVP o format BrainVision (.vhdr + .vmrk + .eeg) na podstawie analizy standardu BIDS i MNE-Python. Koszt implementacyjny minimalny (mne.io.read_raw_brainvision()). Formaty .bdf i .set odłożone do v2.0.

- FR-002: Aplikacja automatycznie przetwarza wczytany plik w następującej kolejności: (1) wykrycie znaczników zadań OO/OZ/ZP — jeśli brak znaczników, podział nagrania co 3 minuty; (2) selekcja kanałów C3 i O1 (system 10-20) z wykluczeniem kanałów EOG, ECG, EMG; (3) usunięcie artefaktów: zakłócenia sieciowe (notch 50 Hz — konfigurowalne w norms.json), artefakty ruchowe, mrugania, napięcia mięśni, artefakty padaczkowe; (4) obliczenie średniej amplitudy [µV] dla 10 kombinacji lokalizacja×zadanie×pasmo zgodnie z macierzą norm. Priority: must-have
  > Socrates: Kontrargument rozważony: automatyczne usuwanie może zniekształcić sygnał bez wiedzy użytkownika. Decyzja: FR stoi — MNE-Python ma sprawdzone algorytmy; w v2.0 można dodać raport jakości artefaktów.
  > Zmiana 2026-05-24: selekcja kanałów według typów BIDS (EEG/EOG/ECG/EMG). Częstotliwość sieciowa konfigurowalna.
  > Zmiana 2026-05-29 (ekspert domenowy): TYLKO 2 lokalizacje (C3, O1) — nie 5. Jeden plik ciągły ze znacznikami OO/OZ/ZP. Jednostka: µV. 10 kombinacji do analizy (nie 25).

- FR-003: Aplikacja porównuje 10 obliczonych wartości µV z bazą norm (plik norms.json). Każda z 10 kombinacji ma dwie granice: Średnią Z (grupa z zaburzeniami) i Średnią K (grupa kontrolna). Dla każdej wartości wyznaczany jest kolor: 🔴 a ≤ Z, 🟡 Z < a < K, 🟢 a ≥ K. Na podstawie rozkładu kolorów algorytm wystawia jeden z trzech wyników: **Wskazanie do dalszej diagnozy** (≥5 wartości ≤Z i ≤3 wartości ≥K; lub wszystkie ≤Z) / **Brak wskazań** (≥4 wartości ≥K i ≤3 wartości ≤Z; lub wszystkie ≥K) / **Uważna obserwacja** (wszystkie pozostałe kombinacje). Surowe wartości µV nie są wyświetlane użytkownikowi. Priority: must-have
  > Socrates: Kontrargument rozważony: „wbudowana" baza norm sugeruje brak możliwości aktualizacji. Rozwiązanie: „domyślna baza norm" — zawsze nadpisywalna przez podmianę norms.json.
  > Zmiana 2026-05-29 (ekspert domenowy): algorytm trójstanowy zamiast binarnego TAK/NIE. Dwie granice (Z i K) zamiast jednej. 10 wartości zamiast 25. Rzeczywiste wartości norm wpisane do norms.json (patrz sekcja Business Logic).

### Prezentacja wyników

- FR-004: Aplikacja wyświetla wizualizację wyników jako siatkę 10 komórek (2 lokalizacje × zadania × pasma), gdzie każda komórka zabarwiona jest kolorem 🔴/🟡/🟢. Surowe wartości µV nie są widoczne dla użytkownika. Pod siatką wyświetlana jest kategoria wynikowa (Wskazanie / Uważna obserwacja / Brak wskazań) z krótkim opisem słownym. Priority: must-have
  > Socrates: Kontrargument rozważony: „czy pedagog zrozumie siatkę kolorów?" Decyzja: FR stoi — trzy kolory są intuicyjne; legenda i opis w instrukcji PDF. Ekspert domenowy potwierdził: surowe µV NIE mogą być widoczne dla użytkownika.
  > Zmiana 2026-05-29: zmieniono z wykresu słupkowego/radarowego na siatkę kolorową 10 komórek zgodnie z wytyczną eksperta.

### Raport

- FR-005: Aplikacja generuje raport PDF zawierający: dane metryki dziecka (wiek, płeć), datę badania, siatkę kolorową 10 komórek, kategorię wynikową (Wskazanie / Uważna obserwacja / Brak wskazań) oraz klauzulę ograniczenia odpowiedzialności. Surowe wartości µV nie są zamieszczane w raporcie. Priority: must-have
  > Socrates: Kontrargument rozważony: ryzyko odpowiedzialności prawnej jeśli raport traktowany jako dokument medyczny. Decyzja: FR stoi — raport to „narzędzie przesiewowe", nie diagnoza; klauzula wchodzi do raportu.
  > Zmiana 2026-05-29: zaktualizowano zawartość raportu — wynik trójstanowy zamiast TAK/NIE, siatka kolorowa zamiast tabeli µV.

- FR-006: Użytkownik może zapisać wygenerowany raport PDF na dysk lokalny. Priority: must-have
  > Socrates: Brak kontrargumentu. FR stoi.

- ~~FR-007: Druk bezpośrednio z aplikacji~~ — **usunięty z MVP.** Użytkownik drukuje samodzielnie z systemowego PDF viewer. Oszczędność: brak integracji z Windows Printing API.

### Konfiguracja norm

- FR-008: Użytkownik może zastąpić domyślną bazę norm poprzez ręczną podmianę pliku .json w określonym folderze aplikacji (format opisany w dokumentacji). Plik norm zawiera m.in. pole `recommendation_threshold` (domyślnie 3) oraz `power_line_frequency` (domyślnie 50). Priority: must-have
  > Socrates: Kontrargument rozważony: walidacja wgranego pliku przez UI to duży zakres. Decyzja: podmiana ręczna (bez UI formularza) — mniejszy scope, prostsze wdrożenie. UI formularz do v2.0. Obsługa .xlsx odłożona do v2.0 (unika zależności openpyxl).
  > Zmiana 2026-05-24: dodano pole `power_line_frequency` (50/60 Hz) umożliwiające użycie aplikacji na rynkach spoza Europy. Dodano pole `recommendation_threshold` jako parametr konfigurowalny przez badacza bez zmiany kodu.

### Metryczka pacjenta

- FR-010: Przed wczytaniem pliku EEG użytkownik wypełnia metrykę dziecka: wiek (6–10 lat), płeć, aktualne lub podejrzewane diagnozy (wielokrotny wybór: ASD/Asperger, ADHD, depresja/lęki, dysleksja, inne). Aplikacja wyświetla ostrzeżenie i blokuje analizę jeśli zaznaczono: uraz/uszkodzenie mózgu, niepełnosprawność intelektualna lub padaczka — te grupy były wykluczone z badania normatywnego i wynik byłby niewiarygodny. Dane metryki zapisywane są wyłącznie lokalnie i trafiają do raportu PDF. Priority: must-have
  > Zmiana 2026-05-29 (ekspert domenowy): nowy FR. Metryczka umożliwia przyszłe uczenie maszynowe (v2.0) i stanowi zabezpieczenie kliniczne przed użyciem narzędzia w wykluczonych grupach.

### Bezpieczeństwo

- FR-009: Użytkownik może opcjonalnie skonfigurować hasło startowe chroniące dostęp do aplikacji. Priority: nice-to-have
  > Socrates: Kontrargument rozważony: „hasło aplikacji bez szyfrowania plików = iluzja bezpieczeństwa". Decyzja: FR stoi jako nice-to-have — dodaje warstwę psychologiczną ochrony; pełne szyfrowanie plików to v2.0.

---

## User Stories

### US-01: Pedagog przeprowadza badanie przesiewowe dziecka

- **Given** pedagog otworzył aplikację NeuroFlag na lokalnym komputerze Windows
- **When** wypełnia metrykę dziecka (wiek, płeć, diagnozy), wczytuje plik .edf lub .vhdr wyeksportowany z aparatu EEG i klika „Analizuj"
- **Then** aplikacja przetwarza plik, wyświetla siatkę 10 kolorowych komórek z kategorią wynikową (Wskazanie / Uważna obserwacja / Brak wskazań) oraz generuje raport PDF

#### Acceptance Criteria
- Cały flow (metryka → import → analiza → siatka → PDF) kończy się w ≤ 10 minut
- Jeśli zaznaczono wykluczające diagnozy (uraz mózgu, niepełnosprawność intelektualna, padaczka) — aplikacja wyświetla ostrzeżenie i blokuje analizę
- Jeśli plik jest nieobsługiwany lub uszkodzony, użytkownik widzi czytelny komunikat błędu (nie crash)
- Raport PDF zawiera: metrykę dziecka, datę badania, siatkę kolorową, kategorię wynikową i klauzulę ograniczenia odpowiedzialności
- Surowe wartości µV nie są widoczne nigdzie w UI ani w raporcie

---

---

## Business Logic

**Dane wejściowe:** plik EEG (.edf lub .vhdr) zawierający ciągłe nagranie z trzema zadaniami (OO = oczy otwarte, OZ = oczy zamknięte, ZP = zadanie pamięciowe/obliczenia) oraz metryka dziecka (wiek, płeć, diagnozy).

**Pipeline przetwarzania:**
1. Wykrycie znaczników OO/OZ/ZP w pliku; jeśli brak — podział co 3 minuty
2. Selekcja kanałów C3 i O1 (system 10-20); wykluczenie EOG/ECG/EMG
3. Usunięcie artefaktów: notch 50 Hz, ICA lub metoda progowa dla ruchów/mrugań/mięśni/padaczkowych
4. Obliczenie średniej amplitudy [µV] dla każdego z 10 aktywnych okien: lokalizacja × zadanie × pasmo

**Macierz norm (10 kombinacji) — wartości z badania 200 dzieci (6–10 lat):**

| # | Lokalizacja | Zadanie | Pasmo | Średnia Z (zaburzenia) | Średnia K (kontrolna) |
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

**Kolorowanie każdej z 10 wartości (a = obliczona średnia):**
- 🔴 Czerwony: a ≤ Średnia Z → wynik jak u dzieci z zaburzeniami
- 🟡 Żółty: Średnia Z < a < Średnia K → strefa nieokreślona
- 🟢 Zielony: a ≥ Średnia K → wynik jak u dzieci bez zaburzeń

**Algorytm trójstanowy (na podstawie 10 wartości):**
- **WSKAZANIE DO DALSZEJ DIAGNOZY:** wszystkie 10 wartości czerwone LUB ≥5 czerwonych i ≤3 zielonych
- **BRAK WSKAZAŃ:** wszystkie 10 wartości zielone LUB ≥4 zielonych i ≤3 czerwonych
- **UWAŻNA OBSERWACJA:** wszystkie pozostałe kombinacje

**Wynik dla użytkownika:** siatka 10 kolorowych komórek + nazwa kategorii + krótki opis słowny. Surowe wartości µV niewidoczne dla użytkownika.

---

## Non-Functional Requirements

- Pełny flow (import .edf → analiza artefaktów → obliczenie metryk → wykres → raport PDF) kończy się w czasie ≤ 10 minut na standardowym komputerze biurowym.
- Aplikacja poprawnie odczytuje i przetwarza pliki .edf z minimum 3 różnych popularnych urządzeń EEG/Biofeedback dostępnych na rynku polskim.
- Użytkownik (pedagog, psycholog) jest w stanie samodzielnie przeprowadzić pełne badanie przesiewowe na podstawie wyłącznie dołączonej instrukcji PDF — bez kontaktu z helpdeskiem ani dodatkowych szkoleń.
- Żadne dane dziecka (plik .edf, wyniki, raport) nie opuszczają urządzenia podczas pracy aplikacji (brak ruchu sieciowego wychodzącego).
- Aplikacja instaluje się i uruchamia na Windows 10/11 bez wywoływania ostrzeżeń Windows Defender SmartScreen (lub z jasno opisanym obejściem w instrukcji, jeśli certyfikat EV jest poza budżetem MVP).

---

## Constraints & Preserved Behavior

Zmiana: prototyp webowy zastępowany jest w całości aplikacją desktopową.

**Brak zobowiązań do zachowania:** prototyp FastAPI nie ma użytkowników produkcyjnych ani kontraktów API do utrzymania.

**Nowe ograniczenia techniczne:**
- Format danych wejściowych: `.edf` oraz BrainVision (`.vhdr` + `.vmrk` + `.eeg`) — oba rekomendowane przez standard BIDS; formaty .bdf i .set w v2.0
- Środowisko docelowe: Windows 10/11, 64-bit (PyInstaller .exe)
- Brak dostępu do sieci w trakcie pracy (wymaganie prywatności)
- Baza norm: domyślny plik `norms.json` dostarczany z aplikacją; nadpisywalny przez użytkownika; zawiera: 10 par wartości (Średnia Z, Średnia K) dla kombinacji lokalizacja×zadanie×pasmo, pole `power_line_frequency` (domyślnie 50), zakresy częstotliwości pasm

---

## Timeline acknowledgment
Acknowledged on 2026-05-23: 8-tygodniowy MVP wymaga konsekwentnej pracy wieczorami i w weekendy przez ~2 miesiące. Użytkownik świadomie zaakceptował ten koszt.

---

## Non-Goals

- **Brak nagrywania sygnału EEG na żywo** — aplikacja nie integruje się ze sprzętem w czasie rzeczywistym; tylko import pliku .edf po fakcie.
- **Brak porównywania historycznych badań dziecka w czasie** — trendy i postępy terapii to v2.0; MVP = analiza jednorazowego pliku.
- **Brak centralnej bazy pacjentów w chmurze ani kont użytkowników (SaaS)** — aplikacja jest w 100% lokalna; żadne dane nie trafiają na serwer.
- **Brak asystenta LLM do generowania opisów klinicznych** — automatyczne opisy prozą (dla lekarza / rodzica) to v2.0; MVP = reguła progowa + wykres.
- **Brak automatycznego pobierania norm z serwera** — normy podmieniane ręcznie przez użytkownika; brak zależności sieciowej.
- **Brak gromadzenia statystyk neuroatypowości do celów badawczych** — funkcja wymaga audytu RODO i jest odłożona; MVP nie loguje żadnych zagregowanych danych.
- **Brak rosnącej lokalnej bazy norm** — mechanizm budowania własnych norm placówki z każdym wgranym badaniem (uczenie) planowany w v2.0; MVP korzysta ze statycznego norms.json.
- **Brak zróżnicowania norm wiekowo** — jednolity zestaw norm dla grupy 6–10 lat w MVP; interpolacja wiekowa w v2.0.

---

## Open Questions

~~1. Jaka jest dokładna reguła wyznaczania rekomendacji TAK/NIE?~~ — **ZAMKNIĘTE 2026-05-29.** Algorytm trójstanowy z granicami Z i K. Patrz Business Logic.

~~2. Jak wybierany jest segment ~3 minut do analizy?~~ — **ZAMKNIĘTE 2026-05-29.** Jeden plik ciągły ze znacznikami OO/OZ/ZP; jeśli brak znaczników — podział co 3 minuty.

~~3. Które lokalizacje elektrod?~~ — **ZAMKNIĘTE 2026-05-29.** C3 i O1 (system 10-20).

~~4. Jednostka: µV czy µV²?~~ — **ZAMKNIĘTE 2026-05-29.** µV (mikrowolty).

~~5. Normy jednolite czy zróżnicowane wiekowo?~~ — **CZĘŚCIOWO ZAMKNIĘTE 2026-05-29.** MVP używa jednego zestawu norm dla grupy 6–10 lat. Zróżnicowanie wiekowe planowane w v2.0 wraz z mechanizmem uczenia (rosnąca lokalna baza norm).

6. **Jakie są dokładne zakresy częstotliwości pasm?** — Delta, Theta, Beta1, Beta2 — standardowe zakresy (np. Delta: 0,5–4 Hz, Theta: 4–8 Hz, Beta1: 12–18 Hz, Beta2: 18–30 Hz) czy specyficzne dla badania? Właściciel: ekspert domenowy. Wpływa na: implementację FR-002 (filtracja pasmowa). Do potwierdzenia przed implementacją.

---

## Forward: tech-stack

(Poniżej dla /10x-stack-assess — nie jest częścią PRD)

Rekomendowany przez użytkownika:
- Język: Python 3.x
- GUI: CustomTkinter lub Flet
- EEG: PyEDFlib + SciPy / MNE-Python
- Wykresy: Matplotlib lub Plotly
- PDF: ReportLab lub FPDF2
- Dystrybucja: PyInstaller (.exe single-file)
- Normy: plik .json (podmienialny ręcznie)

