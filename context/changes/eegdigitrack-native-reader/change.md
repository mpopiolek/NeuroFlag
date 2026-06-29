---
id: eegdigitrack-native-reader
title: "Natywny czytnik formatu EEGDigiTrack (Elmiko) w NeuroFlag"
status: implementing
created: 2026-06-26
updated: 2026-06-29
---

## Cel

Umożliwić wczytywanie plików `.EEG` w formacie EEGDigiTrack (Elmiko Medical)
bezpośrednio w NeuroFlag — bez konieczności eksportu do EDF przez oprogramowanie DigiTrack.

## Kontekst

Użytkownicy posiadają pliki `.EEG` z aparatów Elmiko (np. EEG-1042).
Format jest własnościowy, nieudokumentowany publicznie, ale został w pełni
zdekodowany w ramach badania `eegdigitrack-native-reader` (2026-06-26).
