---
project: NeuroFlag
created_at: 2026-05-29
context_type: desktop-distribution
deployment_target: Windows 10/11 64-bit
distribution_method: manual-file-transfer
network_requirement: none
---

## Dystrybucja aplikacji NeuroFlag

NeuroFlag dystrybuowana jest jako katalog `.exe` zbudowany przez PyInstaller (`--onedir`).
Aplikacja jest w pełni samowystarczalna — nie wymaga instalacji Pythona, sieci ani dodatkowego oprogramowania.

---

## Artefakt dystrybucyjny

Po komendzie `pyinstaller neuroflag.spec --clean` powstaje:

```
dist/
  neuroflag/
    neuroflag.exe       ← punkt wejścia (uruchamia GUI)
    norms.json          ← baza norm, nadpisywalna przez użytkownika
    norms.json.template ← wzór schematu z komentarzami (informacyjny)
    docs/
      README-norms.md   ← instrukcja wymiany norm dla administratora
    _internal/          ← biblioteki Python (mne, scipy, numpy itd.)
```

Cały katalog `dist/neuroflag/` jest artefaktem do przekazania placówce.
Nie przenosi się samego pliku `.exe` bez katalogu `_internal/`.

---

## Wersjonowanie

Format wersji: `MAJOR.MINOR.PATCH` (np. `1.0.0`).

Wersja jest przechowywana w dwóch miejscach jednocześnie:

| Miejsce | Pole | Przykład |
|---|---|---|
| `pyproject.toml` | `[project] version` | `version = "1.0.0"` |
| `app/main.py` | stała `APP_VERSION` | `APP_VERSION = "1.0.0"` |

`APP_VERSION` jest wyświetlana w pasku tytułu okna i stopce raportu PDF.
Przed każdym buildem dystrybucyjnym należy zsynchronizować obie wartości.

Nazwa archiwum przekazywanego placówce:

```
neuroflag-<wersja>-win64.zip
```

Przykład: `neuroflag-1.0.0-win64.zip` zawiera spakowany katalog `dist/neuroflag/`.

---

## Przekazanie placówce

NeuroFlag nie ma mechanizmu automatycznych aktualizacji (brak sieci w trakcie pracy).
Nowa wersja jest przekazywana ręcznie jedną z poniższych metod:

1. **Pendrive** — skopiuj archiwum `.zip` na pendrive, rozpakuj na komputerze placówki.
2. **E-mail / Teams / dysk sieciowy placówki** — wyślij archiwum `.zip`; odbiorca rozpakowuje lokalnie.
3. **Sieć lokalna placówki** — udostępnij archiwum przez udział sieciowy (SMB); placówka pobiera sama.

Procedura instalacji po stronie placówki:
1. Rozpakuj archiwum do wybranego folderu (np. `C:\Programy\NeuroFlag\`).
2. Utwórz skrót do `neuroflag.exe` na pulpicie.
3. Uruchom `neuroflag.exe` — pierwsze uruchomienie weryfikuje, że `norms.json` się ładuje.

Nie jest wymagane uruchamianie jako administrator, chyba że folder docelowy jest chroniony (np. `C:\Program Files\`). Rekomendowany folder: `C:\Programy\NeuroFlag\` lub katalog domowy użytkownika.

---

## Aktualizacja bazy norm (`norms.json`)

Ekspert domenowy może zaktualizować normy bez rebuildu aplikacji:

1. Przygotuj nowy plik `norms.json` zgodny ze schematem (patrz `context/foundation/prd.md` — sekcja Business Logic Changes).
2. Przekaż plik placówce (e-mail, pendrive).
3. Placówka zastępuje plik `norms.json` w folderze instalacyjnym (obok `neuroflag.exe`).
4. Następne uruchomienie aplikacji wczytuje nowe normy automatycznie.

Aplikacja waliduje `norms.json` przy starcie. Jeśli plik jest uszkodzony lub niezgodny ze schematem — wyświetla komunikat błędu i nie uruchamia analizy.

---

## Smoke-test po każdym buildzie

Przed przekazaniem placówce wykonaj ręczny smoke-test na czystej maszynie Windows (lub maszynie wirtualnej bez Pythona):

```
Checklist smoke-test:
[ ] neuroflag.exe uruchamia się bez komunikatów błędów systemu Windows
[ ] Okno GUI otwiera się i wyświetla formularz metryki dziecka
[ ] norms.json ładuje się (brak komunikatu błędu przy starcie)
[ ] Możliwe jest wczytanie przykładowego pliku .edf lub .vhdr
[ ] Analiza uruchamia się i zwraca wynik (siatka kolorów + kategoria)
[ ] Raport PDF generuje się i zapisuje na dysk
[ ] Aplikacja nie wywołuje połączeń sieciowych (zweryfikuj Monitorem zasobów)
```

---

## Obsługa błędów bezpieczeństwa Windows

PyInstaller `.exe` może być blokowany przez Windows SmartScreen (nieznany wydawca).

Obejście dla placówki (opisane w instrukcji PDF):
1. Kliknij „Więcej informacji" w oknie SmartScreen.
2. Kliknij „Uruchom mimo to".

Opcjonalnie (dla oficjalnych wydań): podpisz `.exe` certyfikatem code-signing.
Narzędzie: `signtool.exe` (Windows SDK). Certyfikat: EV Code Signing (koszt ~300–500 USD/rok).
Dla MVP podpisywanie nie jest wymagane — obejście SmartScreen jest wystarczające.

---

## Rejestr wydań

| Wersja | Data | Zmiany | Przekazana placówce |
|---|---|---|---|
| 0.1.0 | — | Pierwsze wydanie (MVP) | — |

Aktualizuj tę tabelę przy każdym przekazaniu nowej wersji placówce.
