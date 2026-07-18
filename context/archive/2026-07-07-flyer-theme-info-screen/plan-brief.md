# Motyw z ulotki i ekran Informacje — Plan Brief

> Full plan: `context/changes/flyer-theme-info-screen/plan.md`

## What & Why

NeuroFlag ma wyglądać spójnie z materiałem NEUROD (akcenty pomarańczowe i granatowe)
oraz udostępniać stały dostęp do informacji o produkcie i kontaktów: konsultacje
merytoryczne EEG (dr Małgorzata Chojak, UMCS) oraz wsparcie techniczne aplikacji
(Małgorzata Popiołek, e-mail i GitHub). Placówki pracują offline — wyjątkiem jest
świadome otwarcie strony zgłoszenia błędu w przeglądarce.

## Starting Point

Motyw CTk (`app/ui/theme.py`, `neuroflag.json`) używa chłodnej palety niebiesko-szarej
(`#2563A8`). Brak globalnego paska nawigacji — każdy widok buduje własny layout.
Tekst o prywatności/offline jest tylko w `info_box` na pierwszym ekranie (`metadata_form.py`).
Stopka PDF zawiera wyłącznie wersję i datę (`pdf_generator.py:264`). Repozytorium GitHub
jest publiczne, bez szablonu issue ani sekcji Kontakt w README.

## Desired End State

Przycisk „Informacje” widoczny na każdym kroku analizy otwiera przewijany dialog CTk
z opisem produktu, wartościami, dwoma blokami kontaktowymi i przyciskiem otwierającym
`https://github.com/mpopiolek/NeuroFlag/issues/new` w przeglądarce (obok widoczny URL).
Przyciski akcji i akcenty UI używają pomarańczu z ulotki; sekcje dialogu — granatu.
Kolory RAG w siatce wyników bez zmian. Stopka PDF zawiera oba kontakty. Repo ma polski
szablon bug report i sekcję Kontakt w README.

## Key Decisions Made

| Decision | Choice | Why (1 sentence) | Source |
| -------- | ------ | ---------------- | ------ |
| Głębokość motywu | Akcenty z ulotki (pomarańcz CTA, granat sekcji) | Spójność wizualna bez ryzyka dla czytelności formularzy i RAG | Plan |
| Kolory wyników RAG | Bez zmian | Reguła domenowa — czerwony/żółty/zielony mają znaczenie kliniczne | AGENTS.md |
| Forma ekranu info | Modal CTkToplevel + stały chrome w AppWindow | Działa na każdym kroku bez komplikacji nawigacji | Plan |
| Grafiki z ulotki | Tylko tekst i kolory | Prostszy build, brak assetów PNG | Plan |
| GitHub | Przycisk otwiera przeglądarkę + widoczny URL | Szybkie zgłoszenia dla osób technicznych przy zachowaniu komunikatu offline | Plan |
| info_box na starcie | Zostaje + pełny dialog | RODO/offline widoczne od razu bez dodatkowego kliknięcia | Plan |
| Branding NEUROD | Bez wzmianki — tylko NeuroFlag | Spójność z nazwą okna i README | Plan |
| Stopka PDF | Oba kontakty (merytoryczny + techniczny) | Kontakt dostępny na wydrukowanym raporcie | Plan |
| Repozytorium | Szablon issue + README Kontakt | Lepsze zgłoszenia i widoczność kanałów poza aplikacją | Plan |

## Scope

**In scope:**
- Stałe kolory akcentów w `theme.py` i `neuroflag.json` (pomarańcz `#F9A825`, granat `#283593`)
- Stały pasek chrome w `AppWindow` z przyciskiem „Informacje”
- Moduł treści + dialog informacyjny (produkt, wartości, kontakty, GitHub)
- Rozszerzenie stopki PDF o oba kontakty
- `.github/ISSUE_TEMPLATE/bug_report.md` (polski)
- Sekcja „Kontakt / wsparcie” w `README.md`

**Out of scope:**
- Pełna przebudowa tła aplikacji na miętę z ulotki
- Osadzanie grafik (mózg, fale EEG) z ulotki
- Zmiana nazwy produktu na NEUROD(6-10)
- Zmiana kolorów RAG w wynikach i PDF siatki
- Automatyczne wysyłanie raportów błędów z aplikacji (telemetria)
- Ikona `.exe` / favicon z ulotki

## Architecture / Approach

```
app/ui/
  theme.py              ← COLOR_ACCENT (pomarańcz), COLOR_SECTION_NAVY (granat)
  assets/themes/neuroflag.json
  info_content.py       ← stałe teksty PL (produkt, kontakty, URL GitHub)
  components/info_dialog.py  ← CTkToplevel scrollable
  app_window.py         ← _shell / _chrome / _view_host; show_view → _view_host

app/reports/pdf_generator.py  ← stopka z kontaktami

.github/ISSUE_TEMPLATE/bug_report.md
README.md               ← sekcja Kontakt
```

Przycisk GitHub wywołuje `webbrowser.open()` — jedyna akcja wymagająca internetu;
reszta aplikacji pozostaje offline.

## Phases at a Glance

| Phase | What it delivers | Key risk |
| ----- | ---------------- | -------- |
| 1. Motyw akcentów | Pomarańcz/granat w CTk theme | Pomarańcz UI vs żółty RAG — utrzymać rozdzielenie ról |
| 2. Chrome + dialog Informacje | Stały przycisk, treść, link GitHub | Layout okna po dodaniu paska chrome |
| 3. PDF + GitHub + README | Stopka raportu, szablon issue, README | Zbyt długa stopka PDF na A4 |

**Prerequisites:** Brak — niezależna zmiana UI/dokumentacji.
**Estimated effort:** ~1–2 sesje implementacji (3 fazy)

## Open Risks & Assumptions

- Otwarcie GitHub wymaga połączenia z internetem — dialog musi to wyraźnie komunikować obok hasła „aplikacja offline”.
- `webbrowser` na Windows otwiera domyślną przeglądarkę — zachowanie poza kontrolą aplikacji.
- Issues na GitHubie muszą być włączone w ustawieniach repozytorium (publiczne repo — domyślnie tak).
- Użytkownicy bez konta GitHub nadal korzystają z e-maila jako głównego kanału.

## Success Criteria (Summary)

- Przycisk „Informacje” widoczny na wszystkich widokach flow analizy
- Dialog zawiera oba kontakty i otwiera stronę new issue w przeglądarce
- Przyciski „Dalej” / „Analizuj” mają pomarańcz akcentu; kolory komórek RAG bez zmian
- PDF zawiera oba kontakty w stopce; `pytest -q` i `mypy app/ --strict` przechodzą
