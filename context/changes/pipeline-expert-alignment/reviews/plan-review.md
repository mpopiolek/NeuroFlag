<!-- PLAN-REVIEW-REPORT -->
# Plan Review: Kalibracja offline pipeline vs Mitsar

- **Plan**: `context/changes/pipeline-expert-alignment/plan.md`
- **Mode**: Deep
- **Date**: 2026-07-09
- **Verdict**: SOUND (po triage)
- **Findings**: 2 critical, 4 warnings, 1 observation

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| End-State Alignment | FAIL ❌ |
| Lean Execution | PASS ✅ |
| Architectural Fitness | WARNING ⚠️ |
| Blind Spots | WARNING ⚠️ |
| Plan Completeness | WARNING ⚠️ |

## Grounding

Grounding: 9/9 paths ✓, 5/5 symbols ✓, brief↔plan ⚠️ (sprzeczność kryterium kategorii EDF w fazie 4)

## Findings

### F1 — Phase 4 wymaga kategorii Wskazanie, brief mówi że to akceptowalna strata

- **Severity**: ❌ CRITICAL
- **Impact**: 🔬 HIGH — architectural stakes; think carefully before deciding
- **Dimension**: End-State Alignment
- **Location**: Phase 4 — Manual Verification; plan-brief Open Risks
- **Detail**: Faza 4 manual (4.4) wymaga „kategoria ADHD/depresja = Wskazanie (nie przez all-red)”. Plan-brief i offline-calibration-plan jednoznacznie akceptują, że po naprawie skali ADHD **może stracić** kategorię Wskazanie — celem jest profil bliski centroidowi Mitsar (~0.6), nie zgodność RAG. Implementer nie wie, co jest kryterium akceptacji.
- **Fix A ⭐ Recommended**: Zmienić 4.4 na: amplitudy Thety ~10–30 µV + profil `amp/mean_z` bliżej centroidu Wskazanie niż baseline ~0.2; kategoria RAG **informacyjna**, nie gate.
  - Strength: Spójne z decyzją planowania (centroidy CSV) i research (all-red był artefaktem skali).
  - Tradeoff: Brak twardego E2E „kategoria = ekspert” bez mapowania ID.
  - Confidence: HIGH — sprzeczność jest literalna w plan vs brief.
  - Blind spot: Nie wiemy, czy profil Mitsar ADHD faktycznie daje ≥5 red po poprawnej skali.
- **Fix B**: Zachować wymóg kategorii Wskazanie i dodać fallback: jeśli profil OK ale kategoria nie — osobna decyzja o regułach RAG (out of scope).
  - Strength: Zachowuje zgodność z etykietami klinicznymi EDF.
  - Tradeoff: Może zablokować fazę 4 mimo poprawnej skali; wchodzi w scope reguł RAG (plan mówi „not doing”).
  - Confidence: MEDIUM — research sugeruje że Mitsar ADHD może nie być all-red.
  - Blind spot: Brak 10 amplitud Mitsar dla plików EDF.
- **Decision**: FIXED via Fix A

### F2 — Regresja CSV w sweepie jest stała (vacuous constraint)

- **Severity**: ❌ CRITICAL
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: End-State Alignment
- **Location**: Desired End State #2; Phase 3 — Skrypt kalibracji
- **Detail**: Desired End State wymaga, by zwycięzca „przechodził regresję rozkładu 82 profili CSV”. Phase 3 jednocześnie mówi, że CSV to stały baseline Mitsar — sweep nie zmienia amplitud CSV. Każdy wariant dostaje identyczny rozkład (60/6/16). Constraint nie rankuje wariantów i nie wykrywa regresji.
- **Fix A ⭐ Recommended**: Przenieść „regresję CSV” do fazy 1 jako jednorazowy sanity check (loader + classify 82 wierszy); z Phase 3 ranking tylko EDF distance + tie-break.
  - Strength: Uczciwy kontrakt — nie obiecujemy testu, którego sweep nie robi.
  - Tradeoff: Brak automatycznej regresji populacyjnej po zmianie pipeline (wymaga mapowania ID lub re-run na EDF).
  - Confidence: HIGH — logika sweepu jest deterministyczna względem CSV.
  - Blind spot: None significant.
- **Fix B**: Dodać fazę symulacji: skaluj EDF profilem gain per wariant i porównuj z CSV — nadal bez mapowania ID, więc i tak nie działa per-pacjent.
  - Strength: Formalnie „łączy” CSV z pipeline.
  - Tradeoff: Gain globalny odrzucony w research; fałszywe poczucie walidacji.
  - Confidence: LOW — research odrzuca globalny mnożnik.
  - Blind spot: Nie zweryfikowano, czy gain per wariant ma sens kliniczny.
- **Decision**: FIXED via Fix A

### F3 — Konflikt backward compat vs domyślne parametry = zwycięzca

- **Severity**: ⚠️ WARNING
- **Impact**: 🔬 HIGH — architectural stakes; think carefully before deciding
- **Dimension**: Blind Spots
- **Location**: Phase 4 — Refaktor pipeline
- **Detail**: Phase 4 wymaga jednocześnie: (a) domyślne parametry = zwycięzca z kalibracji (Welch + 2-pass + min_clean_seconds), (b) backward compat: mean_abs + obecne progi = dotychczasowy wynik. Obecny pipeline: tylko Pass 2 po filtrze, 200 µV, brak min_clean_seconds, ignoruje amplitude_method. Zwycięzca sweepu **nie może** spełniać obu warunków naraz.
- **Fix A ⭐ Recommended**: Wprowadzić `LegacyPipelineParams` (mean_abs, reject_broadband=0, reject_filtered=200, min_clean=0) dla testów regresji; produkcyjne defaulty z `calibration-result.md` jako nowy standard (breaking change udokumentowany w Migration Notes).
  - Strength: Jawny kontrakt testów vs produkcji; implementer wie co porównać.
  - Tradeoff: Istniejący `norms.json` bez nowych pól wymaga defaultów w kodzie.
  - Confidence: HIGH — diff pipeline vs harness jest udokumentowany w research.
  - Blind spot: Klientów z zapisanymi normami trzeba powiadomić ręcznie (plan już to ma).
- **Fix B**: Zwycięzca tylko jako opt-in przez `norms.json`; default pozostaje legacy mean_abs.
  - Strength: Zero breaking change dla istniejących instalacji.
  - Tradeoff: Aplikacja bez aktualizacji norms.json nie korzysta z kalibracji — plan kończy się bez efektu u użytkownika.
  - Confidence: MEDIUM — plan zakłada integrację produkcyjną w fazie 4.
  - Blind spot: Kto aktualizuje norms u klientów.
- **Decision**: FIXED via Fix A

### F4 — Ryzyko circular import pipeline ↔ calibration.harness

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Architectural Fitness
- **Location**: Phase 2 harness + Phase 4 refaktor
- **Detail**: Harness importuje `pipeline.detect_task_segments` / `_load_raw`; Phase 4 każe `pipeline` importować logikę z `calibration.harness` → cykl modułów. Plan wspomina `signal_amplitude.py` jako alternatywę, ale nie decyduje.
- **Fix A ⭐ Recommended**: Phase 2 tworzy `app/domain/signal_amplitude.py` (artifact passes + compute) używany przez harness **i** pipeline; `calibration/` tylko CSV + sweep; pipeline importuje `signal_amplitude`, nie `calibration`.
  - Strength: Jednokierunkowy graf: calibration → signal_amplitude ← pipeline.
  - Tradeoff: Dodatkowy plik w fazie 2 zamiast „później może”.
  - Confidence: HIGH — standardowy wzorzec extract-shared-core.
  - Blind spot: None significant.
- **Fix B**: Lazy import w `pipeline.run()` — łata symptom, nie architekturę.
  - Strength: Mniejszy diff w fazie 2.
  - Tradeoff: Ukryty coupling; mypy/import-time surprises.
  - Confidence: LOW — antywzorzec w codebase (brak lazy imports w domain).
  - Blind spot: None significant.
- **Decision**: FIXED via Fix A

### F5 — `ResultCategory` nie istnieje w codebase

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Phase 1 — Contract csv_oracle.py
- **Detail**: Plan używa `ResultCategory`; faktyczny typ to `ScreeningCategory` (`app/domain/types.py:39`); `classify()` zwraca `AnalysisResult`.
- **Fix**: Zamienić `classify_csv_row(...) -> ScreeningCategory` (lub zwracać `AnalysisResult.category`).
- **Decision**: FIXED

### F6 — Welch wymaga `fmin/fmax`, brak w sygnaturze `compute_band_amplitude`

- **Severity**: ⚠️ WARNING
- **Impact**: 🔎 MEDIUM — real tradeoff; pause to reason through it
- **Dimension**: Plan Completeness
- **Location**: Phase 2 — Metoda Welch/PSD
- **Detail**: Obecna sygnatura `compute_band_amplitude(data_uv, sfreq, method)` nie przyjmuje granic pasma. Welch na już przefiltrowanym sygnale nadal potrzebuje zakresu częstotliwości do integracji PSD — implementer musi zgadywać API.
- **Fix A ⭐ Recommended**: Rozszerzyć kontrakt: `compute_band_amplitude(..., band: BandRange | None = None)` — wymagane dla `welch_band_power`, ignorowane dla time-domain metod.
  - Strength: Jawny kontrakt; harness przekazuje `config.band_ranges[norm.band]`.
  - Tradeoff: Dotknięcie wszystkich wywołań w testach.
  - Confidence: HIGH — bez band range Welch jest niezdefiniowany.
  - Blind spot: Czy sqrt(mean(PSD)) na post-filter sygnale = Mitsar — nadal otwarte (research Q3).
- **Fix B**: Osobna funkcja `welch_band_amplitude(data_uv, sfreq, l_freq, h_freq)` bez zmiany istniejącego API.
  - Strength: Mniejszy blast radius na time-domain metody.
  - Tradeoff: Rozproszenie logiki amplitudy w dwóch API.
  - Confidence: MEDIUM — działa, ale mnoży entry points.
  - Blind spot: None significant.
- **Decision**: FIXED via Fix A

### F7 — Brak reguły touched-set z lessons.md w planie commitów

- **Severity**: 💡 OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Completeness
- **Location**: Migration Notes / implementacja faz
- **Detail**: `context/foundation/lessons.md` wymaga commitów fazowych tylko z touched-set bieżącej zmiany — plan tego nie wspomina; ryzyko zaśmieconych commitów (np. `_tmp_*.txt`, inne change foldery).
- **Decision**: FIXED
