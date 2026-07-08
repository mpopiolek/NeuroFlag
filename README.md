# NeuroFlag

Aplikacja desktopowa dla Windows do przesiewowej analizy sygnału EEG dzieci w wieku 6–10 lat.
Wczytuje pliki `.edf` / BrainVision `.vhdr`, porównuje wyniki z empiryczną bazą norm i zwraca
jedną z trzech kategorii: **Wskazanie do diagnozy / Uważna obserwacja / Brak wskazań**.

Działa w trybie w pełni offline — żadne dane nie opuszczają urządzenia.

> Wynik nie jest diagnozą medyczną. To narzędzie przesiewowe wskazujące potrzebę dalszej oceny klinicznej.

---

## Wymagania

- Windows 10 / 11, 64-bit
- Brak wymagań instalacji Pythona — aplikacja dystrybuowana jako `.exe`

---

## Uruchomienie (środowisko deweloperskie)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Uruchomienie aplikacji:

```powershell
python app/main.py
```

Testy i sprawdzenie typów:

```powershell
pytest -q
mypy app/ --strict
```

---

## Build (.exe)

```powershell
pyinstaller neuroflag.spec --clean
```

Artefakt: `dist\neuroflag\neuroflag.exe`

Przed przekazaniem placówce wykonaj smoke-test zgodnie z `context/foundation/distribution.md`.

---

## Struktura projektu

```
app/
  main.py              # Punkt wejścia GUI
  domain/              # Logika domenowa (pipeline EEG, algorytm, normy)
  ui/                  # Widoki i komponenty CustomTkinter
  reports/             # Generowanie PDF (ReportLab)
  config/              # Ustawienia, ścieżka norms.json
norms.json             # Baza norm (nadpisywalna)
tests/                 # Testy jednostkowe i integracyjne
neuroflag.spec         # Konfiguracja PyInstaller
pyproject.toml         # Zależności i konfiguracja narzędzi
```

---

## Dokumentacja projektu

- `context/foundation/prd.md` — wymagania produktowe
- `context/foundation/stack-assessment.md` — ocena stosu technologicznego
- `context/foundation/distribution.md` — procedura dystrybucji do placówek
- `AGENTS.md` — reguły dla agentów AI pracujących w projekcie

---

## Kontakt i wsparcie

### Konsultacje merytoryczne (EEG)

**dr Małgorzata Chojak** — Kierownik Laboratorium Badań nad Neuroedukacją UMCS  
tel. 508 216 957 · malgorzata.chojak@mail.umcs.pl

### Wsparcie techniczne

**Małgorzata Popiołek** — malgorzata.pe@gmail.com

### Zgłaszanie błędów (GitHub)

Problemy z aplikacją można zgłaszać w sekcji Issues:  
https://github.com/mpopiolek/NeuroFlag/issues

Analiza EEG w NeuroFlag odbywa się offline. Otwarcie strony GitHub wymaga połączenia z internetem.
