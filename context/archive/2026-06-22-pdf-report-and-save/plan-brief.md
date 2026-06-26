# PDF Report & Save — Plan Brief

> Full plan: `context/changes/pdf-report-and-save/plan.md`

## What & Why

Aplikacja NeuroFlag ma kompletny pipeline EEG i siatkę wyników (S-02), ale nie może wygenerować raportu PDF — brakuje modułu `app/reports/` i przycisku zapisu. Celem S-03 jest umożliwienie pedagogowi/psychologowi kliknięcia jednego przycisku po analizie i zapisanie dokumentu PDF gotowego do archiwizacji lub omówienia z rodzicem.

## Starting Point

S-02 jest gotowy: `AnalysisResult` z 10 komórkami RAG i kategorią jest dostępny w `AppState`. `NormsConfig` zawiera już `observation_checklist` i `category_descriptions`. ReportLab jest wpisany w zależności (`pyproject.toml`) i `neuroflag.spec`. Brakuje jedynie warstwy generowania PDF i punktu wejścia w UI.

## Desired End State

Po kliknięciu "Zapisz raport PDF" na ekranie wyników użytkownik wybiera ścieżkę przez systemowy dialog Windows i otrzymuje plik PDF z czterema sekcjami: (1) data/wiek/płeć/kategoria słowna, (2) kolorowa siatka 10 komórek 2×5, (3) checklist "Co obserwować", (4) klauzula odpowiedzialności. Surowe wartości µV nigdy nie pojawiają się w dokumencie.

## Key Decisions Made

| Decision | Choice | Why (1 zdanie) |
|---|---|---|
| Dane pacjenta w PDF | Wiek + płeć + data badania | Anonimowość per PRD; `analyzed_at` z `AnalysisResult` jest jedynym significantnym znacznikiem |
| Tekst disclaimera | Hardcode `DISCLAIMER_PL` w pdf_generator.py | Zero konfiguracji, deterministyczny output; tekst oznaczony `# TODO: weryfikacja eksperta` |
| Kolory RAG w PDF | Wypełnione prostokąty z tymi samymi hex co UI | Wierność wizualna 1:1; hex values wyodrębnione do `app/ui/components/rag_colors.py` |
| Trigger zapisu | Przycisk + `filedialog.asksaveasfilename` | Użytkownik kontroluje lokalizację; wzorzec Windows |
| Obsługa błędu zapisu | `messagebox.showerror` + powrót do ekranu wyników | Spójne z `_show_norms_error()` z `main.py`; użytkownik może spróbować ponownie |
| Layout siatki | 2 rzędy × 5 komórek z opisem (kanał/zadanie/pasmo) | Mieści się na A4, czytelne opisy; spójne z PRD |
| APP_VERSION | `importlib.metadata.version("neuroflag")` | Jedno źródło prawdy (pyproject.toml); PEP 517 idiom |
| Testy | Smoke unit (bytes, magic, brak µV, sekcje) | Szybkie, bez dodatkowych zależności; weryfikuje format bez parsowania PDF |

## Scope

**In scope:**
- `app/reports/pdf_generator.py` — `generate_report() -> bytes`
- `app/ui/components/rag_colors.py` — wyodrębnienie stałych kolorów RAG
- `app/__init__.py` — `__version__` przez `importlib.metadata`
- Przycisk "Zapisz raport PDF" + dialog + error handling w `ResultsGridView`
- `tests/unit/test_pdf_generator.py` — 6 testów

**Out of scope:**
- Drukowanie bezpośrednie
- Zbieranie imienia/nazwiska / pola ID pacjenta
- Podgląd PDF przed zapisem
- Konfigurowalne szablony
- Historia zapisanych raportów
- Wartości µV w jakiejkolwiek formie

## Architecture / Approach

```
ResultsGridView
    └─ _on_save_pdf()
          ├─ filedialog.asksaveasfilename → ścieżka
          ├─ generate_report(metadata, result, config) → bytes   [app/reports/pdf_generator.py]
          │       ├─ RAG_COLOR_BG, TASK_LABELS  [app/ui/components/rag_colors.py]
          │       ├─ ObservationChecklist        [NormsConfig — norms.json]
          │       └─ DISCLAIMER_PL              [stała w module]
          └─ Path(path).write_bytes(pdf_bytes)
```

`generate_report()` jest czystą funkcją (input → bytes), co ułatwia testowanie bez systemu plików.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|---|---|---|
| 1. Shared Infrastructure | `rag_colors.py` + `__version__` | Refaktor results_grid.py może złamać istniejące UI — objęty testami |
| 2. PDF Generator | `generate_report() -> bytes`, 4 sekcje PRD | Wierność kolorów RAG w ReportLab (`Table`+`BACKGROUND` vs `Canvas`) |
| 3. UI Integration | Przycisk + dialog + error handling | Anulowanie dialogu musi być obsłużone bez wyjątku |
| 4. Unit Tests | 6 testów smoke dla generatora | Weryfikacja sekcji bez pdfminer (raw bytes search) |

**Prerequisites:** S-02 kompletny (jest). ReportLab zainstalowany (`pip install reportlab==4.2.5` lub przez venv).

**Estimated effort:** ~2 sesje, 4 fazy sekwencyjne.

## Open Risks & Assumptions

- Tekst `DISCLAIMER_PL` jest wersją roboczą — wymaga weryfikacji eksperta domenowego przed wdrożeniem produkcyjnym
- `observation_checklist` w `norms.json` ma status `DRAFT` (`_content_review_status`) — treść checklist w PDF będzie odpowiadać tej wersji roboczej
- ReportLab `Table` z `BACKGROUND` style jest standardowym podejściem dla kolorowych komórek; jeśli na testowym buildzie kolory nie są renderowane poprawnie, fallback to `Canvas.setFillColor` + `rect()`

## Success Criteria (Summary)

- Kliknięcie "Zapisz raport PDF" → systemowy dialog → plik PDF z 4 sekcjami zapisany na dysku
- Plik PDF nie zawiera żadnych wartości µV (weryfikacja automatyczna przez test)
- Pełny flow (S-01 → S-02 → PDF) zamyka się w ≤ 10 minut (kryterium PRD `prd.md:85`)
