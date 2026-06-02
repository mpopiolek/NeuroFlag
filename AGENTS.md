# AGENTS.md

NeuroFlag to aplikacja desktopowa dla Windows (Python), która analizuje pliki EEG (.edf / BrainVision .vhdr) i generuje wynik przesiewowy dla dzieci w wieku 6–10 lat. Nie ma bazy danych, nie ma połączeń sieciowych, nie ma Docker. Dystrybuowana jako single-dir `.exe` (PyInstaller).

---

## Kluczowe reguły domenowe

- Surowe wartości µV **nigdy** nie są widoczne dla użytkownika — tylko kolory RAG i kategoria wynikowa
- UI i komunikaty są w języku polskim
- > ⚠️ Prototyp webowy (FastAPI) jest zastępowany w całości. Stare komendy uvicorn / curl są nieaktualne.
- Python 3.11 w CI (`.github/workflows/python-app.yml`); lokalnie działa 3.12+
- Biblioteka `mne` jest najcięższą zależnością (najdłuższy czas instalacji)
- Cała logika domenowa opisana w `context/foundation/prd.md` i `context/foundation/stack-assessment.md`

---

## Typowanie i sprawdzanie typów

Cały nowy kod Pythona musi zawierać adnotacje typów na granicach funkcji i metod.
Użyj `from __future__ import annotations` dla forward references.

Uruchom przed commitem:
  mypy app/ --strict

Przykłady wymaganych adnotacji:
  - Funkcje: `def process_signal(raw: mne.io.BaseRaw, config: NormsConfig) -> AnalysisResult:`
  - Dataclasses: użyj `@dataclass` z typowanymi polami zamiast dict
  - Typy domenowe: zdefiniuj `AnalysisResult`, `PatientMetadata`, `NormsConfig` jako dataclasses
    w `app/domain/types.py` — agent powinien je importować, nie tworzyć ad hoc

Nigdy nie używaj `Any` bez wyraźnego komentarza `# type: ignore[<kod>]` z uzasadnieniem.

---

## MNE-Python — idiomy specyficzne dla projektu

Projekt używa MNE-Python do analizy EEG. Kluczowe konwencje:

Ładowanie pliku (obsługiwane formaty):
  raw_edf  = mne.io.read_raw_edf(path, preload=True, verbose=False)
  raw_bv   = mne.io.read_raw_brainvision(vhdr_path, preload=True, verbose=False)

Selekcja kanałów domenowych (ZAWSZE przed przetwarzaniem):
  raw.pick(['C3', 'O1'])  # system 10-20; wyklucz EOG/ECG/EMG przez pick_types()

Znaczniki zadań (mapowanie na segmenty):
  events, event_id = mne.events_from_annotations(raw)
  # Szukaj: 'OO' (oczy otwarte), 'OZ' (oczy zamknięte), 'ZP' (zadanie pamięciowe)
  # Fallback jeśli brak znaczników: dziel na segmenty co 180 s (3 minuty)

Usuwanie zakłóceń sieciowych:
  raw.notch_filter(freqs=config.power_line_frequency)  # domyślnie 50 Hz

Obliczanie pasma (przykład dla Theta 4–8 Hz):
  raw_theta = raw.copy().filter(l_freq=4.0, h_freq=8.0)
  # Nie hardkoduj wartości pasm — ładuj z norms.json (config.band_ranges["Theta"])

Jednostka wynikowa: µV (mikrowolty).
  data_uv = raw.get_data(units='uV')  # zawsze konwertuj do µV przed obliczeniami

Agent NIE wyświetla surowych wartości µV użytkownikowi — tylko kolory RAG i kategorię.

---

## Struktura katalogów aplikacji desktopowej

Docelowa struktura projektu (aplikacja desktopowa, nie serwer webowy):

  app/
    main.py              # Punkt wejścia — inicjalizacja GUI, ładowanie config
    domain/
      types.py           # Typy domenowe: PatientMetadata, AnalysisResult, NormsConfig
      norms.py           # Ładowanie i walidacja norms.json
      pipeline.py        # Pipeline EEG: segment detection → channel select → artifact removal → compute
      algorithm.py       # Algorytm trójstanowy: 10 wartości → Wskazanie / Obserwacja / Brak
    ui/
      views/
        metadata_form.py # Widok: formularz metryki dziecka
        file_import.py   # Widok: import pliku .edf / .vhdr
        analysis.py      # Widok: progress i wyniki analizy
        results_grid.py  # Widok: siatka 10 kolorowych komórek + kategoria
      components/        # Wielokrotnie używane widgety (przyciski, pola, kolory RAG)
      app_window.py      # Główne okno CTk/Flet — routing między widokami
    reports/
      pdf_generator.py   # Generowanie raportu PDF (ReportLab)
    config/
      settings.py        # Opcjonalne hasło startowe, ścieżka norms.json
  norms.json             # Domyślna baza norm (10 kombinacji, Z i K, pasma)
  tests/
    unit/                # Testy domenowe (pipeline, algorytm, ładowanie norm)
    integration/         # Testy E2E: pełny flow z przykładowym plikiem .edf

Agent zawsze umieszcza nowy kod w odpowiednim module domenowym.
Nie twórz `utils.py` ani `helpers.py` — funkcje trafiają do modułu według roli.

---

## Zarządzanie zależnościami

Projekt używa pyproject.toml (PEP 517/518). NIE modyfikuj requirements.txt bezpośrednio.

Wersje są przypięte:
  customtkinter==5.2.2     # lub flet==0.24.x — zdecydować przed startem
  mne==1.8.0
  scipy==1.14.1
  numpy==2.2.0
  reportlab==4.2.5
  pytest==8.3.4
  mypy==1.13.0

Przy dodawaniu nowej zależności:
  1. Dodaj do pyproject.toml [project.dependencies] z przypiętą wersją
  2. Uruchom: pip-compile pyproject.toml -o requirements.txt
  3. Zaktualizuj sekcję "Zależności" w tym pliku z krótkim uzasadnieniem wyboru wersji

---

## Build: PyInstaller (.exe)

Aplikacja dystrybuowana jako single-dir .exe dla Windows 10/11 64-bit.

Plik spec: `neuroflag.spec` w root projektu.
Build command: `pyinstaller neuroflag.spec --clean`

Wymagane hidden imports w .spec (MNE-Python + SciPy mają ukryte zależności):
  hiddenimports=['mne', 'scipy.signal', 'scipy.linalg', 'sklearn.utils._cython_blas',
                 'reportlab.graphics', 'customtkinter']

Dane do dołączenia (.spec datas):
  - norms.json         → dołącz do root .exe
  - app/ui/assets/     → ikony, czcionki

Testowanie buildu (uruchom po każdej zmianie deps):
  dist/neuroflag/neuroflag.exe --smoke-test
  # Sprawdź: okno otwiera się, norms.json ładuje się, plik .edf można wczytać

Agent modyfikuje .spec przy dodaniu nowych zależności domenowych.
Agent NIE używa --onefile dla MNE-Python (zbyt długi czas startu) — używa --onedir.

---

## Uruchamianie i testy

- **Testy:** `python -m pytest -q` (zalecane na Windows, gdy `pytest` nie jest w PATH; alias `pytest -q` działa po aktywacji venv z `Scripts` w PATH)
- **Build .exe:** `pyinstaller neuroflag.spec --clean` (plik `.spec` tworzony w trakcie implementacji)
- Brak serwera deweloperskiego — aplikacja uruchamia się jako okno GUI
