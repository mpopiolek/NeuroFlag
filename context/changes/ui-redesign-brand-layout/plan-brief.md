# Redesign UI — Wariant B — Plan Brief

> Full plan: `context/changes/ui-redesign-brand-layout/plan.md`
> Research: `context/changes/ui-redesign-brand-layout/research.md`

## What & Why

Przebudowa interfejsu NeuroFlag według **Wariantu B**: stały nagłówek z poziomym stepperem, układ dwukolumnowy (formularz + panel kontekstu), dashboard wyników i spójna stopka nawigacji. Celem jest lepsza hierarchia wizualna, wykorzystanie przestrzeni ekranu i spójność z charakterem ulotki NEUROD (granat + pomarańcz + subtelny miętowy akcent) — bez zmiany kolorów wyników klinicznych RAG.

## Starting Point

Aplikacja to jednokolumnowy wizard CustomTkinter (~720 px treści po lewej) z pomarańczem na wszystkich kontrolkach CTk. Shell ma tylko przycisk „Informacje”; każdy widok sam układa nawigację. Tokeny w `theme.py` + `neuroflag.json`; kolory RAG w `rag_colors.py` (sztywne).

## Desired End State

Użytkownik widzi nagłówek z logo NeuroFlag, stepperem (Dane → Plik → Analiza → Wynik) i skrótami Informacje/Historia. Kroki formularza mają panel kontekstu po prawej (RODO, wymagania pliku). Stopka zawsze w tym samym miejscu: Wstecz | primary CTA. Wyniki w układzie dashboard; historia z chipami kategorii. Pomarańcz tylko na głównych akcjach; kontrolki formularza w granacie.

## Key Decisions Made

| Decision | Choice | Why | Source |
|----------|--------|-----|--------|
| Wariant layoutu | B — nagłówek + 2 kolumny | Wybór użytkownika; lepszy dashboard wyników | Plan |
| Tło miętowe | Tylko pasek 4 px pod nagłówkiem | Spokojniejszy UI medyczny; nod do ulotki | Research |
| Kolory kontrolek | Granat `#1E3A5F`, nie pomarańcz | Pomarańcz wyłącznie na CTA; odróżnienie od RAG żółci | Research |
| Kolory RAG | Bez zmian | Twarde reguły domenowe / PRD | Research |
| Stopka nawigacji | W shell (`AppWindow`), nie w widokach | Spójny UX, jeden primary na ekran | Plan |
| PDF | Poza zakresem | Redesign dotyczy aplikacji desktop | Plan |
| Logo mózgu | Tekst „NeuroFlag”; asset PNG opcjonalny później | Brak gotowego assetu w repo | Plan |
| Responsywność | Stack kolumn przy <900 px | `minsize(900,640)` — musi działać na minimum | Plan |

## Scope

**In scope:** `theme.py`, `neuroflag.json`, `widgets.py`, shell `app_window.py`, stepper, wszystkie widoki, `info_dialog.py`, testy theme/navigation

**Out of scope:** kolory RAG, PDF redesign, dark mode, ikona exe, drag & drop, rename NEUROD

## Architecture / Approach

```
AppWindow (shell)
├── header: logo + WorkflowStepper + Informacje/Historia
├── mint stripe (4px)
├── view_host: widoki z two_column_body lub dashboard
└── footer: set_footer() z widoku

Widoki: logika bez zmian → nowy layout + delegacja przycisków do shell
```

5 faz: tokeny → shell → formularze → wyniki/historia/info → overlay/modal (UX polish).

## Phases at a Glance

| Phase | What it delivers | Key risk |
|-------|------------------|----------|
| 1. Tokeny i prymitywy | Paleta B, widgets, context_copy | Test theme musi rozdzielić accent vs control |
| 2. Shell | Nagłówek, stepper, stopka | Stepper vs widoki opcjonalne (mapowanie) |
| 3. Formularze | Metadata + import 60/40 | Resize/stack kolumn w CTk |
| 4. Wyniki i historia | Dashboard, chipy, info dialog | Skalowanie siatki RAG |
| 5. UX przejść | Overlay analizy, modal mapowania | Wątki analizy + overlay lifecycle |

**Prerequisites:** CustomTkinter 5.2.2, istniejący flow wizarda  
**Estimated effort:** ~3–4 sesje implementacji (5 faz)

## Open Risks & Assumptions

- CTk `grid` + dynamiczny resize może wymagać `after_idle` — wzorzec już w `bind_auto_hide_scrollbar`
- Phase 5 (overlay) jest bardziej złożona — aplikacja używalna po Phase 4
- Brak testów GUI — regresje wizualne tylko manualnie

## Success Criteria (Summary)

- Pełny flow badania działa bez regresji funkcjonalnej
- Wygląd zgodny z mockupem Wariantu B (nagłówek, 2 kolumny, dashboard)
- `pytest` + `mypy --strict` pass; RAG kolory niezmienione
