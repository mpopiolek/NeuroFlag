# run.ps1 - tworzy/aktywuje venv i uruchamia serwer FastAPI (PowerShell)
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

# Aktywuj środowisko
. .\.venv\Scripts\Activate.ps1

# Zainstaluj zależności (opcjonalnie, wykona się tylko jeśli nie ma zainstalowanych pakietów)
pip install -r requirements.txt

# Uruchom serwer deweloperski
uvicorn app.main:app --reload
