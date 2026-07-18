# Wynik kalibracji pipeline vs Mitsar

> Uzupełniono po pełnym sweepie (`scripts/calibrate_against_expert_csv.py`, 2026-07-09).
> Ten plik jest wejściem do fazy 4 (integracja produkcyjna).

## Winning Params

| Pole | Wartość |
|------|---------|
| `amplitude_method` | `welch_band_power` |
| `reject_broadband_uv` | 200 |
| `reject_filtered_uv` | 100 |
| `min_clean_seconds` | 30 |

Pełny opis: `method=welch_band_power, bb=200, rf=100, min_clean=30s` — najniższa średnia odległość od centroidu Wskazanie w gridzie 360/360 kombinacji (5 metod × progi artefaktów × min. czysty segment).

## Metryki odległości

| Kotwica EDF | Odległość od centroidu Wskazanie | Uwagi |
|-------------|----------------------------------|-------|
| ADHD_EEG.edf | 1.096 | profil bliżej centroidu niż baseline mean_abs (~0.13–0.35 NF/mean_z) |
| depresja_EEG.edf | 0.761 | przechodzi harness (brak `artifact_rejection`) przy rf=100 |

Średnia odległość (ADHD + depresja) / 2: **0.9287**

## Profile amp/mean_z (zwycięzca)

### ADHD

```
[0.191, 0.298, 0.374, 0.622, 0.569, 0.389, 0.306, 0.406, 1.019, 0.576]
```

### depresja

```
[0.278, 0.415, 0.318, 0.410, 0.723, 0.630, 0.411, 0.596, 0.812, 0.455]
```

## Centroid Wskazanie (referencja CSV N=82)

```
[0.661, 0.863, 0.306, 0.622, 0.794, 0.715, 0.749, 0.725, 0.648, 0.322]
```

Rozkład kategorii CSV (sanity check): Wskazanie 60, Uważna obserwacja 16, Brak wskazań 6.

## Uzasadnienie wyboru

- **Welch wygrywa grid:** wszystkie 10 najlepszych wariantów z 360 kombinacji to `welch_band_power`; żaden wariant `mean_abs` nie trafił do top 10.
- **Cel metryki:** odległość euklidesowa profilu `amp/mean_z` od centroidu „Wskazanie” (N=82) — zwycięzca minimalizuje ją na obu kotwicach EDF (avg 0.9287).
- **vs baseline (legacy mean_abs, reject_filtered=200):** produkcyjny pipeline dawał NF/mean_z ≈ 0.13–0.35 (za nisko względem centroidu ~0.63); `depresja_EEG.edf` kończył się błędem `artifact_rejection` przy rf=200. Welch podnosi skalę profilu; rf=100 + min_clean=30 s odblokowuje drugą kotwicę.
- **Stabilność progów:** przy zwycięskiej metodzie (bb=200, rf=100) warianty min_clean 30/60/90 s mają identyczną odległość (0.929 zaokr.) — wybrano 30 s jako najmniejszy wymagany czysty segment.
- **depresja przechodzi:** profil depresja (0.761) jest bliżej centroidu niż ADHD (1.096); oba pliki wchodzą do scoringu bez wykluczenia artefaktów.

## Known limitations

- `ok_EEG.edf` nie był kryterium akceptacji sweepu (flat-line C3/O1).
- `Kuczyński.EEG` (legacy DigiTrack) wykluczony ze scoringu.
- Brak mapowania ID CSV → pliki EDF — walidacja tylko na 2 kotwicach.
- Progi `mean_z` / `mean_k` w `norms.json` bez zmian; faza 4 zmienia tylko metodę/pipeline amplitudy.

## Akceptacja

- [v] Użytkownik zaakceptował wynik przed fazą 4
- Data: _TBD_
- Raport źródłowy: `reports/calibration_20260709_074248.md`
