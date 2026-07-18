---
id: metadata-and-import
title: "Formularz metryki dziecka + import pliku EEG"
status: archived
created: 2026-06-01
updated: 2026-06-02
archived_at: 2026-06-02T12:00:00Z
roadmap_ref: S-01
prd_refs: [FR-001, FR-010, US-01]
unlocks: [eeg-pipeline-and-results]
---

## Summary

Buduje dwa pierwsze widoki aplikacji CustomTkinter (MetadataFormView + FileImportView),
moduł walidacji pliku EEG (`app/domain/eeg_file.py`) oraz nawigacyjną powłokę AppWindow
z typowanym AppState. Po ukończeniu S-01 aplikacja przyjmuje `PatientMetadata` i ścieżkę
pliku EEG jako wejście gotowe do S-02 (pipeline + siatka wyników).
