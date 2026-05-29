---
project: NeuroFlag
assessed_at: 2026-05-29T18:45:00+02:00
agent_readiness: ready-with-compensation
context_type: brownfield
stack_components:
  language: Python 3.11
  framework: FastAPI (current, replaced) → CustomTkinter or Flet (incoming desktop GUI)
  eeg_processing: MNE-Python
  pdf_generation: ReportLab
  build_tool: pip / requirements.txt (no version pins, no pyproject.toml)
  test_runner: pytest
  package_manager: pip
  ci_provider: GitHub Actions
  deployment_target: PyInstaller .exe (Windows 10/11 64-bit)
gates_passed: 3
gates_failed: 4
---

## Stack Components

**Kontekst oceny:** PRD (context/foundation/prd.md, context_type: brownfield) potwierdza pełną wymianę kodu — prototyp FastAPI jest zastępowany aplikacją desktopową. Poniższa ocena dotyczy **docelowego stosu** (incoming stack), który będzie budowany od zera, z uwzględnieniem komponentów zachowanych (Python, MNE-Python, ReportLab) i nowych (GUI, PyInstaller).

**Python 3.11** — język bazowy, zachowany. CI celuje w 3.11 (`.github/workflows/python-app.yml`), lokalnie działa 3.12/3.13 (`.pyc` w cache). Brak adnotacji typów i brak narzędzi do sprawdzania typów w `requirements.txt`.

**GUI: CustomTkinter lub Flet** — niezdecydowane (Forward: tech-stack). Oba są minimalistycznymi bibliotekami widgetów bez opinii o strukturze projektu. CustomTkinter jest dojrzalszy i popularniejszy w danych treningowych; Flet jest nowszy i mniej reprezentowany.

**MNE-Python** — biblioteka analizy EEG. Niszowa (neuroscience/scientific Python), ale z doskonałą dokumentacją (mne.tools) i silnymi konwencjami domenowymi (Raw → Epochs → pipeline). Zachowana z prototypu jako wiedza dziedzinowa.

**ReportLab** — generowanie PDF. Dojrzała, dobrze udokumentowana biblioteka Python z jasnym API. Obecna w `requirements.txt`.

**pip / requirements.txt** — zarządzanie zależnościami. Brak przypięcia wersji (wszystkie zależności bez `==X.Y.Z`), brak `pyproject.toml`, brak pliku lock. Ryzyko niedeterministycznych buildów.

**pytest** — test runner. Standardowy framework testowy Python. Skonfigurowany w CI.

**PyInstaller** — dystrybucja (.exe). Dobrze znany, ale złożony. Brak `.spec`, brak makefile, brak udokumentowanego powtarzalnego flow budowania.

---

## Quality Gate Assessment

| Komponent              | Typowany | Konwencje | Dane treningowe  | Dokumentacja | Wynik    |
|------------------------|----------|-----------|------------------|--------------|----------|
| Python (język)         | ✗        | —         | —                | —            | fail     |
| GUI (CTk / Flet)       | —        | ✗         | ~ (CTk ✓, Flet~) | ✓            | fail     |
| MNE-Python (EEG)       | —        | ✓         | ~ (niszowy)      | ✓            | pass     |
| ReportLab (PDF)        | —        | ✓         | ✓                | ✓            | pass     |
| pip / requirements.txt | —        | ✗         | ✓                | ✓            | fail     |
| pytest                 | —        | —         | ✓                | ✓            | pass     |
| PyInstaller (.exe)     | —        | ~         | ✓                | ~            | partial  |

Legenda: ✓ = zaliczone  ✗ = niezaliczone  ~ = częściowe  — = nie dotyczy

### Gate Details

**Bramka 1 — Typowany**

- **Python: NIEZALICZONE**
  - Dowód: `requirements.txt` — brak `mypy`, `pyright`, `ty`; `app/main.py` — żadna funkcja nie ma adnotacji typów (np. `async def upload_norm(file: UploadFile = File(...))` zamiast właściwego `-> JSONResponse`).
  - Konsekwencja dla agenta: agent generujący nowy kod bez typowania tworzy niesprawdzalny interfejs. Refaktoryzacje i zmiany sygnatur funkcji nie są wykrywane statycznie — każda zmiana wymaga ręcznego prześledzenia call chain.

**Bramka 2 — Oparta na konwencjach**

- **GUI (CustomTkinter / Flet): NIEZALICZONE**
  - Dowód: obie biblioteki to zestawy widgetów bez opinii o strukturze projektu. Brak udokumentowanego wzorca komponentów w AGENTS.md. Cały obecny kod aplikacji siedzi w jednym `app/main.py`.
  - Konsekwencja: agent budujący GUI bez wzorca struktury tworzy monolityczne pliki lub niespójne podziały.

- **pip / requirements.txt: NIEZALICZONE**
  - Dowód: `requirements.txt` zawiera `fastapi`, `mne`, `pytest` itd. — bez wersji. Brak `pyproject.toml`, brak `requirements-lock.txt`, brak `uv.lock`.
  - Konsekwencja: agent nie może wnioskować o kompatybilności zależności; `pip install` może wyprodukować inny środowisko niż CI.

- **MNE-Python: ZALICZONE** — silne konwencje: Raw object → preprocessing → Epochs → compute. Pipeline jest idiomatyczny i dobrze znany w danych treningowych.

- **ReportLab: ZALICZONE** — jasne API: Canvas → elements → save. Spójna między wersjami.

**Bramka 3 — Popularny w danych treningowych (ocena w ramach ekosystemu Python)**

- **Python: PASS** — fundamentalny język.
- **CustomTkinter: PASS** — popularny Python GUI toolkit z dużą liczbą tutoriali i przykładów.
- **Flet: PARTIAL** — nowszy (2022), rosnący, ale mniejsza reprezentacja w danych treningowych w porównaniu z CTk czy tkinter.
- **MNE-Python: PARTIAL** — niszowy (EEG/neuroscience), ale dobrze reprezentowany w naukowym Python. Agent może potrzebować więcej wskazówek dla zaawansowanych API (ICA, montaż elektrod, filtry pasmowe).
- **ReportLab: PASS** — dojrzała, szeroko używana.
- **pytest: PASS** — standardowy.
- **PyInstaller: PASS** — dobrze znany, dużo przykładów w sieci.

**Bramka 4 — Dobrze udokumentowany**

- **Python: PASS** — docs.python.org.
- **CustomTkinter: PASS** — customtkinter.tomschimaneck.de, aktywnie utrzymywana.
- **Flet: PASS** — flet.dev, kompletna dokumentacja.
- **MNE-Python: PASS** — mne.tools, doskonała dokumentacja z przykładami klinicznymi.
- **ReportLab: PASS** — reportlab.com + ReportLab User Guide.
- **pytest: PASS** — docs.pytest.org.
- **PyInstaller: PARTIAL** — pyinstaller.org, ale dokumentacja `.spec` jest fragmentaryczna dla złożonych przypadków (multiprocessing, MNE, hidden imports).

---

## Gaps & Compensation

### Gap 1 — Python bez typowania

**Dlaczego to ważne dla przepływów agenta:** Agent generujący funkcje bez typowania tworzy kod, którego sygnatury nie mogą być sprawdzone statycznie. Przy refaktoryzacji modułów (np. zmiana pipeline przetwarzania EEG) agent nie może wykryć, czy wywołanie funkcji jest nadal poprawne. W projekcie z 10 komponentami domenowymi (kombinacje lokalizacja×zadanie×pasmo, algorytm trójstanowy, metryczka pacjenta) brak typów oznacza więcej cykli korekcji na późniejszych etapach.

**Strategia kompensacji:**
- Dodaj `mypy` do `requirements.txt` i skonfiguruj w `pyproject.toml` lub `setup.cfg`
- Dodaj regułę do AGENTS.md (gotowy tekst poniżej)

### Gap 2 — GUI bez konwencji struktury

**Dlaczego to ważne:** Aplikacja desktopowa będzie miała co najmniej 5 widoków (metryczka dziecka, import pliku, analiza, siatka wyników, generowanie PDF) plus logikę domenową (pipeline EEG, algorytm norm) i warstwę konfiguracji (norms.json). Bez udokumentowanej struktury modułów agent będzie umieszczał kod w przypadkowych miejscach lub tworzy monolityczne pliki.

**Strategia kompensacji:** Udokumentuj strukturę katalogów docelowej aplikacji w AGENTS.md (gotowy tekst poniżej).

### Gap 3 — pip/requirements.txt bez pinowania wersji

**Dlaczego to ważne:** MNE-Python i SciPy mają zmieniające się API między wersjami (szczególnie API dla ICA, filtrów, obsługi kanałów). Nieprzypięte wersje mogą spowodować, że kod generowany przez agenta na podstawie starej dokumentacji przestaje działać przy nowym `pip install`.

**Strategia kompensacji:** Przypnij wersje i przejdź na `pyproject.toml` (gotowy tekst poniżej).

### Gap 4 — MNE-Python jest niszowy w danych treningowych

**Dlaczego to ważne:** Agent zna ogólne API MNE-Python, ale może nie znać specyficznych dla projektu idiomów (np. mapowanie kanałów systemu 10-20, obsługa znaczników EDF, filtrowanie pasmowe dla Delta/Theta/Beta). Bez przykładów domenowych agent może generować kod poprawny składniowo, ale niepoprawny klinicznie.

**Strategia kompensacji:** Dodaj sekcję MNE-Python do AGENTS.md z idiomami specyficznymi dla projektu (gotowy tekst poniżej).

### Gap 5 — PyInstaller bez udokumentowanego procesu budowania

**Dlaczego to ważne:** PyInstaller z MNE-Python, SciPy i CustomTkinter wymaga starannie skonfigurowanego `.spec` z hidden imports. Bez `.spec` i udokumentowanego przepływu każdy build może skończyć się inaczej. Agent nie może wygenerować poprawnego `.spec` bez wiedzy o strukturze projektu.

**Strategia kompensacji:** Dodaj sekcję build do AGENTS.md z wymaganiami `.spec` (gotowy tekst poniżej).

---

### Recommended Instruction File Additions

Poniższe bloki są gotowe do wklejenia do `AGENTS.md`. Zastąp istniejącą treść (która opisuje stary prototyp) lub dodaj jako nowe sekcje.

---

```markdown
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
```

---

```markdown
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
```

---

```markdown
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
```

---

```markdown
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
```

---

```markdown
## Build: PyInstaller (.exe)

Aplikacja dystrybuowana jako single-file .exe dla Windows 10/11 64-bit.

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
```

---

## Summary

**Projekt:** NeuroFlag  
**Gotowość agenta:** ready-with-compensation  
**Zaliczone bramki:** 3 / 7 komponentów (MNE-Python, ReportLab, pytest)

**Główne mocne strony:**
- Python to doskonały fundament dla kodu generowanego przez agenta — ogromna baza danych treningowych
- MNE-Python ma silne konwencje domenowe i doskonałą dokumentację — agent zna wzorzec Raw→Epochs→pipeline
- ReportLab i pytest są stabilne, dobrze udokumentowane i przewidywalne

**Główne luki (wszystkie z klarowną kompensacją):**
1. **Brak typowania** — krytyczne dla projektu z nietrywialną logiką domenową (algorytm trójstanowy, pipeline 10 kombinacji). Mypy + adnotacje typów od pierwszego commita.
2. **Brak konwencji GUI i struktury modułów** — ryzyko monolitycznych plików i niespójnych decyzji architektonicznych. Dodaj udokumentowaną strukturę katalogów do AGENTS.md przed napisaniem pierwszej linii kodu.
3. **Nieustrukturyzowane zarządzanie zależnościami** — pyproject.toml + przypięte wersje eliminują problem niedeterministycznych buildów z MNE-Python.
4. **PyInstaller bez .spec** — kompleksowy .spec z MNE-Python hidden imports jest wymagany. Dokumentuj go zanim zaczniesz budować.

**Zalecany następny krok:** `/10x-health-check`  
Audytuje zdrowie zależności, pokrycie testów i CI/CD w kontekście zidentyfikowanych luk. Skupi się na: braku pinowania wersji MNE-Python/SciPy, pokryciu testów domenowych (pipeline EEG, algorytm trójstanowy) i gotowości CI do buildu PyInstaller.
