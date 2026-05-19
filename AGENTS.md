# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

NeuroFlag is a single-service Python/FastAPI web app that analyzes EDF brain signal files. No database, no Docker, no external services required.

### Running the application

- **Dev server:** `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` (from repo root)
- **Tests:** `pytest -q`
- **Health check:** `curl http://127.0.0.1:8000/health`
- No linter is configured in this project.

### Key notes

- The CI targets Python 3.11 (`.github/workflows/python-app.yml`), but the app works on 3.12+ as well.
- The `mne` library is the heaviest dependency and takes the most time to install.
- All application state is in-memory (`app.state`); restarting the server resets uploaded files and results.
- To test the full workflow via CLI, create test EDF files with `mne`, then use curl to POST to `/upload/norm`, `/upload/data`, `/compare`, and GET `/report` and `/result`.
- The frontend is served at `/` (vanilla HTML/JS, no build step).
- The UI and messages are in Polish.
