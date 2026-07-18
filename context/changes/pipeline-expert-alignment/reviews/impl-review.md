<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Kalibracja offline pipeline vs Mitsar

- **Plan**: context/changes/pipeline-expert-alignment/plan.md
- **Scope**: All 4 phases
- **Date**: 2026-07-09
- **Verdict**: NEEDS ATTENTION
- **Findings**: 0 critical, 2 warnings, 4 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | WARNING |
| Scope Discipline | WARNING |
| Safety & Quality | PASS |
| Architecture | PASS |
| Pattern Consistency | WARNING |
| Success Criteria | PASS |

## Automated Verification

| Command | Result |
|---------|--------|
| `python -m pytest -q` | PASS — 279 tests green |
| `python -m mypy app/ --strict` | PASS — 42 source files |
| `python -m app.main --validate-norms norms.json` | PASS |

## Findings

### F1 — change.md wciąż wymienia ok_EEG jako kotwicę walidacyjną

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Plan Adherence
- **Location**: context/changes/pipeline-expert-alignment/change.md:15-16
- **Detail**: Plan i sweep wykluczają `ok_EEG.edf` ze scoringu (flat-line C3/O1). `change.md` w sekcji Cel nadal wymienia `ok_EEG.edf` obok ADHD i depresja jako zestaw walidacyjny eksperta.
- **Fix**: Zaktualizuj sekcję Cel: ok_EEG informacyjny/pominięty w sweepie; kotwice akceptacji = ADHD + depresja + centroid CSV.
- **Decision**: FIXED

### F2 — diagnose_patient_files.py używa przestarzałej ścieżki diagnostycznej

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Pattern Consistency
- **Location**: scripts/diagnose_patient_files.py:163-229
- **Detail**: Skrypt używa legacy single-pass mean(abs) + MNE drop_bad (200 µV) i importuje prywatne symbole pipeline (`_REJECT_EEG_VOLTS`). Rozjazd względem produkcyjnego 2-pass Welch + `signal_amplitude` — wprowadza w błąd przy debugowaniu po kalibracji.
- **Fix A ⭐ Recommended**: Refaktor do `compute_cell_amplitude` / `pipeline.run` z bieżącym `NormsConfig`.
  - Strength: Diagnostyka odzwierciedla produkcję.
  - Tradeoff: Większy diff w skrypcie dev-only.
  - Confidence: HIGH — publiczne API już istnieje.
  - Blind spot: Nie sprawdzono czy ktoś polega na starym formacie outputu.
- **Fix B**: Oznacz skrypt jako legacy-only w nagłówku; nie refaktoruj.
  - Strength: Minimalny diff.
  - Tradeoff: Nadal mylący przy przypadkowym użyciu.
  - Confidence: MED.
  - Blind spot: Brak.
- **Decision**: FIXED (Fix A)

### F3 — compare_amplitude_methods.py bez override ścieżek EDF

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: scripts/compare_amplitude_methods.py:24-29
- **Detail**: `REFERENCE_FILES` hardkoduje `D:\CVGOSI\...` bez `--edf-dir` / env, w przeciwieństwie do `calibrate_against_expert_csv.py` i `paths.py`.
- **Fix**: Użyj `DEFAULT_EDF_DIR` / `NEUROFLAG_EDF_DIR` lub dodaj argparse jak w skrypcie kalibracji.
- **Decision**: FIXED

### F4 — norms.json bez jawnych pól zwycięzcy kalibracji

- **Severity**: 👁 OBSERVATION
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Scope Discipline
- **Location**: norms.json (brak kluczy) + app/domain/norms.py:318-340
- **Detail**: Plan przewiduje breaking change behawioralny przez defaulty w kodzie (`welch_band_power`, bb=200, rf=100, min=30) gdy klucze nieobecne. `norms.json.template` udokumentowany; produkcyjny `norms.json` bez tych pól — trudniejszy audyt „co faktycznie działa”.
- **Fix A ⭐ Recommended**: Dopisz zwycięskie pola do `norms.json` (nie zmieniaj progów mean_z/mean_k).
  - Strength: Jawna konfiguracja, łatwiejszy rollback i audyt.
  - Tradeoff: Zmiana pliku klienta (behawior już i tak się zmienił przez defaulty).
  - Confidence: HIGH — template już ma wartości.
  - Blind spot: Instalacje z ręcznie edytowanym norms.json.
- **Fix B**: Zostaw jak jest; opisz w change.md że defaulty kodu = zwycięzca.
  - Strength: Zgodne z migration note planu.
  - Tradeoff: Ukryta konfiguracja.
  - Confidence: HIGH.
  - Blind spot: Admin nie wie skąd biorą się nowe amplitudy.
- **Decision**: FIXED (Fix A)

### F5 — DEFAULT_PRODUCTION_PARAMS martwa stała

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: app/domain/signal_amplitude.py:33-38
- **Detail**: `DEFAULT_PRODUCTION_PARAMS` zdefiniowana, nigdzie nieużywana; produkcyjne parametry płyną przez `NormsConfig` / `signal_params_from_config`.
- **Fix**: Usuń stałą lub podłącz jako single source of truth w `norms.load()`.
- **Decision**: FIXED

### F6 — Brak wariantu ZADANIE POZNA w tabeli aliasów docs

- **Severity**: 👁 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: docs/EEG-segmentacja.md:88
- **Detail**: Plan wymagał aliasu `ZADANIE POZNA` / `zadanie pozna`. Kod pipeline ma `"ZADANIE POZNA"`; docs ma tylko `Zadanie pozna` / `zadanie pozna` (bez wariantu ALL CAPS z EDF).
- **Fix**: Dodaj `ZADANIE POZNA` do tabeli aliasów ZP.
- **Decision**: FIXED
