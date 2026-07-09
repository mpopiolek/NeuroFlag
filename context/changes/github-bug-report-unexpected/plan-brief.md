# Zgłaszanie błędów nieoczekiwanych — Plan Brief

> Pełny plan: `context/changes/github-bug-report-unexpected/plan.md`

## What & Why

Gdy NeuroFlag napotka błąd nieoczekiwany, pedagog powinien móc jednym kliknięciem otworzyć GitHub Issue z wstępnie wypełnioną diagnostyką techniczną (wersja, OS, krok wizarda, kontekst pliku EEG) — bez wysyłania danych dziecka. Ręczne zgłoszenie z widoku Informacje korzysta z tego samego mechanizmu. Użytkownik dopisuje opis problemu i ewentualny zrzut ekranu sam.

## Starting Point

Przycisk „Zgłoś błąd na GitHubie” w Informacjach otwiera pusty URL (`GITHUB_NEW_ISSUE_URL`). Błędy pipeline wyświetlają komunikat PL na status label (`FileImportView.show_analysis_error`); `unexpected_error` traci typ wyjątku poza nazwą klasy. Brak globalnego `excepthook`. Wynik detekcji znaczników OO/OZ/ZP nie jest zapisywany poza runtime pipeline.

## Desired End State

- `unexpected_error` z analizy → komunikat na ekranie importu + przycisk „Zgłoś błąd” w stopce z pre-fill.
- Nieobsłużony wyjątek w GUI → modal CTk z komunikatem + przycisk zgłoszenia (ten sam URL builder).
- Ręczne zgłoszenie w Informacjach → pre-fill diagnostyki bieżącej sesji (bez kodu błędu).
- Treść issue zawiera wyłącznie pola z listy użytkownika; resztę użytkownik uzupełnia w przeglądarce.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|---|---|---|---|
| Zakres auto-zgłoszenia | `unexpected_error` + globalny excepthook | Pokrywa crashy analizy i nieobsłużone błędy GUI | Plan |
| UI błędu analizy | Status label + primary stopki = „Zgłoś błąd” | Jeden slot primary w `set_footer` — zastąpienie „Analizuj”, bez nowego modala | Plan |
| Traceback w issue | Tylko typ wyjątku (np. `ValueError`) | Kompromis debug vs PII/rozmiar URL | Plan |
| Znaczniki OO/OZ/ZP | Snapshot w AppState z pipeline | Dokładna odpowiedź nawet przy unexpected_error po segmentacji | Plan |
| Oczekiwane błędy pipeline | Bez przycisku zgłoszenia | Pedagog rozumie komunikat; nie zaśmiecamy issue trackera | Użytkownik |
| Załączniki plików | Ręcznie przez użytkownika na GitHubie | API/token nie pasuje do modelu offline | Plan |

## Scope

**In scope:**
- Moduł `bug_report` (kontekst, sanityzacja, URL GitHub)
- Snapshot segmentacji w `AppState` / `pipeline.run()`
- Stopka FileImportView z przyciskiem przy `unexpected_error`
- Globalny excepthook + modal dla nieobsłużonych wyjątków
- Pre-fill przy ręcznym zgłoszeniu w Informacjach
- Testy jednostkowe URL i sanityzacji

**Out of scope:**
- Przycisk zgłoszenia przy oczekiwanych `PipelineError` (np. `missing_channels`)
- Automatyczne załączanie plików / screenshotów
- GitHub API / token / tworzenie issue bez przeglądarki
- Lokalny plik logów na dysku
- Zmiana szablonu issue poza sekcją auto-wypełnianą w body

## Architecture / Approach

```
AppWindow / AppState
    ↓ collect_bug_report_context()
app/ui/bug_report.py  →  format body (PL) + urllib.parse.urlencode
    ↓ webbrowser.open()
GitHub issues/new?template=bug_report.md&title=...&body=...
```

Pipeline aktualizuje `AnalysisDiagnostics` na milestone'ach (segmentacja: adnotacje / fallback / nie dotyczy). `AnalysisRunner` zapisuje `exc_type` przy wrapowaniu na `unexpected_error`.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Moduł bug_report | URL builder + sanityzacja + testy | Limit długości URL w przeglądarce |
| 2. Pipeline snapshot | `segment_mode` w AppState | Refaktor `detect_task_segments` bez regresji pipeline |
| 3. unexpected_error UI | Status + stopka FileImportView | Stopka musi współistnieć z „Analizuj” |
| 4. excepthook + Info | Modal crash + pre-fill Informacje | Hook musi działać z CTk mainloop |

**Prerequisites:** Brak nowych zależności.
**Estimated effort:** ~2 sesje, 4 fazy.

## Open Risks & Assumptions

- Długi body może wymagać fallbacku „kopiuj do schowka” (implementować jeśli URL > ~6000 znaków w testach)
- Globalny excepthook nie łapie błędów w wątkach daemon poza `AnalysisRunner` (akceptowalne — analiza już owinięta)
- Wersje MNE/NumPy tylko gdy import się powiedzie (w `.exe` zawsze; w dev zawsze)

## Success Criteria (Summary)

- Po `unexpected_error` użytkownik widzi przycisk zgłoszenia i otwiera GitHub z wypełnioną diagnostyką
- Ręczne zgłoszenie z Informacji zawiera wersję, OS, krok, kontekst pliku — bez inicjałów/ścieżek
- `pytest` i `mypy app/ --strict` przechodzą
