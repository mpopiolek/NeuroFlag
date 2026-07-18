# Instrukcja wymiany bazy norm (`norms.json`)

Ten dokument opisuje, jak administrator placówki (np. psycholog) może zastąpić domyślną bazę norm własnym plikiem — bez przebudowy aplikacji i bez dostępu do kodu źródłowego.

---

## Gdzie znajduje się plik `norms.json`

Po rozpakowaniu aplikacji plik leży **w tym samym folderze co `neuroflag.exe`**:

```
C:\Programy\NeuroFlag\
  neuroflag.exe
  norms.json              ← ten plik można podmienić
  norms.json.template     ← wzór do kopiowania (tylko informacyjny)
  docs\
    README-norms.md       ← ta instrukcja
  _internal\              ← biblioteki — nie modyfikować
```

Ścieżka w buildzie deweloperskim: `dist/neuroflag/norms.json` obok `dist/neuroflag/neuroflag.exe`.

---

## Jak wymienić bazę norm

1. **Skopiuj wzór** — skopiuj plik `norms.json.template` jako `norms.json` (lub edytuj istniejący `norms.json`).
2. **Edytuj wartości** — zmień `mean_z` i `mean_k` w tablicy `norms` (oraz ewentualnie progi w `recommendation_rules`). Nie zmieniaj nazw pól ani struktury bez konsultacji z ekspertem domenowym.
3. **Zwaliduj plik** przed wdrożeniem (patrz sekcja poniżej).
4. **Uruchom aplikację** — NeuroFlag wczytuje `norms.json` przy starcie. Jeśli plik jest niepoprawny, zobaczysz okno z komunikatem błędu (aplikacja nie uruchomi analizy).

---

## Walidacja pliku przed wdrożeniem

W folderze aplikacji otwórz wiersz poleceń (cmd) i uruchom:

```cmd
neuroflag.exe --validate-norms norms.json
```

W środowisku deweloperskim:

```cmd
python -m app.main --validate-norms norms.json
```

**Poprawny plik** — komunikat na ekranie:

```
OK: norms.json jest poprawny (version=1, 10 norm)
```

**Niepoprawny plik** — komunikat zaczyna się od `BŁĄD:` i program kończy się kodem 1.

Możesz też wskazać pełną ścieżkę do pliku roboczego przed skopiowaniem go obok `.exe`:

```cmd
neuroflag.exe --validate-norms C:\Users\Ja\Pulpit\nowe-normy.json
```

---

## Opis pól schematu

| Pole | Typ | Opis | Przykład |
|------|-----|------|----------|
| `version` | liczba całkowita | Wersja schematu pliku | `1` |
| `power_line_frequency` | liczba | Częstotliwość sieci (Hz) do filtra notch | `50` (Europa) |
| `recommendation_rules` | obiekt | Progi decyzyjne algorytmu trójstanowego | patrz wzór |
| `recommendation_rules.indication_min_red` | liczba całkowita ≥ 0 | Min. liczba czerwonych komórek do kategorii „Wskazanie" | `5` |
| `recommendation_rules.indication_max_green` | liczba całkowita ≥ 0 | Max. liczba zielonych komórek przy „Wskazaniu" | `3` |
| `recommendation_rules.no_indication_min_green` | liczba całkowita ≥ 0 | Min. liczba zielonych komórek do kategorii „Brak wskazań" | `4` |
| `recommendation_rules.no_indication_max_red` | liczba całkowita ≥ 0 | Max. liczba czerwonych komórek przy „Braku wskazań" | `3` |
| `category_descriptions` | obiekt *(opcjonalny)* | Opisy słowne wyników widoczne w UI i raporcie PDF | patrz wzór |
| `category_descriptions.wskazanie` | tekst niepusty | Opis kategorii „Wskazanie do dalszej diagnozy" | — |
| `category_descriptions.obserwacja` | tekst niepusty | Opis kategorii „Obserwacja" | — |
| `category_descriptions.brak` | tekst niepusty | Opis kategorii „Brak wskazań" | — |
| `observation_checklist` | obiekt *(opcjonalny)* | Lista obszarów do obserwacji w UI i raporcie PDF | patrz wzór |
| `observation_checklist.title` | tekst niepusty | Tytuł sekcji checklista | — |
| `observation_checklist.intro` | tekst niepusty | Tekst wprowadzający do listy | — |
| `observation_checklist.categories` | tablica obiektów | Kategorie obserwacji; każda ma `title` (tekst) i `items` (tablica tekstów) | — |
| `band_ranges` | obiekt | Zakresy pasm częstotliwości (Hz) | patrz wzór |
| `band_ranges.*.l_freq` | liczba | Dolna granica pasma (Hz) | `4.0` dla Theta |
| `band_ranges.*.h_freq` | liczba | Górna granica pasma (Hz) | `8.0` dla Theta |
| `norms` | tablica (10 wpisów) | Macierz norm — dokładnie 10 kombinacji kanał/zadanie/pasmo | — |
| `norms[].id` | liczba całkowita | Identyfikator normy (1–10) | `1` |
| `norms[].channel` | tekst | Kanał EEG (system 10–20) | `"C3"` lub `"O1"` |
| `norms[].task` | tekst | Segment zadania | `"OO"`, `"OZ"` lub `"ZP"` |
| `norms[].band` | tekst | Nazwa pasma z `band_ranges` | `"Theta"` |
| `norms[].mean_z` | liczba | Próg dolny Z (µV) — wartość ≤ Z daje kolor czerwony | `30.35` |
| `norms[].mean_k` | liczba | Próg górny K (µV) — wartość ≥ K daje kolor zielony | `35.44` |

Pola `_comment` w pliku wzorcowym są opcjonalne — służą tylko dokumentacji i nie wpływają na walidację.

---

## Najczęstsze błędy

| Komunikat błędu (fragment) | Przyczyna | Co zrobić |
|----------------------------|-----------|-----------|
| `missing required key 'version'` | Brakuje wymaganego pola na poziomie głównym | Porównaj plik z `norms.json.template` |
| `must contain exactly 10 entries` | Tablica `norms` ma inną liczba wpisów niż 10 | Uzupełnij lub usuń nadmiarowe wpisy |
| `missing key 'mean_z'` / `'mean_k'` | Brakuje progu w wpisie normy | Uzupełnij oba progi w każdym wpisie |
| `references band 'Alpha' not defined` | W `norms` jest pasmo spoza `band_ranges` | Użyj tylko: Delta, Theta, Beta1, Beta2 |
| `Invalid JSON` | Błąd składni (przecinek, cudzysłów) | Sprawdź plik w edytorze JSON lub walidatorze online |
| `Cannot read norms file` | Zła ścieżka lub brak pliku | Upewnij się, że plik istnieje i ścieżka jest poprawna |

---

## Nota o wersji v2.0

W przyszłej wersji aplikacji planowany jest **formularz graficzny** do wprowadzania norm bez edycji JSON. W MVP (S-04) wymiana odbywa się wyłącznie przez podmianę pliku `norms.json` i walidację CLI opisaną powyżej.

---

## Przywracanie domyślnej bazy

Jeśli podmieniony plik jest uszkodzony:

1. Skopiuj ponownie `norms.json.template` jako `norms.json`, **lub**
2. Przywróć oryginalny `norms.json` z archiwum instalacyjnego placówki.

Następnie uruchom `--validate-norms norms.json` i dopiero potem aplikację.
