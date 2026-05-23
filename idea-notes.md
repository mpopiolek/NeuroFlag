# NeuroFlag - MVP ideas

### Główny problem
Tradycyjna diagnostyka neurorozwojowa dzieci jest skomplikowana i czasochłonna. Brakuje szybkiego narzędzia przesiewowego, które pozwalałoby na przebadanie dużej liczby dzieci przy użyciu dowolnego, istniejącego w placówkach sprzętu EEG/Biofeedback, bez konieczności wysyłania danych medycznych do sieci.

### Najmniejszy zestaw funkcjonalności (MVP)
- Lokalna aplikacja desktopowa (plik .exe dla systemu Windows) działająca w 100% offline
- Import plików .edf przez intuicyjne przeciągnięcie pliku do okna programu (Drag & Drop)
- Automatyczne usuwanie podstawowych artefaktów (ruch, bicie serca, sieć) przy użyciu naukowych bibliotek Pythona (np. SciPy / MNE-Python)
- Porównanie wyników z wbudowaną bazą norm odniesienia dla dzieci w wieku 6-10 lat (opartą na badaniach grupy 200 osób)
- Wizualna prezentacja odchyleń na wykresie profilowym (np. słupkowym) porównującym wynik badania z obszarem normy
- Opcjonalne zabezpieczenie dostępu do aplikacji lokalnym hasłem użytkownika w celu ochrony danych
- Generowanie raportu przesiewowego z informacją o konieczności (lub jej braku) skierowania dziecka do diagnozy wielospecjalistycznej
- Zapis raportu wraz z wykresem do pliku PDF na dysku lokalnym oraz opcja jego bezpośredniego wydruku
- Formularz konfiguracyjny umożliwiający administratorowi/badaczowi ręczną aktualizację bazy norm (np. poprzez podmianę pliku .json lub .xlsx)

### Co NIE wchodzi w zakres MVP (Rozbudowa w wersji 2.0+)
- Bezpośrednia integracja ze sprzętem EEG (brak nagrywania sygnału na żywo w aplikacji)
- Porównywanie wielu historycznych badań dziecka w czasie (wykresy trendów i postępów terapii)
- Centralna baza danych pacjentów w chmurze i system kont użytkowników (SaaS)
- Lokalny moduł gromadzenia statystyk neuroatypowości z funkcją jednorazowego eksportu/wysyłki e-mail do celów badawczych (wymaga wcześniejszego audytu RODO)
- Inteligentny asystent LLM (np. lokalna Llama) do automatycznego generowania opisów klinicznych dla lekarza oraz sekcji wyjaśniającej dla rodzica prozą
- Automatyczne dopasowywanie i pobieranie norm pod rynki zagraniczne z serwera

### Stos technologiczny (Rekomendowany)
- **Język:** Python 3.x
- **Interfejs użytkownika:** CustomTkinter lub Flet (nowoczesne okna desktopowe)
- **Analiza EEG:** PyEDFlib (odczyt plików) + SciPy / MNE-Python (matematyka i filtry)
- **Wykresy:** Matplotlib lub Plotly
- **Raporty PDF:** ReportLab lub FPDF2
- **Dystrybucja i budowanie:** PyInstaller (pakowanie do jednego pliku .exe)

### Kryteria sukcesu
- Procedura analizy wgranego pliku .edf i wygenerowania raportu PDF trwa do 10 minut na standardowym komputerze biurowym
- Aplikacja bezbłędnie i poprawnie interpretuje pliki .edf z minimum 3 różnych, popularnych aparatów EEG/Biofeedback dostępnych na rynku
- Użytkownicy (pedagodzy, psycholodzy) uruchamiają i obsługują aplikację na podstawie samej dołączonej instrukcji PDF, bez konieczności odbywania dodatkowych szkoleń
- Cały proces analizy i zapisu danych odbywa się lokalnie bez wywoływania błędów bezpieczeństwa Windows (przy wdrożeniu instrukcji uruchomienia dla testerów)