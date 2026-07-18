# Opcjonalne hasło startowe (FR-009) — Implementation Plan

## Overview

Domyknięcie FR-009: opcjonalne hasło startowe jako warstwa psychologicznej ochrony
dostępu do aplikacji desktopowej (jeden użytkownik na urządzenie). Hasło przechowywane
lokalnie jako hash w `settings.json`; przy starcie — bramka przed `AppWindow`;
zarządzanie (ustaw / zmień / wyłącz) z ekranu Informacje.

## Current State Analysis

- `app/config/settings.py` **nie istnieje** — slot opisany w `AGENTS.md` i
  `stack-assessment.md`, pakiet `app/config/` nie został jeszcze utworzony.
- Boot (`app/main.py:69-103`): `norms.load()` → wczesne wyjście `--smoke-test` →
  `AppWindow` → `MetadataFormView`. Brak jakiejkolwiek bramki auth.
- Lokalne pliki obok exe: `norms.json` (`resolve_norms_path`), `history.db`
  (`resolve_history_db_path` w `app/storage/history.py:52-56`) — wzorzec ścieżki
  dla nowego `settings.json`.
- Informacje: `InfoView` + `build_info_content` (`app/ui/components/info_dialog.py`)
  buduje karty sekcji (`_section_card`); brak sekcji hasła.
- Dialogi modalne: `CTkToplevel` + `grab_set` (np. `_EditStudyDialog` w
  `app/ui/views/history.py`, `ChannelMappingDialog`) — wzorzec UI dla odblokowania
  i zarządzania hasłem.
- Brak użycia `hashlib` / `secrets` / pól `show="*"` w repo — greenfield dla crypto i
  entry hasła.
- Roadmap parkował FR-009 post-MVP; ta zmiana świadomie go wyciąga jako jedyną lukę
  techniczną minimalnego paska.

## Desired End State

1. Gdy hasło **nie** jest ustawione — aplikacja startuje jak dziś (bez dodatkowego UI).
2. Gdy hasło **jest** ustawione — przed `AppWindow` pojawia się ekran odblokowania;
   poprawne hasło otwiera aplikację; błędne pokazuje komunikat i pozwala ponowić;
   zamknięcie okna kończy proces.
3. Z Informacji użytkownik może **ustawić**, **zmienić** (po podaniu obecnego) i
   **wyłączyć** hasło (po podaniu obecnego).
4. Na dysku tylko hash + salt (+ parametry KDF) w `settings.json` obok exe / w root
   projektu w dev — nigdy plaintext.
5. `--smoke-test` i `--validate-norms` nadal wychodzą bez GUI / bez bramki hasła.
6. Unit testy pokrywają settings (path, hash verify, clear) oraz logikę „czy wymaga
   odblokowania” / skip przy braku hasła.

Weryfikacja: ustaw hasło → restart wymaga hasła → Informacje → wyłącz → restart bez bramki.

### Key Discoveries:

- Hook bramki: po `if smoke_test: sys.exit(0)` (`main.py:87-88`), przed
  `AppWindow(...)` (`main.py:94-98`) — inaczej CI/`--smoke-test` złamie się.
- Writable config: kopiuj `resolve_history_db_path`, nie `resolve_norms_path`
  (norms ma fallback `_MEIPASS`; settings musi być zawsze zapisywalne obok exe).
- Zarządzanie hasłem: karta w `build_info_content` + `CTkToplevel` — bez przebudowy
  Informacji; pola hasła nie na głównym scrollu.
- Stdlib wystarczy: `hashlib.pbkdf2_hmac` + `secrets.token_hex` / `token_bytes` —
  zero nowych zależności w `pyproject.toml`.

## What We're NOT Doing

- Szyfrowanie plików EEG, `history.db` ani `norms.json` (v2.0 / PRD).
- Konta użytkowników, role, multi-user, remote auth.
- Rate-limit / lockout po N próbach (restart procesu i tak omija).
- Odzyskiwanie hasła e-mailem / pytaniem pomocniczym — reset = wyłączenie przez UI
  (ze starym hasłem) albo ręczne usunięcie / edycja `settings.json`.
- Hasło w tabeli SQLite `settings` w `history.db` (osobny plik JSON).
- Pełne E2E CTk dla odblokowania w CI.
- Opcjonalne hasło do poszczególnych funkcji (PDF, historia) — tylko start aplikacji.

## Implementation Approach

Trzy fazy bottom-up: najpierw czysta domena settings + testy, potem bramka startowa
(zależna od API settings), na końcu UI zarządzania w Informacjach.

Persystencja: JSON `{ "password_hash": "...", "salt": "...", "iterations": N }`
(lub równoważny, spójny schemat). Brak pliku / brak pól hasła = hasło wyłączone.

UI odblokowania: tymczasowy root CTk (theme przez `apply_app_theme`) **przed**
`AppWindow` — UI unlock na root lub `CTkToplevel` + `wait_window` / synchroniczny
wynik. Po sukcesie: kontrolowane zamknięcie root unlock, potem utwórz `AppWindow`
jak dziś. Po anulowaniu/zamknięciu: `sys.exit(0)`. Nie tworzyć dwóch żywych
`CTk()` jednocześnie; unikać „destroy default root → od razu nowy CTk” bez
sprawdzenia (klasyczne ryzyko Tk). Nie otwierać `AppWindow` (ani HistoryStore)
przed sukcesem odblokowania.

## Critical Implementation Details

- **Timing & lifecycle**: bramka wyłącznie na ścieżce GUI po udanym `norms.load()` i
  po early-exit `--smoke-test`. Nie otwierać `HistoryStore` / `AppWindow` przed
  sukcesem odblokowania (lub gdy hasło wyłączone).
- **User experience**: copy PL; tytuł w stylu „NeuroFlag — Odblokuj”; błędne hasło =
  komunikat przy polu / messagebox + ponowna próba; zamknięcie okna odblokowania =
  `sys.exit(0)` (lub równoważne czyste wyjście). Przy zmianie/wyłączeniu w Informacjach
  zawsze wymagać aktualnego hasła.
- **State sequencing**: po ustawieniu hasła w Informacjach kolejne uruchomienie musi
  wymagać bramki — bez osobnego „włącznika” poza samym zapisem hash.

---

## Phase 1: Settings domain — `app/config/settings.py`

### Overview

Pakiet `app/config/` z API odczytu/zapisu i weryfikacji hasła (hash PBKDF2 + salt).
Brak UI — czysta logika + unit testy.

### Changes Required:

#### 1. Utwórz pakiet `app/config/`

**File**: `app/config/__init__.py`

**Intent**: Zainicjować pakiet konfiguracji aplikacji (wzorzec jak `app/storage/`).

**Contract**: Pusty lub re-eksport publicznych symboli z `settings` (opcjonalnie).

#### 2. Moduł settings

**File**: `app/config/settings.py`

**Intent**: Lokalna persystencja opcjonalnego hasła startowego — resolve path,
load/save JSON, ustawianie/weryfikacja/czyszczenie hasła przez PBKDF2.
Nie mylić z tabelą SQLite `settings` w `history.db` (`HistoryStore`) — hasło
żyje wyłącznie w `settings.json`, nie w bazie historii.

**Contract**:
- `resolve_settings_path() -> Path` — frozen: `Path(sys.executable).parent / "settings.json"`;
  dev: project root / `settings.json` (jak `resolve_history_db_path`).
- Publiczne API (nazwy mogą być drobno dostosowane, semantika stała):
  - `is_password_enabled(path: Path | None = None) -> bool`
  - `set_password(password: str, path: Path | None = None) -> None`
  - `verify_password(password: str, path: Path | None = None) -> bool`
  - `clear_password(path: Path | None = None) -> None`
- Na dysku wyłącznie hash + salt + iterations (stdlib `hashlib.pbkdf2_hmac`,
  sól z `secrets`). Plaintext nigdy nie trafia do pliku.
- Brak pliku / uszkodzony / brak pól hasła → traktuj jako „hasło wyłączone”
  (`is_password_enabled` False; `verify` False gdy włączone i hasło złe).
- Adnotacje typów; `from __future__ import annotations`; bez `Any` bez justification.

#### 3. Unit testy settings

**File**: `tests/unit/test_settings.py`

**Intent**: Pokryć path (dev + frozen via monkeypatch), set→verify OK/źle, clear,
brak pliku = wyłączone.

**Contract**: Testy używają `tmp_path` jako ścieżki settings (nie piszą do realnego
`settings.json` w root). Wzorzec frozen jak `tests/unit/test_history.py` /
`test_norms.py`.

#### 4. Ignoruj lokalny plik hasła w git

**File**: `.gitignore`

**Intent**: Zapobiec przypadkowemu commitowi `settings.json` z hash/salt z root
projektu w trakcie developmentu.

**Contract**: Dodaj wpis `settings.json` (root / dowolna lokalizacja wg konwencji
repo — wystarczy wzorzec pliku jak dla innych lokalnych artefaktów). Testy nadal
piszą wyłącznie do `tmp_path`.

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/test_settings.py -q` przechodzi
- `mypy app/config --strict` przechodzi (lub `mypy app/ --strict` bez nowych błędów w tym pakiecie)

#### Manual Verification:

- Po ręcznym `set_password` w REPL / krótkim skrypcie plik `settings.json` zawiera
  hash/salt, nie plaintext hasła

**Implementation Note**: Po tej fazie pauza na potwierdzenie manualne przed Phase 2.

---

## Phase 2: Unlock gate — bramka przed `AppWindow`

### Overview

Ekran odblokowania + wiring w `main.py`. Gdy hasło wyłączone — zero zmian w UX startu.
`--smoke-test` pozostaje bez GUI.

### Changes Required:

#### 1. Widok / dialog odblokowania

**File**: nowy moduł UI, np. `app/ui/unlock_dialog.py` (lub równoważna lokalizacja
w `app/ui/`, nie `utils.py`)

**Intent**: Małe okno CTk z polem hasła (`show="*"`), przyciskiem odblokowania i
obsługą zamknięcia = wyjście z aplikacji; weryfikacja przez API settings.

**Contract**:
- Wywołanie synchroniczne z `main` (np. funkcja `prompt_unlock() -> bool` —
  True = kontynuuj do `AppWindow`, False = caller robi `sys.exit`).
- Lifecycle: jeden tymczasowy root CTk na czas bramki; po `True` zamknij go
  zanim powstanie `AppWindow` (żaden moment z dwoma żywymi rootami). Jeśli
  destroy→create okaże się niestabilne na CTk w spike’u Phase 2 — dopuszczalny
  wariant: reuse tego samego root jako `AppWindow` tylko gdy API na to pozwala
  bez otwierania HistoryStore przed verify; domyślnie preferuj osobny AppWindow
  po czystym zamknięciu unlock root.
- Theme: `apply_app_theme()` przed utworzeniem okna unlock (AppWindow i tak
  wywoła ponownie — idempotentne).
- Copy PL: tytuł w stylu „NeuroFlag — Odblokuj”; komunikat przy złym haśle;
  ponowna próba bez limitu.
- Nie tworzyć `AppWindow` ani nie otwierać `HistoryStore` wewnątrz dialogu.

#### 2. Wiring w `main.py`

**File**: `app/main.py`

**Intent**: Jeśli hasło włączone — pokaż bramkę po smoke-test exit, przed
`AppWindow`; przy niepowodzeniu/anulowaniu zakończ proces.

**Contract**:
- Kolejność: `norms.load()` → smoke early-exit → (opcjonalnie unlock) → `AppWindow`…
- Gdy `not is_password_enabled()`: pomiń bramkę (zachowanie jak dziś).
- Wydziel czystą funkcję pomocniczą do testów, np. `should_prompt_unlock() -> bool`
  (owijka nad `is_password_enabled`), aby uniknąć pełnego E2E CTk w CI.

#### 3. Testy bramki (logika, bez pełnego GUI)

**File**: `tests/unit/test_main_cli.py` i/lub `tests/unit/test_unlock.py`

**Intent**: Utrwalić: brak hasła → brak promptu; hasło ustawione → `should_prompt_unlock`
True; smoke-test nadal wychodzi 0 bez okna (istniejący kontrakt CI).

**Contract**: Unit na helperach; nie wymagać interakcji CTk w pytest. Smoke-test
path nie może wywoływać dialogu odblokowania.

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/test_settings.py tests/unit/test_main_cli.py -q` przechodzi
  (oraz nowe testy unlock helperów, jeśli w osobnym pliku)
- `mypy app/main.py app/config app/ui/unlock_dialog.py --strict` (dostosuj ścieżki do
  faktycznych plików) — bez nowych błędów

#### Manual Verification:

- Z ustawionym hasłem: start aplikacji pokazuje odblokowanie; złe hasło → komunikat + retry;
  dobre → MetadataForm jak dziś
- Zamknięcie okna odblokowania kończy aplikację (brak `AppWindow` w tle)
- Bez hasła: start bez bramki
- `python -m app.main --smoke-test` kończy się 0 bez okna

**Implementation Note**: Pauza na manual QA przed Phase 3.

---

## Phase 3: Password management UI — Informacje

### Overview

Sekcja „Hasło startowe” w Informacjach + dialog ustaw / zmień / wyłącz z weryfikacją
obecnego hasła przy zmianie i wyłączeniu.

### Changes Required:

#### 1. Karta w Informacjach

**File**: `app/ui/components/info_dialog.py` (ew. mały helper w sąsiednim module UI)

**Intent**: Dodać sekcję „Hasło startowe” (status włączone/wyłączone + przycisk
otwierający dialog zarządzania) bez przebudowy reszty Informacji.

**Contract**:
- Nowa `_section_card(..., "Hasło startowe")` — preferowane miejsce: po „Problemy z
  aplikacją” (koniec scrolla).
- Status tekstowy PL odzwierciedla `is_password_enabled()` — trzymaj uchwyt do
  `CTkLabel` (lub równoważnego) statusu, żeby dało się go zaktualizować bez
  przebudowy całego Informacji.
- CTA otwiera dialog (nie inline formularz na scrollu).
- **Nie** polegać na `open_info()` do odświeżenia — gdy użytkownik już jest na
  `InfoView`, `open_info` robi early-return i nie przebuduje treści.

#### 2. Dialog zarządzania hasłem

**File**: np. `app/ui/password_settings_dialog.py` (lub w tym samym module co unlock,
jeśli spójne)

**Intent**: Umożliwić ustawienie (gdy wyłączone), zmianę i wyłączenie (gdy włączone)
z wymogiem aktualnego hasła przy zmianie/wyłączeniu.

**Contract**:
- Wzorzec `CTkToplevel` + `grab_set` + `primary_button` / `secondary_button`.
- Pola `CTkEntry(show="*")`; walidacja: puste hasło przy ustawieniu = błąd PL.
- Po sukcesie: zapis przez API settings; odśwież status na karcie przez **callback**
  przekazany do dialogu (np. `on_password_changed: Callable[[], None]`), który
  ustawia tekst labela statusu z `is_password_enabled()` — bez `show_view` /
  `open_info` i bez restartu aplikacji.
- Wyłączenie: `clear_password()` dopiero po `verify_password(current)`.

#### 3. Testy regresji copy / smoke (opcjonalnie minimalne)

**File**: istniejące testy info jeśli pokrywają strukturę; w przeciwnym razie ogranicz
się do unit settings już z Phase 1 + manual UI.

**Intent**: Nie budować kruchego E2E CTk; ewentualnie asercja że builder Informacji
nie crashuje przy wywołaniu z mockiem (tylko jeśli tani i zgodny z obecnym stylem).

**Contract**: Brak obowiązku nowych GUI unit testów, jeśli projekt ich unika —
manual Verification poniżej jest źródłem prawdy dla Phase 3 UI.

### Success Criteria:

#### Automated Verification:

- `python -m pytest -q` (pełny suite) przechodzi
- `mypy app/ --strict` przechodzi

#### Manual Verification:

- Informacje → Hasło startowe: ustaw hasło → status „włączone” → restart wymaga hasła
- Zmiana hasła (stare + nowe) działa; stare nie przechodzi bramki, nowe tak
- Wyłączenie (z obecnym hasłem) → status „wyłączone” → restart bez bramki
- Próba zmiany/wyłączenia ze złym obecnym hasłem — komunikat błędu, stan bez zmian

**Implementation Note**: Po Phase 3 — ręczna regresja ścieżki analizy (Metadata → …)
bez regresji; hasło nie wpływa na pipeline ani historię.

---

## Testing Strategy

### Unit Tests:

- `resolve_settings_path` (dev + frozen)
- `set_password` → plik bez plaintext; `verify_password` True/False
- `clear_password` / brak pliku → `is_password_enabled` False
- `should_prompt_unlock` (lub równoważne) True tylko gdy hasło włączone
- Istniejące CLI: `--validate-norms`, parse debug flags — bez regresji

### Integration Tests:

- Brak obowiązkowego E2E CTk; ścieżka smoke-test pozostaje headless

### Manual Testing Steps:

1. Czysty start (brak `settings.json`) → brak bramki
2. Ustaw hasło w Informacjach → zamknij app → start → odblokuj poprawnym
3. Złe hasło → komunikat → retry → sukces
4. Zamknij okno odblokowania → proces kończy się
5. Zmień hasło → weryfikuj stare vs nowe przy restarcie
6. Wyłącz hasło → restart bez bramki
7. `python -m app.main --smoke-test` → exit 0, zero okien

## Performance Considerations

PBKDF2 przy starcie i przy zapisie hasła — pomijalne dla desktopu (jednorazowo).
Nie blokować UI długim KDF w wątku GUI przy absurdalnie wysokich iterations —
wybrać rozsądną stałą (np. rząd 100k–300k) i trzymać ją w module settings.

## Migration Notes

Brak migracji danych. Istniejące instalacje bez `settings.json` = hasło wyłączone.
Usunięcie pliku = de facto reset hasła (świadome; zgodne z modelem „ochrona fizyczna
placówki” + brak odzyskiwania). W dev: `settings.json` w `.gitignore` (Phase 1)
— nie commitować lokalnego hasła.

## References

- PRD Access Control / FR-009: `context/foundation/prd.md`
- Change notes: `context/changes/priority-improvements/change.md`
- Path wzorzec: `app/storage/history.py` (`resolve_history_db_path`)
- Boot: `app/main.py`
- Info sections: `app/ui/components/info_dialog.py`
- Dialog wzorzec: `app/ui/views/history.py` (`_EditStudyDialog`)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles. See `references/progress-format.md`.

### Phase 1: Settings domain — `app/config/settings.py`

#### Automated

- [x] 1.1 `python -m pytest tests/unit/test_settings.py -q` przechodzi — 745a92c
- [x] 1.2 `mypy app/config --strict` przechodzi (bez nowych błędów w pakiecie) — 745a92c

#### Manual

- [x] 1.3 Plik `settings.json` po `set_password` zawiera hash/salt, nie plaintext — 745a92c

### Phase 2: Unlock gate — bramka przed `AppWindow`

#### Automated

- [x] 2.1 Pytest settings + main_cli (+ unlock helperów) przechodzi
- [x] 2.2 mypy dla `main` / config / unlock dialog — bez nowych błędów

#### Manual

- [x] 2.3 Z hasłem: odblokowanie, złe hasło + retry, dobre → MetadataForm
- [x] 2.4 Zamknięcie okna odblokowania kończy aplikację
- [x] 2.5 Bez hasła: start bez bramki
- [x] 2.6 `--smoke-test` exit 0 bez okna

### Phase 3: Password management UI — Informacje

#### Automated

- [ ] 3.1 `python -m pytest -q` przechodzi
- [ ] 3.2 `mypy app/ --strict` przechodzi

#### Manual

- [ ] 3.3 Ustawienie hasła w Informacjach + restart wymaga hasła
- [ ] 3.4 Zmiana hasła (stare/nowe) działa przy bramce
- [ ] 3.5 Wyłączenie hasła → restart bez bramki
- [ ] 3.6 Złe obecne hasło przy zmianie/wyłączeniu — błąd, stan bez zmian
