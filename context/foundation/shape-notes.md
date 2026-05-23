---
project: "NeuroFlag"
context_type: brownfield
created: 2026-05-23
updated: 2026-05-23
checkpoint:
  current_phase: 7
  phases_completed: [1, 2, 3, 4, 5, 6]
  frs_drafted: 8
  gray_areas_resolved:
    - topic: "preservation of existing prototype"
      decision: "Nic nie jest przenoszone. Aplikacja desktopowa to czysty start; prototyp webowy (FastAPI) służy jako wiedza dziedzinowa, nie jako baza kodu."
    - topic: "primary persona"
      decision: "Pedagog szkolny/specjalny (primary); psycholog kliniczny (secondary). Pedagog jest twardszym ograniczeniem — jeśli obsłuży bez szkolenia, psycholog tym bardziej."
    - topic: "insight: dlaczego to nie istnieje"
      decision: "Kombinacja trzech barier: (1) istniejące narzędzia wymagają wysyłania danych medycznych do sieci; (2) każdy producent EEG ma własne oprogramowanie bez wspólnych norm; (3) brak publicznie dostępnej, wiarygodnej bazy norm dla dzieci w konkretnej grupie wiekowej."
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

Kluczowy moment: otwiera aplikację, przeciąga plik .edf, otrzymuje wydruk z odpowiedzią TAK/NIE dla skierowania — bez konfiguracji, bez sieci, bez szkolenia ponad instrukcję PDF.

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
- Użytkownik może wczytać plik .edf metodą przeciągnięcia i upuszczenia, uruchomić analizę oraz otrzymać gotowy raport PDF z wykresem i rekomendacją TAK/NIE dla skierowania — cały flow w jednej sesji, bez żadnej konfiguracji sieciowej.
- Procedura analizy i generowania raportu trwa ≤ 10 minut na standardowym komputerze biurowym.

### Secondary
- Aplikacja poprawnie interpretuje pliki .edf z minimum 3 różnych, popularnych aparatów EEG/Biofeedback dostępnych na rynku.

### Guardrails
- Użytkownik (pedagog, psycholog) uruchamia i obsługuje aplikację wyłącznie na podstawie dołączonej instrukcji PDF — bez dodatkowych szkoleń.
- Cały proces analizy i zapisu danych odbywa się lokalnie bez wywoływania błędów bezpieczeństwa Windows.
- Dane dziecka nigdy nie opuszczają urządzenia (żadne połączenia sieciowe w trakcie pracy aplikacji).

---

## Functional Requirements

### Import i analiza

- FR-001: Użytkownik może wczytać plik .edf przyciskiem „Wczytaj plik" (akcja główna) lub metodą drag & drop (bonus). Priority: must-have
  > Socrates: Kontrargument rozważony: „pedagodzy mogą nie znać drag & drop". Rozwiązanie: przycisk jako akcja główna, drag & drop jako ułatwienie dla zaawansowanych.

- FR-002: Aplikacja automatycznie usuwa podstawowe artefakty sygnału (ruch, bicie serca, zakłócenia sieciowe 50Hz), a następnie oblicza średnią amplitudę w 5 pasmach (Delta, Theta, Alpha, Beta, Gamma) dla 5 predefiniowanych lokalizacji elektrod — tworząc macierz 5×5 wartości [µV]. Segment analizy: ~3 minuty (sposób wyboru segmentu — patrz Open Questions). Priority: must-have
  > Socrates: Kontrargument rozważony: automatyczne usuwanie może zniekształcić sygnał bez wiedzy użytkownika. Decyzja: FR stoi — SciPy/MNE-Python mają sprawdzone algorytmy; w v2.0 można dodać raport jakości artefaktów.

- FR-003: Aplikacja porównuje macierz 25 wartości amplitud z domyślną bazą norm (wiek 6–10 lat; 200 osób) zawierającą obszary normy dla każdej z 25 komórek macierzy. Baza może być zastąpiona przez użytkownika (FR-008). Priority: must-have
  > Socrates: Kontrargument rozważony: „wbudowana" baza norm sugeruje brak możliwości aktualizacji. Rozwiązanie: „domyślna baza norm" — zawsze nadpisywalna. Baza norm definiuje też, które lokalizacje elektrod i pasma są brane pod uwagę. Zgodne z modelem laboratoriów diagnostycznych.

### Prezentacja wyników

- FR-004: Użytkownik może wyświetlić wykres profilowy z odchyleniami metryk EEG od normy (słupkowy lub radarowy). Priority: must-have
  > Socrates: Kontrargument rozważony: „czy pedagog odczyta wykres bez opisu?" Decyzja: FR stoi — opis metryk w instrukcji PDF; w MVP wykres z podpisanymi osiami wystarczy.

### Raport

- FR-005: Aplikacja generuje raport PDF zawierający: dane analizy, wykres profilowy, rekomendację skierowania TAK/NIE (opartą na regule progowej — patrz Open Questions). Priority: must-have
  > Socrates: Kontrargument rozważony: ryzyko odpowiedzialności prawnej jeśli raport traktowany jako dokument medyczny. Decyzja: FR stoi — raport to „narzędzie przesiewowe", nie diagnoza; klauzula ograniczenia odpowiedzialności wchodzi do treści raportu.

- FR-006: Użytkownik może zapisać wygenerowany raport PDF na dysk lokalny. Priority: must-have
  > Socrates: Brak kontrargumentu. FR stoi.

- ~~FR-007: Druk bezpośrednio z aplikacji~~ — **usunięty z MVP.** Użytkownik drukuje samodzielnie z systemowego PDF viewer. Oszczędność: brak integracji z Windows Printing API.

### Konfiguracja norm

- FR-008: Użytkownik może zastąpić domyślną bazę norm poprzez ręczną podmianę pliku .json w określonym folderze aplikacji (format opisany w dokumentacji). Priority: must-have
  > Socrates: Kontrargument rozważony: walidacja wgranego pliku przez UI to duży zakres. Decyzja: podmiana ręczna (bez UI formularza) — mniejszy scope, prostsze wdrożenie. UI formularz do v2.0. Obsługa .xlsx odłożona do v2.0 (unika zależności openpyxl).

### Bezpieczeństwo

- FR-009: Użytkownik może opcjonalnie skonfigurować hasło startowe chroniące dostęp do aplikacji. Priority: nice-to-have
  > Socrates: Kontrargument rozważony: „hasło aplikacji bez szyfrowania plików = iluzja bezpieczeństwa". Decyzja: FR stoi jako nice-to-have — dodaje warstwę psychologiczną ochrony; pełne szyfrowanie plików to v2.0.

---

## User Stories

### US-01: Pedagog przeprowadza badanie przesiewowe dziecka

- **Given** pedagog otworzył aplikację NeuroFlag na lokalnym komputerze Windows
- **When** przeciąga lub wczytuje przyciskiem plik .edf wyeksportowany z aparatu EEG/Biofeedback
- **Then** aplikacja przetwarza plik, wyświetla wykres profilowy z odchyleniami od normy oraz generuje raport PDF z rekomendacją TAK/NIE dla skierowania na pełną diagnozę

#### Acceptance Criteria
- Cały flow (import → analiza → wykres → PDF) kończy się w ≤ 10 minut
- Jeśli plik .edf jest nieobsługiwany lub uszkodzony, użytkownik widzi czytelny komunikat błędu (nie crash)
- Raport PDF zawiera: datę badania, wykres profilowy, tabelę metryk vs. norma, rekomendację z klauzulą ograniczenia odpowiedzialności

---

---

## Business Logic

Aplikacja automatycznie wybiera 5 (lub 3, jeśli tyle dostępnych) standardowych lokalizacji elektrod z pliku .edf (zestaw predefiniowany w bazie norm), a następnie dla wybranego segmentu nagrania oblicza średnią amplitudę w 5 klasycznych pasmach częstotliwości EEG (Delta, Theta, Alpha, Beta, Gamma). Wynikiem jest macierz 5 lokalizacji × 5 pasm = 25 wartości średnich [µV], które porównywane są z odpowiednim obszarem normy dla grupy wiekowej dziecka. Na tej podstawie wystawiana jest binarna rekomendacja przesiewowa TAK/NIE.

**Dane wejściowe (z perspektywy użytkownika):** plik .edf z nagraniem EEG (dowolna długość) oraz wiek dziecka.

**Przetwarzanie:** usunięcie artefaktów → wybór segmentu analizy (~3 minuty; patrz Open Questions) → obliczenie średniej amplitudy per pasmo per lokalizacja → macierz 25 wartości.

**Wynik:** macierz 5×5 z wartościami vs. norma + profil odchyleń + rekomendacja TAK/NIE z klauzulą „narzędzie przesiewowe, nie diagnoza".

**Otwarte pytania:** (1) reguła TAK/NIE — próg liczby/wagi odchyleń w macierzy; (2) wybór segmentu 3-minutowego — pełna automatyka vs. manualne wskazanie — patrz Open Questions.

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
- Format danych wejściowych: tylko .edf (otwarty standard — wspólny mianownik dla wielu producentów EEG)
- Środowisko docelowe: Windows 10/11, 64-bit (PyInstaller .exe)
- Brak dostępu do sieci w trakcie pracy (wymaganie prywatności)
- Baza norm: domyślny plik .json dostarczany z aplikacją; nadpisywalny przez użytkownika

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

---

## Open Questions

1. **Jaka jest dokładna reguła wyznaczania rekomendacji TAK/NIE?** — Macierz 25 wartości vs. norma. Próg: czy wystarczy 1 odchylenie z 25? Określona liczba? Odchylenia tylko w wybranych komórkach macierzy (kluczowe pary lokalizacja+pasmo)? Właściciel: użytkownik / ekspert domenowy. Blokuje: implementację FR-005 i treść raportu PDF. Do rozwiązania przed rozpoczęciem implementacji.

2. **Jak wybierany jest segment ~3 minut do analizy?** — Nagranie może być dłuższe niż 3 minuty. Opcje: (a) pełna automatyka — aplikacja wybiera najczystszy 3-minutowy segment po artefaktach; (b) manualne wskazanie startu przez użytkownika; (c) średnia z całego nagrania po usunięciu artefaktów. Właściciel: użytkownik (do dopytania). Wpływa na: złożoność FR-002 i czas przetwarzania.

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

