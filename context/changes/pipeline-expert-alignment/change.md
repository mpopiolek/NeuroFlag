---
id: pipeline-expert-alignment
title: "Wyr├│wnanie pipeline NeuroFlag z metodologi─ů eksperta (QEEG / Mitsar)"
status: impl_reviewed
created: 2026-07-09
updated: 2026-07-09
pipeline_validated: 2026-07-09

Wynik kalibracji: `calibration-result.md`. Plan: `plan.md`.
---

## Cel

Doprowadzić pipeline amplitud i klasyfikację RAG do zgodności z metodą eksperta domenowego,
tak aby wyniki aplikacji były spójne z oceną kliniczną na **kotwicach walidacyjnych**:
`ADHD_EEG.edf` (wskazanie) i `depresja_EEG.edf` (wskazanie), względem centroidu kategorii
„Wskazanie” z CSV Mitsar (N=82).

`ok_EEG.edf` (brak wskazań) — plik informacyjny, **pominięty w sweepie** (flat-line C3/O1).

## Kontekst

Handoff z sesji 2026-07-08/09 (`handoff.md`), research (`research.md`) oraz pliki od eksperta Bartka w
`D:\CVGOSI\NF dane\analiza eeg\` (CSV, mail, raport PDF).

Pliki testowe EDF: `D:\CVGOSI\NF dane\Testowe\`. `Kuczy┼äski.EEG` (DigiTrack) ÔÇö przypadek legacy z wcze┼Ťniejszej pracy, poza powy┼╝sz─ů tr├│jk─ů.
