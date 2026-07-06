# Pipeline Signal Fidelity — Plan Brief

> Full plan: `context/changes/pipeline-signal-fidelity/plan.md`
> Research: `context/archive/2026-06-30-testing-critical-path-domain/research.md`

## What & Why

Faza 2 rollout testów NeuroFlag: upewnić się, że pipeline EEG **nie niszczy sygnału** (R4) i **poprawnie segmentuje** nagrania DigiTrack bez tekstowych znaczników przez fallback 3×3 min (R5). Motywacja: realne pliki pacjentów pokazywały wyłącznie czerwone komórki; obecny test `isfinite`-only nie wykrywa regresji amplitudy ~0 µV.

## Starting Point

17 testów unit w `test_pipeline.py` mockują I/O; `sample_digitrack.eeg` ma tylko 10 s. Brama artefaktów to jedynie 200 µV p-p — odrzucenie jest jawne (`artifact_rejection`), nie ciche. DigiTrack zawsze używa fallback (brak adnotacji tekstowych).

## Desired End State

`tests/integration/test_pipeline_fidelity.py` z testami: syntetyk 50 µV → każda amplituda w (5, 200) µV; segment >200 µV → błąd; rozszerzona fixture ≥8 min → fallback OO/OZ/ZP + smoke `run()` z 10 skończonymi wartościami. Poprawki w `eeg_file.py` / `pipeline.py` gdy testy ujawnią kalibrację lub skrócony segment ZP.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
|----------|--------|------------------|--------|
| Zakres | Testy + poprawki produkcyjne | Testy bez fixów zostawią znane bugi kalibracji/segmentacji | Plan |
| Fixture DigiTrack | Rozszerzyć `sample_digitrack.eeg` ≥8 min | 10 s nie przechodzi `_require_recording_duration()` | Plan |
| Asercje R4 | Każda amplituda w (5.0, 200.0) µV | Dokładnie jak cookbook test-plan Faza 2 | Plan / test-plan |
| Lokalizacja testów | `tests/integration/test_pipeline_fidelity.py` | Pierwsza warstwa integration w repo | Plan |
| Brama 200 µV | Osobny test `artifact_rejection` | Potwierdza widoczny błąd, nie all-red | Plan |
| DigiTrack run() | Smoke: 10 skończonych; kalibracja w Phase 4 | Realna fixture może mieć złą skalę µV | Plan |
| UI fallback | Poza scope | Wybrano fixes bez ostrzeżenia użytkownika | Plan |

## Scope

**In scope:** R4/R5 testy integracyjne; rozszerzona fixture; test bramy 200 µV; poprawka kalibracji DigiTrack; ewentualna poprawka długości segmentu ZP przy `"Artefakt"`; aktualizacja cookbook test-plan §6.

**Out of scope:** UI, ICA/autoreject, dekodowanie markerów binarnych DigiTrack, Faza 3 (malformed files R2/R6), testy filtrów MNE, zmiana progu 200 µV.

## Architecture / Approach

```
sample_digitrack.eeg (≥8 min) ──► read_raw_digitrack ──► detect_task_segments ──► fallback 3×3
synthetic Raw 50 µV + patch _load_raw ──► run() ──► assert 5 < amp < 200 (×10)
high-amplitude synthetic ──► run() ──► PipelineError artifact_rejection
Phase 4: eeg_file.py / pipeline.py fixes if tests red
```

## Phases at a Glance

| Phase | What it delivers | Key risk |
|-------|------------------|----------|
| 1. Fixture + scaffold | ≥8 min DigiTrack w repo, `tests/integration/` | Generator wymaga lokalnego źródła pacjenta |
| 2. R4 tests | Bound 5–200 µV + artifact gate | Filtr MNE może obniżyć 50 µV poniżej 5 µV na niektórych pasmach |
| 3. R5 tests | Fallback structure + run() smoke | Niska kalibracja DigiTrack → Phase 4 |
| 4. Production fixes | Kalibracja, ZP/Artefakt, test-plan update | Reguła końca ZP może kolidować z `docs/EEG-segmentacja.md` |

**Prerequisites:** Faza 1 test-plan (testing-critical-path-domain) ukończona; MNE w venv; opcjonalnie `Kuczyński.EEG` do regeneracji fixture.

**Estimated effort:** ~2–3 sesje implementacji, 4 fazy sekwencyjnie.

## Open Risks & Assumptions

- Regeneracja fixture zależy od dostępności lokalnego pliku źródłowego — CI musi polegać na commitowanej binarii.
- Poprawka ZP/`"Artefakt"` wymaga uzgodnienia z `docs/EEG-segmentacja.md` (obecnie `"Artefakt"` może kończyć segment).
- Bound 5 µV może być zbyt ciasny dla niektórych pasm po filtracji — wtedy diagnoza, nie obniżanie progu bez uzasadnienia.

## Success Criteria (Summary)

- Integration testy R4/R5 przechodzą w CI (`python -m pytest -q`).
- Fixture DigiTrack ≥480 s w repo.
- Poprawki produkcyjne zamykają regresje ujawnione testami (min. smoke `run()` na DigiTrack).
- `mypy app/ --strict` bez regresji.
