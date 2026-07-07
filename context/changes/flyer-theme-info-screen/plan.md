# Motyw z ulotki i ekran Informacje — Implementation Plan

## Overview

Dostosowanie akcentów kolorystycznych NeuroFlag do ulotki NEUROD (pomarańczowe CTA,
granatowe nagłówki sekcji) oraz dodanie stałego dostępu do informacji o produkcie
i kontaktów przez przycisk „Informacje” w pasku chrome `AppWindow`. Dialog zawiera
konsultacje merytoryczne (dr Małgorzata Chojak, UMCS), wsparcie techniczne aplikacji
(Małgorzata Popiołek) i link do zgłaszania błędów na publicznym GitHubie. Stopka PDF
oraz repozytorium (szablon issue + README) zostają uzupełnione o te same kanały.

## Current State Analysis

- Motyw CTk: `app/ui/theme.py:15-29` definiuje `COLOR_ACCENT = "#2563A8"`; `neuroflag.json`
  używa tego niebieskiego dla przycisków, checkboxów, paska postępu i option menu.
- Nawigacja: `AppWindow.show_view()` (`app/ui/app_window.py:57-67`) niszczy i tworzy
  widoki bezpośrednio jako dzieci okna — brak globalnego chrome.
- Treść informacyjna: `info_box` z tekstem RODO/offline tylko w `MetadataFormView`
  (`app/ui/views/metadata_form.py:183-192`); brak kontaktów i GitHub.
- PDF: stopka to `NeuroFlag v{version} | {data}` (`app/reports/pdf_generator.py:262-265`).
- RAG: `app/ui/components/rag_colors.py` — kolory wyników muszą pozostać bez zmian.
- PyInstaller bundluje `app/ui/assets` (`neuroflag.spec:69`) — wystarczy dla `neuroflag.json`.
- Testy UI: brak testów widoków; `tests/unit/test_deps.py` sprawdza import CTk na Windows.

## Desired End State

1. Przycisk „Informacje” widoczny w prawym górnym rogu na każdym kroku flow analizy.
2. Kliknięcie otwiera przewijany dialog CTk z sekcjami: Produkt, Wartości, Kontakt
   merytoryczny, Wsparcie techniczne (+ URL GitHub i przycisk otwierający issues/new).
3. Przyciski akcji (primary) i akcenty CTk w pomarańczu `#F9A825`; nagłówki sekcji
   dialogu w granacie `#283593`. Tła formularzy bez pełnej mięty z ulotki.
4. Kolory komórek RAG identyczne jak przed zmianą.
5. `info_box` RODO na ekranie „Dane dziecka” bez zmian treści.
6. Stopka PDF z oboma kontaktami pod klauzulą odpowiedzialności.
7. Repozytorium: polski szablon bug report + sekcja Kontakt w README.

Weryfikacja: uruchomić aplikację, przejść cały flow, sprawdzić dialog na każdym widoku,
wygenerować PDF, otworzyć link GitHub (ręcznie), uruchomić `pytest -q` i `mypy app/ --strict`.

### Key Discoveries:

- Wzorzec modala: `_EditStudyDialog` w `app/ui/views/history.py:281-359` — CTkToplevel
  ze scrollowalną treścią i przyciskami akcji.
- Wzorzec stałego nagłówka: `HistoryView` (`history.py:52-62`) — `header_row` z tytułem
  i przyciskiem po prawej; chrome w `AppWindow` uogólnia ten wzorzec.
- Jedyny precedens `messagebox` dla RODO: `analysis.py` — dialog info powinien być CTk,
  nie natywny messagebox.

## What We're NOT Doing

- Pełna paleta tła (mięta `#A8C4BC`) na całym oknie aplikacji.
- Osadzanie PNG/JPG z ulotki (mózg, wykres fal EEG).
- Zmiana nazwy okna lub produktu na NEUROD(6-10).
- Wzmianka o NEUROD w treści dialogu (decyzja użytkowniczki).
- Modyfikacja kolorów RAG w `rag_colors.py` ani w tabeli PDF siatki wyników.
- Telemetria, auto-report crashy, integracja z GitHub API z poziomu aplikacji.
- Ikona `.exe` z ulotki (`neuroflag.spec:142` pozostaje zakomentowana).

## Implementation Approach

Trzy fazy sekwencyjne: najpierw kolory (niskie ryzyko regresji wizualnej poza akcentami),
potem chrome + dialog (główna funkcja użytkownika), na końcu PDF i repo (dokumentacja
poza runtime GUI). Treści kontaktowe w jednym module `info_content.py` — single source
of truth dla dialogu, PDF i README (README może skrócić, ale dane identyczne).

## Critical Implementation Details

Dialog musi zawierać zdanie, że otwarcie GitHub to **jedyna** akcja wymagająca internetu
(aplikacja analizy pozostaje offline). Przycisk GitHub używa `webbrowser.open(GITHUB_NEW_ISSUE_URL)`
— nie importować `http` w głównym flow analizy poza handlerem przycisku.

Po dodaniu chrome w `AppWindow` widoki montowane w `_view_host`, nie bezpośrednio w `self`.
`page_container` zachowuje obecne marginesy — nie zmniejszać wysokości okna poniżej `minsize`.

**Phase 1 — kolory CTk:** `COLOR_ACCENT` w `theme.py` nie jest dziś importowany przez widoki —
widoczne akcenty CTk (przyciski, checkboxy, progress) pochodzą wyłącznie z `neuroflag.json`.
Aktualizacja samego `theme.py` **nie zmienia UI**. Item 2 Phase 1 (`neuroflag.json`) jest
obowiązkowy dla Desired End State; `COLOR_ACCENT` / `COLOR_SECTION_NAVY` służą nowemu kodowi
Python (nagłówki sekcji w `info_dialog`).

---

## Phase 1: Motyw akcentów z ulotki

### Overview

Zastąpienie niebieskiego akcentu CTk pomarańczem z ulotki; dodanie stałej granatu
do użycia w dialogu Informacje. Powierzchnie i tekst bez pełnej przebudowy.

### Changes Required:

#### 1. Stałe kolory semantyczne

**File**: `app/ui/theme.py`

**Intent**: Zdefiniować paletę akcentów z ulotki obok istniejących kolorów tekstu/surface;
zaktualizować `COLOR_ACCENT` na pomarańcz CTA.

**Contract**:
- `COLOR_ACCENT = "#F9A825"` (pomarańcz — przyciski primary, progress)
- `COLOR_ACCENT_HOVER = "#E09000"` (ciemniejszy hover)
- `COLOR_SECTION_NAVY = "#283593"` (nagłówki sekcji w dialogu info)
- `COLOR_ON_NAVY = "#FFFFFF"` (tekst na granatowym tle sekcji)
- Pozostałe `COLOR_TEXT`, `COLOR_SURFACE`, `COLOR_BORDER` — bez zmian (akcent-only scope)

#### 2. Motyw JSON CustomTkinter

**File**: `app/ui/assets/themes/neuroflag.json`

**Intent**: Przenieść pomarańcz akcentu na wszystkie widgety CTk używające `fg_color`
primary (Button, CheckBox, RadioButton, Switch progress, ProgressBar, OptionMenu,
SegmentedButton selected).

**Contract**: Zamiana `#2563A8` / `#1D4F8C` / `#1F6AA5` / `#144870` na wartości z
`theme.py` (pomarańcz + hover). `CTkFrame`/`CTk` tła bez zmian na miętę.
`primary_button()` w `widgets.py` deleguje do motywu CTk — po aktualizacji JSON
przyciski primary odziedziczą pomarańcz bez zmian w `widgets.py` (verify-only w manual).

### Success Criteria:

#### Automated Verification:

- `python -m pytest -q` — wszystkie testy przechodzą
- `mypy app/ --strict` — bez błędów typów

#### Manual Verification:

- Uruchomić `python app/main.py` — przyciski „Dalej”, checkboxy i pasek postępu w pomarańczu
- Siatka wyników (po analizie testowej lub mock) — kolory RAG identyczne jak przed zmianą;
  na `ResultsGridView` porównać obok siebie pomarańcz przycisków (`#F9A825`) vs żółte
  komórki RAG (`#F5A800`) — muszą być rozróżnialne wizualnie
- Czytelność tekstu na przyciskach primary (biały na pomarańczu)

**Implementation Note**: Po tej fazie i przejściu automated verification — potwierdzenie manualne przed Phase 2.

---

## Phase 2: Chrome AppWindow + dialog Informacje

### Overview

Stały pasek z przyciskiem „Informacje” oraz modal CTk z treścią produktu, wartościami,
kontaktami i linkiem GitHub.

### Changes Required:

#### 1. Moduł treści informacyjnych

**File**: `app/ui/info_content.py` (nowy)

**Intent**: Centralne stałe tekstów PL i URL — single source dla dialogu, PDF (Phase 3) i README.

**Contract**:
```python
GITHUB_REPO_URL: str = "https://github.com/mpopiolek/NeuroFlag"
GITHUB_NEW_ISSUE_URL: str = f"{GITHUB_REPO_URL}/issues/new"

@dataclass(frozen=True)
class ContactInfo:
    name: str
    role: str
    phone: str | None
    email: str

EXPERT_CONTACT: ContactInfo  # dr Małgorzata Chojak, UMCS
TECH_CONTACT: ContactInfo    # Małgorzata Popiołek

PRODUCT_DESCRIPTION: str     # z ulotki: przesiew 6-10 lat, EEG
VALUE_BULLETS: tuple[str, ...]  # skrócone hasła z niebieskiej sekcji ulotki
OFFLINE_NOTE: str            # wyjątek: GitHub wymaga internetu
```

Treść eksperta (z ulotki): dr Małgorzata Chojak, Kierownik Laboratorium Badań nad
Neuroedukacją UMCS, tel. 508 216 957, malgorzata.chojak@mail.umcs.pl.
Techniczny: Małgorzata Popiołek, malgorzata.pe@gmail.com.

#### 2. Komponent dialogu

**File**: `app/ui/components/info_dialog.py` (nowy)

**Intent**: `InfoDialog(ctk.CTkToplevel)` — modal z `CTkScrollableFrame`, sekcjami
(granatowy nagłówek + treść), przyciskiem „Zgłoś błąd na GitHubie” (`webbrowser.open`),
wyświetlonym URL i przyciskiem „Zamknij”.

**Contract**:
```python
def show_info_dialog(parent: ctk.CTk, *, app_window: ctk.CTk) -> None: ...
```
- `transient(parent)`, `grab_set()`, wyśrodkowanie względem `app_window`
- Sekcje: Produkt, Wartości (lista punktów), Konsultacje merytoryczne, Problemy z aplikacją
- W sekcji technicznej: e-mail, URL repo, przycisk otwierający `GITHUB_NEW_ISSUE_URL`
- Tekst `OFFLINE_NOTE` widoczny przy przycisku GitHub
- Bez wzmianki NEUROD w tytule — tytuł okna dialogu: „Informacje — NeuroFlag”

#### 3. Shell okna z chrome

**File**: `app/ui/app_window.py`

**Intent**: Dodać `_shell` → `_chrome` (przycisk Informacje) + `_view_host`; `show_view`
montuje widoki w `_view_host`.

**Contract**:
- Metoda `_show_info()` wywołuje `show_info_dialog(self, app_window=self)`
- Przycisk: `widgets.secondary_button(_chrome, text="Informacje", command=self._show_info, width=120).pack(side="right")`
- `show_view`: `master=self._view_host` zamiast `master=self`
- Tytuł okna bez zmian: „NeuroFlag — Badanie przesiewowe EEG”
- Poszerzyć parametr `master` we **wszystkich** widokach flow (`MetadataFormView`,
  `FileImportView`, `ChannelMappingView`, `AnalysisView`, `ResultsGridView`, `HistoryView`)
  z `ctk.CTk` na `ctk.CTkBaseClass` — `_view_host` to `CTkFrame`; wymagane dla `mypy --strict`

#### 4. Eksport komponentu

**File**: `app/ui/components/__init__.py`

**Intent**: Opcjonalnie wyeksportować `show_info_dialog` jeśli inne moduły importują z pakietu.

**Contract**: Import z `app.ui.components.info_dialog` działa bez cykli z `app_window`.

#### 5. Test jednostkowy treści (bez Tk)

**File**: `tests/unit/test_info_content.py` (nowy)

**Intent**: Sprawdzić obecność kluczowych fragmentów (e-maile, URL GitHub, opis produktu).

**Contract**:
- Assert `TECH_CONTACT.email == "malgorzata.pe@gmail.com"`
- Assert `"github.com/mpopiolek/NeuroFlag" in GITHUB_NEW_ISSUE_URL`
- Assert `EXPERT_CONTACT.phone` zawiera „508”
- Assert brak słowa „NEUROD” w `PRODUCT_DESCRIPTION` (decyzja brandingowa)

### Success Criteria:

#### Automated Verification:

- `python -m pytest tests/unit/test_info_content.py -q` — przechodzi
- `python -m pytest -q` — pełna suite zielona
- `mypy app/ --strict` — bez błędów

#### Manual Verification:

- Przycisk „Informacje” widoczny na: Dane dziecka, Import, Mapowanie kanałów, Analiza, Wyniki, Historia
- Dialog przewija się przy małym oknie; „Zamknij” zamyka modal
- Klik „Zgłoś błąd na GitHubie” otwiera przeglądarkę na `/issues/new`
- `info_box` RODO na pierwszym ekranie nadal obecny z tą samą treścią

**Implementation Note**: Po manual verification — przejść do Phase 3.

---

## Phase 3: Stopka PDF, szablon GitHub, README

### Overview

Spójne kontakty na wydruku PDF oraz dokumentacja zgłaszania błędów w repozytorium.

### Changes Required:

#### 1. Stopka raportu PDF

**File**: `app/reports/pdf_generator.py`

**Intent**: Pod linią wersji/daty dodać dwa wiersze kontaktów z `info_content.py`.

**Contract**:
- Import `EXPERT_CONTACT`, `TECH_CONTACT` z `app.ui.info_content`
- Po `Paragraph(f"NeuroFlag v{__version__} | {footer_date}", style_footer)` dodać:
  - Linia merytoryczna: imię, rola skrócona, tel., e-mail eksperta
  - Linia techniczna: imię, e-mail wsparcia, URL repo (bez hyperlinku — ReportLab plain text)
- Styl: istniejący `style_footer` lub `style_small` — mniejsza czcionka, nie psuje layoutu A4

#### 2. Test PDF stopki

**File**: `tests/unit/test_pdf_generator.py` (istniejący lub nowy — sprawdzić repo)

**Intent**: Assert wygenerowany PDF (bytes) zawiera oba adresy e-mail kontaktów.

**Contract**: Jeśli plik testowy istnieje — rozszerzyć; jeśli nie — dodać minimalny test
generacji z mock metadata/result i `in` check na bytes (UTF-8 lub latin-1 decode).

#### 3. Szablon zgłoszenia błędu

**File**: `.github/ISSUE_TEMPLATE/bug_report.md` (nowy)

**Intent**: Polski szablon issue z polami: wersja NeuroFlag, Windows, kroki reprodukcji,
oczekiwane vs rzeczywiste, załącznik zrzutu.

**Contract** (nagłówek frontmatter YAML):
```yaml
---
name: Zgłoszenie błędu
about: Problem z aplikacją NeuroFlag (Windows)
title: "[Bug] "
labels: bug
---
```
Treść sekcji po polsku; link do repo; informacja że analiza EEG jest offline.

#### 4. Sekcja Kontakt w README

**File**: `README.md`

**Intent**: Dodać sekcję „Kontakt i wsparcie” z tymi samymi danymi co dialog + link do Issues.

**Contract**:
- Podsekcje: Konsultacje merytoryczne (EEG) / Wsparcie techniczne / Zgłaszanie błędów (GitHub)
- E-maile i telefon eksperta zgodne z `info_content.py`
- Link: `https://github.com/mpopiolek/NeuroFlag/issues`

#### 5. Test spójności README ↔ info_content

**File**: `tests/unit/test_info_content.py` (rozszerzenie)

**Intent**: Wykryć drift między README a modułem treści — README nie importuje Pythona,
ale e-maile muszą pozostać zsynchronizowane.

**Contract**:
- Test odczytuje `README.md` z root projektu
- Assert: `EXPERT_CONTACT.email` i `TECH_CONTACT.email` występują w treści README

### Success Criteria:

#### Automated Verification:

- `python -m pytest -q` — w tym test stopki PDF jeśli dodany
- `mypy app/ --strict`
- Plik `.github/ISSUE_TEMPLATE/bug_report.md` istnieje

#### Manual Verification:

- Wygenerować PDF z aplikacji — stopka zawiera oba kontakty, czytelna na A4
- Na GitHubie: „New issue” pokazuje szablon „Zgłoszenie błędu” (po push)
- README renderuje sekcję Kontakt poprawnie

**Implementation Note**: Po push na GitHub — jednorazowo sprawdzić szablon issue w UI repo.

---

## Testing Strategy

### Unit Tests:

- `test_info_content.py` — stałe kontaktów, URL, brak NEUROD w opisie
- Rozszerzenie/weryfikacja testu PDF — obecność e-maili w bytes output

### Integration Tests:

- Brak nowych testów E2E GUI (headless CI); manual smoke w `distribution.md` opcjonalnie uzupełnić punktem „Informacje na każdym ekranie”

### Manual Testing Steps:

1. Uruchomić aplikację — sprawdzić pomarańcz primary na każdym ekranie
2. Otworzyć Informacje na każdym widoku — scroll, zamknięcie, treść PL
3. Kliknąć link GitHub — strona new issue w przeglądarce
4. Przeprowadzić analizę (lub wczytać znany plik) — kolory RAG bez zmian
5. Zapisać PDF — stopka z kontaktami
6. `dist/neuroflag/neuroflag.exe --smoke-test` po buildzie (jeśli dystrybucja w toku)

**Obowiązkowy smoke przed release (poza CI):** `--smoke-test` weryfikuje tylko `norms.load()` —
nie uruchamia GUI. Przed przekazaniem placówce ręcznie potwierdzić: przycisk Informacje na
każdym ekranie flow, dialog + GitHub, stopka PDF z kontaktami (patrz Phase 2.4 i 3.4).

## Performance Considerations

Dialog tworzony on-demand — brak wpływu na start aplikacji. `webbrowser.open` jednorazowo
przy kliknięciu. Import `info_content` w PDF generatorze — lekki moduł stringów.

## Migration Notes

Brak migracji danych. Użytkownicy po aktualizacji `.exe` widzą nowe kolory i przycisk Informacje
od razu. Istniejące PDF-y historyczne bez kontaktów w stopce — oczekiwane.

## References

- Motyw: `app/ui/theme.py`, `app/ui/assets/themes/neuroflag.json`
- Nawigacja: `app/ui/app_window.py`
- Wzorzec modala: `app/ui/views/history.py:281-359`
- PDF stopka: `app/reports/pdf_generator.py:262-265`
- RAG (niezmieniane): `app/ui/components/rag_colors.py`
- Ulotka NEUROD — źródło treści i palety (materiał użytkowniczki)

## Progress

> Convention: `- [ ]` pending, `- [x]` done. Append ` — <commit sha>` when a step lands. Do not rename step titles.

### Phase 1: Motyw akcentów z ulotki

#### Automated

- [x] 1.1 `python -m pytest -q` — wszystkie testy przechodzą
- [x] 1.2 `mypy app/ --strict` — bez błędów typów

#### Manual

- [x] 1.3 Przyciski pomarańcz; RAG bez zmian; pomarańcz vs żółty RAG rozróżnialne na wynikach

### Phase 2: Chrome AppWindow + dialog Informacje

#### Automated

- [ ] 2.1 `python -m pytest tests/unit/test_info_content.py -q` — przechodzi
- [ ] 2.2 `python -m pytest -q` — pełna suite zielona
- [ ] 2.3 `mypy app/ --strict` — bez błędów

#### Manual

- [ ] 2.4 Przycisk Informacje na wszystkich widokach; dialog, GitHub, info_box RODO

### Phase 3: Stopka PDF, szablon GitHub, README

#### Automated

- [ ] 3.1 `python -m pytest -q` — w tym test stopki PDF
- [ ] 3.2 `mypy app/ --strict`
- [ ] 3.3 Plik `.github/ISSUE_TEMPLATE/bug_report.md` istnieje

#### Manual

- [ ] 3.4 PDF ze stopką kontaktów; szablon issue na GitHubie po push
