---
change_id: digitrack-patient-header-info
title: Odczyt inicjałów i roku urodzenia z nagłówka DigiTrack
status: done
created: 2026-07-07
updated: 2026-07-07
archived_at: null
---

## Notes

Rozszerzenie `read_patient_header_info()` o pliki `.eeg` (EEGDigiTrack): inicjały z pola
`Imie_NAZWISKO` (np. Michal_KUCZYNSKI → MK) oraz rok urodzenia z daty `DD-MMM-YYYY`
(np. 24-DEC-1989 → 1989). Pre-fill w ekranie importu pliku — analogicznie do EDF.
