# S-04: Wymiana bazy norm — Plan Brief

> Full plan: `context/changes/norms-replacement/plan.md`

## What & Why

S-04 uzupełnia FR-008 o trzy brakujące ogniwa: widoczny dialog błędu gdy `norms.json`
jest niepoprawny (bo `sys.exit()` w `.exe` bez konsoli jest niewidoczne), tryb CLI
`--validate-norms <path>` dla administratora oraz dokumentację schematu.
Logika domenowa (walidacja JSON) jest gotowa od F-01 — tutaj zamykamy pętlę po stronie UX i dokumentacji.

## Starting Point

`app/domain/norms.py` posiada kompletną walidację schematu z `NormsLoadError` dla każdego
przypadku (brakujący plik, błędny JSON, brakujące klucze, zła liczba norm, nieznane pasmo).
`app/main.py` łapie `NormsLoadError` i wywołuje `sys.exit()` — komunikat trafia na stderr,
który w spakowanym `.exe` jest niewidoczny dla użytkownika. Dokumentacja schematu nie istnieje.

## Desired End State

Gdy `norms.json` jest niepoprawny, użytkownik widzi okno systemowe z polskim opisem błędu
zamiast cichej śmierci aplikacji. Administrator może zweryfikować własny plik komendą
`neuroflag.exe --validate-norms norms.json` i otrzymać czytelny wynik (OK / BŁĄD)
przed wdrożeniem. `norms.json.template` + `docs/README-norms.md` prowadzą za rękę
przez podmianę bez znajomości kodu.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) |
|---|---|---|
| Error display | `tkinter.messagebox.showerror()` przed CTk init | Zawsze widoczne — stdlib, zero nowych zależności; nie czeka na S-01 (AppWindow). |
| --validate-norms arg | Dodany do `main.py`, exit 0/1 | Administrator może weryfikować plik bez uruchamiania GUI; przydatny też w CI. |
| Schema docs | `norms.json.template` + `docs/README-norms.md` | Dwa artefakty o różnych celach: template do kopiowania, README do czytania. |
| norms.py | exe-dir-first path resolution | Podmiana obok .exe wymaga fix resolve_norms_path(), nie tylko UX |
| UI formularz norm | Osobny slice po S-01 (v2.0) | S-04 naprawia podmianę pliku; formularz CTk to większy scope |

## Scope

**In scope:**
- `app/domain/norms.py` — `resolve_norms_path()` exe-dir-first (podmiana obok `.exe`)
- `app/main.py` — `format_norms_error_message()` + `_show_norms_error()` + `--validate-norms`
- `tests/unit/test_main_cli.py`, `tests/unit/test_main_messages.py`, rozszerzenie `test_norms.py`
- `norms.json.template`, `docs/README-norms.md`
- `neuroflag.spec` — bundling template + README; opcjonalnie post-build copy `norms.json`

**Out of scope:**
- Formularz UI do edycji norm w aplikacji (osobny slice po S-01)
- Automatyczne pobieranie norm z serwera (PRD §Non-Goals)

## Architecture / Approach

```
app/main.py
  ├─ --validate-norms <path>  → norms.load(path) → print OK/BŁĄD → exit 0/1
  ├─ NormsLoadError           → _show_norms_error() + exit 1
  └─ (normalny start)         → ctk.CTk() mainloop
```

`_show_norms_error()` używa `tkinter.Tk().withdraw() + messagebox.showerror()` —
działa przed inicjalizacją CTk, bez nowych zależności.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Path resolution + error dialog + CLI | `resolve_norms_path()` exe-dir-first + messagebox + `--validate-norms` | PyInstaller path resolution musi być przetestowana |
| 2. Dokumentacja + bundling | `norms.json.template` + README + neuroflag.spec datas | Template `_comment` placement |

**Prerequisites:** F-01 ukończony (typy domenowe, norms.py, main.py stub) ✅
**Estimated effort:** ~0.5–1 sesja implementacyjna; 2 fazy liniowe

## Open Risks & Assumptions

- `tkinter.Tk().withdraw()` na headless CI (Ubuntu) może wymagać Xvfb — ale `_show_norms_error` jest wołane tylko gdy `norms.load()` rzuca wyjątek przy normalnym starcie; `--smoke-test` i `--validate-norms` exitują przed tym kodem, więc CI ich nie wywołuje
- `_comment` klucze w `norms.json.template` są ignorowane przez `norms.load()` (nie należą do `_TOP_LEVEL_KEYS`) — to zachowanie musi być potwierdzone testem `--validate-norms norms.json.template`

## Success Criteria (Summary)

- `python app/main.py --validate-norms norms.json` → `OK: norms.json jest poprawny (version=1, 10 norm)`
- Aplikacja z brakującym `norms.json` pokazuje widoczne okno błędu zamiast cichej śmierci
- `docs/README-norms.md` jest zrozumiały dla psychologa-administratora bez znajomości kodu
