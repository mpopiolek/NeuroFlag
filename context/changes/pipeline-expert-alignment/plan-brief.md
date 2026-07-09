# Kalibracja offline pipeline vs Mitsar — Plan Brief

> Full plan: `context/changes/pipeline-expert-alignment/plan.md`
> Research: `context/changes/pipeline-expert-alignment/research.md`
> Strategia offline: `context/changes/pipeline-expert-alignment/offline-calibration-plan.md`

## What & Why

Pipeline NeuroFlag produkuje amplitudy ~4–7× za niskie względem norm i skali Mitsar eksperta, co daje systematyczne all-red i fałszywe zgodności kliniczne. Bez dodatkowych danych od eksperta (brak mapowania ID, brak 10 amplitud per pacjent) budujemy **pętlę kalibracji offline**: CSV N=82 jako oracle skali/profili, kotwice EDF ADHD/depresja, sweep metryk i czyszczenia artefaktów — dopiero potem integracja do aplikacji.

## Starting Point

Na branchu `experiment/pipeline-amplitude-calibration` jest WIP: `amplitude.py` (5 metod time-domain), `amplitude_method` w config (niepodpięte do `pipeline.run()`), skrypty `compare_amplitude_methods.py` / `diagnose_patient_files.py`. Research i offline-calibration-plan ustalają mapowanie 10 kolumn CSV, centroidy kategorii (Wskazanie mediana profilu ≈ 0.63) oraz kolejność prac. Dokumentacja change zsynchronizowana z `coursor/dev-env-setup-2f65`.

## Desired End State

Skrypt `calibrate_against_expert_csv.py` wybiera wariant pipeline (metoda + 2-pass artefakty), który minimalizuje odległość profilu ADHD/depresja od centroidu „Wskazanie” w przestrzeni `amp/mean_z`. Po akceptacji raportu — produkcyjny `pipeline.run()` używa zwycięzcy; amplitudy Thety w skali ~10–30 µV zamiast ~2–5 µV. `ok_EEG.edf` pominięty w scoringu (flat-line C3/O1).

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|----------|--------|-------------------|--------|
| Kryterium sukcesu | Odległość profilu od centroidu CSV „Wskazanie” | Bez mapowania ID nie da się walidować per-pacjent EDF | Plan |
| ok_EEG.edf | Pomiń w kalibracji | Flat-line C3/O1 daje fałszywe wnioski | Plan |
| Scope produkcyjny | Offline first → integracja w fazie 4 | Bezpieczny eksperyment bez regresji GUI | Plan |
| Metryka widmowa | Welch/PSD w sweepie (priorytet) | Główna hipoteza rozjazdu z workflow Mitsar/FFT | Research + Plan |
| Czyszczenie artefaktów | Pełny 2-pass sweep (broadband + filtered) | Odzwierciedla kolejność eksperta | offline-calibration-plan + Plan |
| Branch | `experiment/pipeline-amplitude-calibration` | Kod WIP już tam; docs przeniesione | Plan |
| Normy RAG | Bez zmian progów mean_z/mean_k | Problem to skala pipeline, nie progi | Research |

## Scope

**In scope:**
- Moduł `app/domain/calibration/` (CSV loader, centroidy, harness, odległości)
- Metoda `welch_band_power` w `amplitude.py`
- Skrypty: `calibrate_against_expert_csv.py`, naprawa `compare_amplitude_methods.py`
- Grid sweep metod × progi × min. czysty segment
- Integracja zwycięzcy do `pipeline.py` (faza 4)
- Testy jednostkowe + opcjonalna integracja EDF

**Out of scope:**
- Mapowanie ID CSV → EDF, kontakt z ekspertem
- Walidacja ok_EEG, DigiTrack/Kuczyński, ICA 1:1
- Zmiana reguł RAG i progów norms.json
- UI wyboru metody, commit danych eksperta do repo

## Architecture / Approach

```
wyniki_indywidualne.csv ──► centroidy (Wskazanie/Brak/Obserwacja)
                                    ▲
ADHD/depresja EDF ──► harness (Pass1 broadband → filter → Pass2 → method) ──► profile amp/mean_z ──► distance
                                    │
                            grid sweep ──► ranking ──► calibration-result.md ──► pipeline.run() (faza 4)
```

Harness reużywa segmentację z `pipeline`; produkcja pozostaje nietknięta do fazy 4. `compute_band_amplitude` odpowiada za redukcję po czyszczeniu okien.

## Phases at a Glance

| Phase | What it delivers | Key risk |
|-------|------------------|----------|
| 1. Fundament CSV | Loader Mitsar, centroidy, testy | Parser przecinka dziesiętnego |
| 2. Harness + Welch | Offline compute z parametrami, PSD | 3 semantyki „mean abs” — pomyłka w kolejności kroków |
| 3. Sweep + raport | Grid search, wybór wariantu | depresja nadal artifact_rejection przy złych progach |
| 4. Produkcja | pipeline.run() + regresja | Regresja na istniejących testach pipeline |

**Prerequisites:** Dostęp lokalny do `wyniki_indywidualne.csv` i EDF ADHD/depresja; branch `experiment/pipeline-amplitude-calibration`.

**Estimated effort:** ~3–4 sesje implementacji (4 fazy), plus manualny full sweep i akceptacja raportu przed fazą 4.

## Open Risks & Assumptions

- Welch/PSD może nie wystarczyć do ~0.6 bez dodatkowego 2-pass — wymaga pełnego sweepu.
- Po podniesieniu skali ADHD może stracić kategorię Wskazanie — akceptujemy, bo celem jest zgodność profilu z Mitsar, nie all-red.
- CSV nie mapuje się na EDF — nie weryfikujemy „Brak wskazań” na pliku ok.
- `depresja_EEG.edf` wymaga łagodniejszych progów artefaktów (OZ pp ~550 µV).

## Success Criteria (Summary)

- Raport kalibracji wskazuje wariant z `NF/mean_z` bliżej centroidu Wskazanie (~0.6) niż obecne ~0.2 dla Thety ADHD.
- depresja i ADHD oba wchodzą w scoring (nie tylko artifact_rejection).
- Po fazie 4: pytest + mypy strict zielone; probe_pipeline na ADHD/depresja w sensownej skali µV; profil bliżej centroidu Wskazanie (kategoria RAG informacyjna).
