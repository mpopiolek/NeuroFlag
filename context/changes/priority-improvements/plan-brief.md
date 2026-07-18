# Opcjonalne hasło startowe (FR-009) — Plan Brief

> Full plan: `context/changes/priority-improvements/plan.md`

## What & Why

Domykamy jedyną lukę techniczną minimalnego paska: opcjonalne hasło startowe (FR-009)
jako warstwę psychologiczną ochrony dostępu do aplikacji offline. Bez szyfrowania
plików EEG/historii (to v2.0) — jeden użytkownik na urządzenie, prompt tylko gdy
hasło jest ustawione.

## Starting Point

Brak `app/config/`; boot idzie prosto z `norms.load()` do `AppWindow`. Lokalne pliki
obok exe (`norms.json`, `history.db`) dają gotowy wzorzec ścieżki; Informacje mają
karty sekcji i wzorzec `CTkToplevel` do dialogów.

## Desired End State

Bez hasła — start jak dziś. Z hasłem — bramka przed głównym oknem; zarządzanie
(ustaw/zmień/wyłącz) z Informacji; na dysku tylko hash w `settings.json`;
`--smoke-test` nadal headless.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| -------- | ------ | ---------------- | ------ |
| Konfiguracja hasła | UI w aplikacji + plik lokalny | Spełnia FR-009 „użytkownik może skonfigurować” bez ręcznego JSON | Plan |
| Storage | Hash PBKDF2 + salt w `settings.json` | Stdlib, bez plaintext; nie udaje szyfrowania danych EEG | Plan |
| Złe hasło / anuluj | Komunikat + retry; zamknięcie okna = exit | Prosta bramka desktopowa bez fałszywego lockoutu | Plan |
| Zarządzanie | Sekcja w Informacjach + dialog | Pełny cykl życia bez nowego chrome w nagłówku | Plan |
| Testy | Unit settings + logika bramki; UI manual | Chroni CI/smoke; unika kruchego E2E CTk | Plan |
| Model dostępu | Jeden użytkownik / jedna rola | Zgodnie z PRD Access Control | PRD |

## Scope

**In scope:**
- `app/config/settings.py` (path, hash, set/verify/clear)
- Bramka odblokowania przed `AppWindow` w `main.py`
- UI zarządzania w Informacjach
- Unit testy settings + helperów bramki

**Out of scope:**
- Szyfrowanie plików / DB
- Multi-user, role, rate-limit
- Odzyskiwanie hasła online
- E2E CTk w CI

## Architecture / Approach

```
main: norms.load → [smoke exit] → [unlock if enabled] → AppWindow
settings.json (obok exe) ← app/config/settings.py (PBKDF2)
Informacje → karta Hasło startowe → dialog set/change/clear
```

## Phases at a Glance

| Phase | What it delivers | Key risk |
| ----- | ---------------- | -------- |
| 1. Settings domain | API + `settings.json` + unit testy | Zły path (MEIPASS vs exe dir) |
| 2. Unlock gate | Bramka startowa; smoke bez GUI | Dialog przed AppWindow / regresja smoke |
| 3. Management UI | Ustaw/zmień/wyłącz w Informacjach | Status karty nie odświeża się po zapisie |

**Prerequisites:** działający GUI Informacje; brak blokady na FR-009 w aktywnym slice
**Estimated effort:** ~1–2 sesje, 3 fazy

## Open Risks & Assumptions

- Usunięcie `settings.json` = reset hasła (świadome; brak recovery flow)
- „Iluzja bezpieczeństwa” zaakceptowana w PRD — plan nie obiecuje ochrony plików
- Iterations PBKDF2 dobrane konserwatywnie pod desktop (stała w module)

## Success Criteria (Summary)

- Hasło opcjonalne: off = start bez tarcia; on = bramka przy każdym starcie GUI
- Zarządzanie w Informacjach bez edycji ręcznej JSON (plik i tak jest czytelny dla resetu)
- CI/`--smoke-test` bez okien i bez regresji suite + mypy
