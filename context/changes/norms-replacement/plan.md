# S-04: Wymiana bazy norm — Implementation Plan

## Overview

S-04 uzupełnia FR-008 (podmiana `norms.json`) o trzy brakujące ogniwa:
(1) widoczny dialog błędu przy starcie aplikacji gdy `norms.json` jest niepoprawny lub
brakuje — bo `sys.exit()` w `.exe` bez okna konsoli jest niewidoczne dla użytkownika;
(2) tryb CLI `--validate-norms <path>` pozwalający administratorowi zweryfikować
własny plik przed wdrożeniem bez uruchamiania GUI;
(3) dokumentacja schematu (`norms.json.template` + `docs/README-norms.md`) eliminująca
frustrację przy ręcznej podmiance przez psychologa-administratora.

## Current State Analysis

> **Stan przed implementacją S-04 (historyczny).** Phase 1–2 adresują poniższe luki; po implementacji patrz sekcję Progress.

F-01 dostarczył kompletną logikę domenową:
- `app/domain/norms.py` — `load()` z pełną walidacją schematu; wszystkie ścieżki błędów
  owijają wyjątek jako `NormsLoadError` (w tym `FileNotFoundError` przez `except OSError`,
  `JSONDecodeError`, brakujące klucze, zła liczba norm, nieznane pasmo)
- `app/main.py` — łapie `NormsLoadError` i wywołuje `sys.exit(f"Błąd ładowania norm: {exc}")`
- `tests/unit/test_norms.py` — 7 scenariuszy `NormsLoadError` w tym `test_file_not_found`

Brakuje:
- Widocznego komunikatu błędu w środowisku bez konsoli (spakowany `.exe`)
- Trybu `--validate-norms <path>` w CLI
- Dokumentacji schematu i lokalizacji pliku dla administratora

### Key Discoveries

- `app/domain/norms.py:80-83` — `FileNotFoundError` jest już owinięty jako
  `NormsLoadError("Cannot read norms file '...': ...")` przez `except OSError` —
  norms.py nie wymaga zmian
- `tests/unit/test_norms.py:104-106` — `test_file_not_found` już istnieje —
  nie trzeba dodawać nowego testu w norms
- `app/main.py:12-16` — jedyny gap: `sys.exit(f"Błąd ładowania norm: {exc}")` zamiast
  `tkinter.messagebox.showerror()` — użytkownik nie widzi komunikatu w `.exe`
- `app/domain/norms.py:39-41` — `resolve_norms_path()` obecnie zwraca `_MEIPASS/norms.json`
  w trybie PyInstaller (`_internal/`), **nie** katalog obok `neuroflag.exe` — podmiana pliku
  zgodnie z `distribution.md` dziś nie działa; S-04 naprawia to przez exe-dir-first resolution
- `norms.json` — plik rootowy projektu jest bundlowany przez `neuroflag.spec:65-66`
  do root `.exe` jako `(str(ROOT / "norms.json"), ".")`; użytkownik podmienia plik
  w folderze `dist/neuroflag/` obok `neuroflag.exe`

## Desired End State

Po ukończeniu S-04:
1. Gdy `norms.json` brakuje lub jest niezgodny ze schematem — użytkownik widzi
   okno systemowe `tkinter.messagebox.showerror()` z polskim komunikatem błędu,
   a nie cichą śmierć aplikacji
2. `python app/main.py --validate-norms /ścieżka/do/norms.json` → wypisuje
   `OK: norms.json jest poprawny (version=1, 10 norm)` lub pełny opis błędu;
   exit code 0 / 1
3. `norms.json.template` — skomentowany plik gotowy do kopiowania przez administratora
4. `docs/README-norms.md` — instrukcja: gdzie umieścić plik, co znaczą pola,
   jak zwalidować przed wdrożeniem
5. `pytest -q` i `mypy app/ --strict` przechodzą bez błędów

Weryfikacja: `python app/main.py --validate-norms norms.json` → `OK: norms.json jest poprawny`

### Key Discoveries

- `tkinter` jest dostępne bez dodatkowej zależności (customtkinter bundluje tcl/tk);
  wzorzec dla error-before-CTk: `import tkinter; tkinter.Tk().withdraw(); tkinter.messagebox.showerror(...)`
- `--validate-norms` musi być sprawdzane PRZED `--smoke-test` w kolejności `sys.argv` —
  oba są trybami exit-only, oba działają headless

## What We're NOT Doing

- **Formularz UI do wprowadzania norm przez niedewelopera** — osobny slice po S-01 (backlog v2.0); S-04 naprawia podmianę pliku, nie UI edycji
- **Walidacja przez UI (dialog podmianki wewnątrz aplikacji)** — FR-008 decyzja: ręczna podmiana pliku
- **Automatyczne pobieranie norm z serwera** — PRD §Non-Goals
- **Różnicowanie norm wiekowo** — PRD §Non-Goals; v2.0
- **Zmian w `norms.json`** — plik bazowy jest poprawny i nie jest modyfikowany przez S-04

## Implementation Approach

Minimalne zmiany: naprawiamy `resolve_norms_path()` (exe-dir-first), modyfikujemy
`app/main.py` (dialog błędu + `--validate-norms`), bundlujemy artefakty docs w
`neuroflag.spec`, dodajemy pliki dokumentacji.
Kolejność: path resolution → main.py → testy CLI → dokumentacja + spec.

---

## Phase 1: Path resolution + dialog błędu + `--validate-norms` CLI

### Overview

Naprawia `resolve_norms_path()` tak, by podmiana `norms.json` obok `neuroflag.exe`
działała zgodnie z `distribution.md` i FR-008. Modyfikuje `app/main.py` tak, żeby
błędy ładowania norm były widoczne w GUI (messagebox zamiast `sys.exit()`) i dodaje
tryb `--validate-norms <path>`. Dodaje testy CLI przez subprocess oraz test path resolution.

### Changes Required

#### 1. Naprawa resolve_norms_path() — exe-dir-first

**File**: `app/domain/norms.py`

**Intent**: Umożliwić ręczną podmianę `norms.json` przez administratora w folderze
instalacyjnym (obok `neuroflag.exe`), zgodnie z `distribution.md` i FR-008.
Obecna implementacja czyta wyłącznie z `_MEIPASS` (`_internal/`), więc podmiana
pliku obok `.exe` jest ignorowana.

**Contract**: `resolve_norms_path()` zwraca:
- Dev (nie frozen): `Path(__file__).parent.parent.parent / "norms.json"`
- Frozen (PyInstaller): `Path(sys.executable).parent / "norms.json"` **jeśli plik istnieje**;
  w przeciwnym razie fallback `Path(sys._MEIPASS) / "norms.json"` (bundlowany default)

Wymaga importu `sys` (już obecny). Nie zmienia sygnatury publicznej `load()`.

#### 2. Test path resolution

**File**: `tests/unit/test_norms.py`

**Intent**: Zabezpieczyć kontrakt exe-dir-first przed regresją.

**Contract**: Nowy test `test_resolve_norms_path_prefers_exe_dir_when_frozen`:
mock `sys.frozen = True`, `sys.executable` wskazuje na `tmp_path/neuroflag.exe`,
plik `tmp_path/norms.json` istnieje → `resolve_norms_path()` zwraca `tmp_path/norms.json`.
Drugi przypadek: brak pliku obok exe → fallback na `_MEIPASS/norms.json`.

Opcjonalny test integracyjny `test_load_prefers_exe_dir_norms_when_frozen`:
gdy obok `.exe` i w `_MEIPASS` są różne pliki `norms.json`, `load()` bez `path=`
wczytuje wersję z katalogu `.exe`.

#### 3. Aktualizacja app/main.py

**File**: `app/main.py`

**Intent**: Zastąpić `sys.exit(f"Błąd ładowania norm: {exc}")` wywołaniem
`tkinter.messagebox.showerror()` — widoczne nawet bez okna konsoli.
Dodać obsługę `--validate-norms <path>`: wczytuje wskazany plik, wypisuje
wynik (OK lub opis błędu), kończy exit(0/1) bez uruchamiania GUI.

**Contract**:

```python
def format_norms_error_message(exc: NormsLoadError) -> str:
    """Pure function — testable without GUI."""
    return (
        f"Nie można wczytać pliku norms.json:\n\n{exc}\n\n"
        f"Sprawdź plik norms.json w folderze aplikacji\n"
        f"(obok neuroflag.exe) lub przywróć plik domyślny z norms.json.template."
    )

def _show_norms_error(message: str) -> None:
    """Show a visible error dialog before CTk init. Uses stdlib tkinter."""
    import tkinter
    import tkinter.messagebox
    root = tkinter.Tk()
    root.withdraw()
    tkinter.messagebox.showerror("NeuroFlag — Błąd konfiguracji", message)
    root.destroy()
```

W `main()` przy `NormsLoadError`: `_show_norms_error(format_norms_error_message(exc))`.

Reszta `main()` bez zmian strukturalnych (`--validate-norms`, `--smoke-test`, CTk).

`Path` musi być importowany (`from pathlib import Path`).
`_show_norms_error` nie importuje CTk — działa zawsze przed `ctk.CTk()`.

#### 4. Testy CLI --validate-norms

**File**: `tests/unit/test_main_cli.py`

**Intent**: Przetestować tryb `--validate-norms` przez subprocess (bez uruchamiania GUI),
pokrywając oba wyjścia: poprawny plik (exit 0) i niepoprawny (exit 1).

**Contract**:

```python
import subprocess, sys, json
from pathlib import Path
import pytest

def _run_validate(tmp_path: Path, payload: object) -> subprocess.CompletedProcess[str]:
    p = tmp_path / "norms.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "app.main", "--validate-norms", str(p)],
        capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent
    )
```

Testy:
- `test_validate_norms_valid`: poprawny payload → exit code 0, stdout zawiera "OK"
- `test_validate_norms_invalid_missing_key`: payload bez `"norms"` → exit code 1,
  stderr zawiera "BŁĄD"
- `test_validate_norms_file_not_found`: ścieżka do nieistniejącego pliku → exit code 1,
  stderr zawiera "BŁĄD"
- `test_validate_norms_missing_path_arg`: `--validate-norms` bez argumentu → exit code 2

#### 5. Test formatowania komunikatu błędu

**File**: `tests/unit/test_main_messages.py`

**Intent**: Przetestować treść komunikatu błędu bez uruchamiania tkinter GUI.

**Contract**: Test `format_norms_error_message(NormsLoadError("test"))` zawiera
`"norms.json"`, `"neuroflag.exe"` i `"norms.json.template"`.

### Success Criteria

#### Automated Verification

- `mypy app/ --strict --ignore-missing-imports` — 0 błędów
- `mypy app/main.py --strict --ignore-missing-imports` — 0 błędów
- `ruff check app/main.py app/domain/norms.py` — 0 błędów
- `pytest tests/unit/test_norms.py -q` — test path resolution zielony
- `pytest tests/unit/test_main_cli.py -q` — wszystkie 4 testy zielone
- `pytest tests/unit/test_main_messages.py -q` — test formatowania zielony
- `pytest -q` — brak regresji

#### Manual Verification

- `python app/main.py --validate-norms norms.json` → wypisuje `OK: norms.json jest poprawny (version=1, 10 norm)`
- `python app/main.py --validate-norms /nieistniejacy/plik.json` → wypisuje `BŁĄD: Cannot read...`, exit 1
- `python app/main.py --smoke-test` → exit 0 (brak regresji)

**Implementation Note**: Po przejściu automated verification i weryfikacji `--validate-norms` ręcznie, przejdź do Phase 2.

---

## Phase 2: Dokumentacja schematu dla administratora

### Overview

Tworzy `norms.json.template` (komentowany plik gotowy do kopiowania) i
`docs/README-norms.md` (kompletna instrukcja dla psychologa-administratora:
gdzie plik umieścić, co znaczą pola, jak zwalidować).

### Changes Required

#### 1. Szablon norms.json

**File**: `norms.json.template`

**Intent**: Dostarczyć komentowany plik referncyjny gotowy do skopiowania
i edycji przez administratora. Zawiera wszystkie wymagane pola z poprawnymi
wartościami oraz komentarze wyjaśniające znaczenie każdego klucza.

**Contract**: Plik JSON z wbudowaną dokumentacją jako klucz `"_comment"`:
- **dozwolony** na poziomie root (obok `version`, `norms`, …)
- **dozwolony wewnątrz** każdego wpisu pasma w `band_ranges` (np. `Delta._comment`)
- **zakazany** jako bezpośredni klucz w `band_ranges` obok `Delta`/`Theta`/… —
  `_parse_band_ranges()` iteruje wszystkie klucze i wymaga obiektu z `l_freq`/`h_freq`

Identyczna struktura jak `norms.json` z dodanymi polami `"_comment"`.
Walidator ignoruje extra keys — `_TOP_LEVEL_KEYS` wymaga tylko pięciu kluczy root.

#### 2. Instrukcja wymiany norm

**File**: `docs/README-norms.md`

**Intent**: Przewodnik krok-po-kroku dla psychologa-administratora: lokalizacja pliku
w folderze `.exe`, opis każdego pola schematu, instrukcja walidacji przez CLI,
sekcja FAQ z najczęstszymi błędami.

**Contract**: Dokument markdown z sekcjami:
1. "Gdzie znajduje się plik norms.json" — ścieżka `dist/neuroflag/norms.json`
   obok `neuroflag.exe`
2. "Jak wymienić bazę norm" — kroki: (a) skopiuj norms.json.template jako norms.json,
   (b) edytuj wartości, (c) zwaliduj przez `neuroflag.exe --validate-norms norms.json`,
   (d) uruchom aplikację
3. "Opis pól schematu" — tabelka: pole, typ, opis, przykład
4. "Najczęstsze błędy" — mapowanie komunikatów NormsLoadError na działanie naprawcze
5. "Nota o wersji v2.0" — planowany formularz UI do wprowadzania norm bez edycji JSON
   (osobny change po S-01, poza zakresem S-04)

#### 3. Bundling artefaktów docs w PyInstaller

**File**: `neuroflag.spec`

**Intent**: Placówka otrzymuje `norms.json.template` i `docs/README-norms.md` obok
`.exe` w artefakcie dystrybucyjnym — error dialog i instrukcja odsyłają do tych plików.

**Contract**: Rozszerzyć `datas` o:
- `(str(ROOT / "norms.json.template"), ".")`
- `(str(ROOT / "docs" / "README-norms.md"), "docs")`

Opcjonalnie: krok post-build w CI kopiuje domyślny `norms.json` obok `.exe`
(jeśli PyInstaller umieszcza go tylko w `_internal/`).

Zaktualizować `context/foundation/distribution.md` — sekcja artefaktu dystrybucyjnego
wymienia `norms.json.template` i `docs/README-norms.md`.

**CI contract (Windows build):** po `pyinstaller neuroflag.spec --clean` job CI
weryfikuje obecność `dist/neuroflag/norms.json.template` i
`dist/neuroflag/docs/README-norms.md` obok `.exe`. Jeśli PyInstaller 6 umieści
pliki w `_internal/`, krok post-build kopiuje je do root dystrybucji przed
asercją (patrz `.github/workflows/python-app.yml`).

### Success Criteria

#### Automated Verification

- `norms.json.template` jest poprawnym plikiem JSON: `python -c "import json; json.load(open('norms.json.template'))"`
- `python app/main.py --validate-norms norms.json.template` → exit 0, stdout "OK"
- Po `pyinstaller neuroflag.spec --clean`: pliki `dist/neuroflag/norms.json.template`
  i `dist/neuroflag/docs/README-norms.md` istnieją
- `pytest -q` — brak regresji

#### Manual Verification

- Przejrzyj `docs/README-norms.md`: czy administrator (osoba niedewelopera) zrozumiałby kroki bez dodatkowych szkoleń?
- Otwórz `norms.json.template` — czy komentarze wyjaśniają znaczenie każdego pola bez znajomości kodu?

**Implementation Note**: Po weryfikacji dokumentacji S-04 jest gotowy do code review i archiwizacji.

---

## Testing Strategy

### Unit Tests

- `tests/unit/test_main_cli.py` — 4 scenariusze `--validate-norms` przez subprocess
- `tests/unit/test_norms.py` — bez zmian (pełne pokrycie już istnieje w F-01)

### Integration Tests

Brak — walidacja pliku JSON jest testem domenowym, nie E2E.

### Manual Testing Steps

1. `python app/main.py --validate-norms norms.json` → "OK: norms.json jest poprawny (version=1, 10 norm)"
2. Usuń pole `"version"` z kopii norms.json, uruchom `--validate-norms` → "BŁĄD: norms.json missing required key 'version'"
3. Usuń `norms.json` z katalogu roboczego, uruchom `--validate-norms /brak/pliku.json` → "BŁĄD: Cannot read..."
4. `python app/main.py --validate-norms norms.json.template` → "OK" (template jest poprawnym norms.json)
5. `python app/main.py --smoke-test` → exit 0 (brak regresji)

## Performance Considerations

Brak — `norms.load()` to parsowanie jednego małego pliku JSON; brak implikacji wydajnościowych.

## Migration Notes

Brak. S-04 nie zmienia schematu `norms.json` — istniejący plik pozostaje bez zmian.

## References

- Roadmap: `context/foundation/roadmap.md` (S-04)
- PRD: `context/foundation/prd.md` (FR-008, §Scope of Change)
- F-01 plan: `context/changes/project-foundation/plan.md`
- Typy domenowe: `app/domain/types.py`
- Loader norm: `app/domain/norms.py`
- Spec bundling: `neuroflag.spec:65-66`

---

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Path resolution + dialog błędu + --validate-norms CLI

#### Automated

- [x] 1.1 `mypy app/ --strict --ignore-missing-imports` — 0 błędów
- [x] 1.2 `mypy app/main.py --strict --ignore-missing-imports` — 0 błędów
- [x] 1.3 `ruff check app/main.py app/domain/norms.py` — 0 błędów
- [x] 1.4 `pytest tests/unit/test_norms.py -q` — test path resolution zielony
- [x] 1.5 `pytest tests/unit/test_main_cli.py -q` — wszystkie 4 testy zielone
- [x] 1.6 `pytest tests/unit/test_main_messages.py -q` — test formatowania zielony
- [x] 1.7 `pytest -q` — brak regresji

#### Manual

- [x] 1.8 `python app/main.py --validate-norms norms.json` → stdout "OK: norms.json jest poprawny (version=1, 10 norm)"
- [x] 1.9 `python app/main.py --validate-norms /nieistniejacy/plik.json` → stderr "BŁĄD", exit 1
- [x] 1.10 `python app/main.py --smoke-test` → exit 0 (brak regresji)

### Phase 2: Dokumentacja schematu dla administratora

#### Automated

- [x] 2.1 `python -c "import json; json.load(open('norms.json.template'))"` — plik jest poprawnym JSON
- [x] 2.2 `python app/main.py --validate-norms norms.json.template` → exit 0, stdout "OK"
- [ ] 2.3 Po buildzie PyInstaller: `norms.json.template` i `docs/README-norms.md` istnieją w `dist/neuroflag/`
- [x] 2.4 `pytest -q` — brak regresji

#### Manual

- [ ] 2.5 `docs/README-norms.md` jest zrozumiały dla osoby niedewelopera bez dodatkowych szkoleń
- [ ] 2.6 `norms.json.template` zawiera komentarze wyjaśniające każde pole schematu
