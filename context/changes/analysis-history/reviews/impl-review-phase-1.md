<!-- IMPL-REVIEW-REPORT -->
# Implementation Review: Historia badań — lokalna baza SQLite

- **Plan**: context/changes/analysis-history/plan.md
- **Scope**: Phase 1 of 5 (Warstwa storage — `app/storage/`)
- **Date**: 2026-07-01
- **Verdict**: APPROVED
- **Findings**: 0 critical  2 warnings  4 observations

## Verdicts

| Dimension | Verdict |
|-----------|---------|
| Plan Adherence | WARNING ⚠️ (1 finding) |
| Scope Discipline | WARNING ⚠️ (1 finding) |
| Safety & Quality | WARNING ⚠️ (1 finding) |
| Architecture | PASS ✅ |
| Pattern Consistency | PASS ✅ |
| Success Criteria | WARNING ⚠️ (1 finding) |

► Overall: **APPROVED**

## Automated Verification

| Check | Result |
|-------|--------|
| `pytest tests/unit/test_history.py -q` | ✅ 13 passed |
| `mypy app/storage/history.py --strict` | ✅ no issues |
| `ruff check app/storage/history.py` | ✅ all checks passed |

## Manual Verification

| Check | Result |
|-------|--------|
| 1.4 `HistoryStore(resolve_history_db_path()).has_any()` → `False` | ✅ verified live |

## Findings

### F1 — `birth_date` → `birth_year`: drift nie odnotowany w Phase 1

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Plan Adherence
- **Location**: `app/storage/history.py:19` + `_CREATE_STUDIES` string

- **Detail**: Plan Phase 1 deklaruje `birth_date: str | None` w `StudyRecord` i kolumnę
  `birth_date` w schemacie SQLite. Implementacja używa `birth_year` w obu miejscach.
  Zmiana jest właściwa (spójna z `PatientMetadata.birth_year` dodanym w Phase 2) i
  udokumentowana w progress Phase 2 (`plan.md:524`), ale w progress Phase 1 nie ma
  adnotacji o odchyleniu.

- **Fix**: Dodaj notatkę w progress Phase 1 planu (bezpośrednio po `- [x] 1.4`) analogiczną
  do tej w Phase 2: `> Odchylenie od planu: birth_date → birth_year (spójność z PatientMetadata)`.

- **Decision**: FIXED — dodana nota odchylenia do progress Phase 1 w plan.md

---

### F2 — `list_for_patient()` dodana w Phase 1, poza zakresem

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Scope Discipline
- **Location**: `app/storage/history.py:168`

- **Detail**: Metoda `list_for_patient(initials, birth_year, custom_label, limit)` nie
  figuruje w planie Phase 1 ani Phase 4 (który opisuje tylko `HistoryView` bez detali API
  storage). Dodana z wyprzedzeniem, bo Phase 4 (`HistoryView`) ją potrzebuje. Progress Phase 4
  odnotowuje filtrowanie pacjenta jako odchylenie, ale nie wspomina o metodzie storage.

- **Fix**: Dodaj wzmiankę w progress Phase 1 lub Phase 4: `> Dodano HistoryStore.list_for_patient()
  w ramach Phase 1 na potrzeby filtrowania w Phase 4.`

- **Decision**: FIXED via Fix A — objęte notą odchylenia F1 w progress Phase 1

---

### F3 — `_rows_to_records`: brak guard dla `ValueError` w `fromisoformat`

- **Severity**: ⚠️ WARNING
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Safety & Quality
- **Location**: `app/storage/history.py:140`

- **Detail**: `datetime.fromisoformat(row["analyzed_at"])` rzuca `ValueError` gdy
  wartość w bazie jest uszkodzona lub ma nieoczekiwany format. Jeden zły rekord
  spowoduje crash całej metody `list_recent` / `list_for_patient` i błąd w UI.
  Ryzyko niskie dla normalnej pracy, ale niezerowe jeśli DB zostanie ręcznie edytowane
  lub przeniesione z innej wersji aplikacji.

- **Fix**: Owiń parsowanie w `try/except ValueError` — pomiń zły rekord i zaloguj do
  `sys.stderr`, lub rzuć `HistoryStoreError` z czytelnym komunikatem.

- **Decision**: FIXED — `_rows_to_records` owiędnięte w try/except ValueError z logiem do stderr

---

### F4 — `exclusions_json`: pole write-only bez dokumentacji

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Architecture
- **Location**: `app/storage/history.py:108` (zapis) + `_CREATE_STUDIES:72` (schemat)

- **Detail**: `exclusions_json` jest zapisywane przy `add()` i istnieje w schemacie,
  ale nie jest selekcjonowane w `list_recent` / `list_for_patient` ani obecne
  w `StudyRecord`. W planie Phase 1 `StudyRecord` nie ma tego pola (asymetria celowa),
  lecz brak komentarza `# write-only: reserved for v2.0` utrudnia zrozumienie przyszłemu
  recenzentowi.

- **Fix**: Dodaj komentarz `# write-only: persisted for v2.0 trend analysis` przy
  `exclusions_json` w `_serialize_cells` lub przy kolumnie w `_CREATE_STUDIES`.

- **Decision**: FIXED — komentarz dodany przy kolumnie w `_CREATE_STUDIES`

---

### F5 — Brak testów dla `eeg_path`, `resolve_history_db_path()` i `list_for_patient`

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Success Criteria
- **Location**: `tests/unit/test_history.py`

- **Detail**: Plan Phase 5 definiuje 13 testów — wszystkie przechodzą. Jednak trzy
  obszary nie są pokryte:
  - `add(..., eeg_path=some_path)` → czy `eeg_filename` poprawnie zapisane i odczytane?
  - `resolve_history_db_path()` — ścieżka dev vs frozen (`sys.frozen`).
  - `list_for_patient` — logika OR, fallback do `list_recent`, kombinacje pól.

- **Fix**: Dodaj trzy testy w `tests/unit/test_history.py`:
  - `test_add_with_eeg_path`
  - `test_resolve_history_db_path_dev`
  - `test_list_for_patient_*` (3–4 przypadki)

- **Decision**: FIXED — dodano 5 testów: `test_add_with_eeg_path`, `test_add_without_eeg_path_eeg_filename_none`, `test_resolve_history_db_path_dev`, `test_list_for_patient_by_initials_and_birth_year`, `test_list_for_patient_no_criteria_returns_all`, `test_list_for_patient_by_custom_label`. Łącznie 19 testów przechodzi.

---

### F6 — `cur.lastrowid`: `type: ignore[assignment]` zamiast assert

- **Severity**: OBSERVATION
- **Impact**: 🏃 LOW — quick decision; fix is obvious and narrowly scoped
- **Dimension**: Pattern Consistency
- **Location**: `app/storage/history.py:133`

- **Detail**: `row_id: int = cur.lastrowid  # type: ignore[assignment]` wycisza mypy,
  bo `lastrowid` jest `int | None` (None gdy operacja nie jest INSERT lub nie zwróciła
  rowid). W tym miejscu zawsze jest INSERT, więc None jest niemożliwe w runtime —
  ale `type: ignore` nie wyraża tej niezmienności i maskuje potencjalny bug gdyby
  SQL został zmieniony.

- **Fix**: Zamień na:
  ```python
  assert cur.lastrowid is not None, "INSERT did not return a rowid"
  return cur.lastrowid
  ```

- **Decision**: FIXED — zastąpiono `type: ignore[assignment]` przez `assert ... is not None`
