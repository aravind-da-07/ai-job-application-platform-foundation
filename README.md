# AI Job Application Platform

A modular, production-oriented platform that automates the job application
lifecycle: parsing resumes into structured data, discovering jobs across
multiple sources, matching them against a candidate profile with AI,
tailoring resumes and cover letters, and — for supported job portals —
filling and submitting applications with full audit tracking and a
Streamlit dashboard.

> **Status: Foundation phase (v0.1.0).** This repository currently contains
> the reusable infrastructure every later module depends on: configuration,
> logging, database access, the repository/service pattern, the API
> skeleton, the event bus, and scheduler infrastructure. Resume Parsing,
> Job Discovery, AI Matching, Browser Automation, and the full Dashboard are
> **not yet implemented** — see [Roadmap](#roadmap) below. Documentation
> only describes what is actually implemented.

## Table of Contents

- [Technology Stack](#technology-stack)
- [Folder Structure](#folder-structure)
- [Installation (Windows)](#installation-windows)
- [Supabase Setup](#supabase-setup)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [Running Tests](#running-tests)
- [Debugging in VS Code](#debugging-in-vs-code)
- [Docker](#docker)
- [Git Workflow](#git-workflow)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

## Technology Stack

| Concern              | Technology                     |
|-----------------------|---------------------------------|
| Backend API            | FastAPI + Uvicorn               |
| Database               | Supabase PostgreSQL             |
| ORM                     | SQLAlchemy 2.x                  |
| File storage            | Supabase Storage                |
| Validation               | Pydantic v2 / pydantic-settings |
| Browser automation        | Playwright (installed, wired in Part 4) |
| Dashboard                 | Streamlit                       |
| Scheduling                 | APScheduler                     |
| Logging                     | Loguru                          |
| Testing                      | pytest, pytest-cov              |
| Formatting / Linting          | Black, Ruff                     |
| Containerization                | Docker, docker-compose          |
| CI/CD                             | GitHub Actions                  |

## Folder Structure

```
AI_JOB_APPLICATION_PLATFORM/
├── docs/                     # Architecture notes, module-specific docs
├── src/
│   ├── api/                  # FastAPI app + routers (system endpoints so far)
│   ├── dashboard/             # Streamlit app
│   ├── modules/               # Domain modules land here (Part 3+): resume_parser, job_discovery, ...
│   └── shared/                 # Infrastructure every module depends on
│       ├── config/                # settings.py, constants.py
│       ├── core/                   # exceptions.py
│       ├── database/                # session.py, base.py
│       ├── models/                   # ORM models (populated per-module)
│       ├── repositories/              # BaseRepository (Repository Pattern)
│       ├── services/                   # BaseService
│       ├── schemas/                     # Shared Pydantic response models
│       ├── middleware/                   # Error handling, request logging
│       ├── events/                        # In-process event bus
│       ├── scheduler/                      # APScheduler wrapper
│       ├── logging/                         # Loguru configuration
│       ├── notifications/                    # Populated in Part 4
│       └── utils/                             # retry, hash, date, file, json helpers
├── tests/
│   ├── unit/
│   └── integration/
├── sql/                       # Numbered SQL migrations, run in order
├── requirements/                # base.txt, dev.txt, prod.txt
├── docker/                       # Dockerfile.dashboard
├── .github/workflows/              # CI pipeline
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

Every directory under `src/shared/` exists because a later module needs it:
`repositories/` and `services/` will be populated by the Resume Parser,
Job Discovery, and Automation modules; `notifications/` is intentionally
empty until Part 4; `modules/` is where each domain feature gets its own
subfolder (e.g. `src/modules/resume_parser/`) so features stay isolated
from shared infrastructure.

## Installation (Windows)

Run these in **Windows PowerShell**, not Command Prompt.

### 1. Install prerequisites

- **Python 3.13+**: download from [python.org](https://www.python.org/downloads/), and during install check "Add python.exe to PATH".
- **Git**: download from [git-scm.com](https://git-scm.com/download/win).
- **VS Code**: download from [code.visualstudio.com](https://code.visualstudio.com/).
- **VS Code extensions**: install `ms-python.python`, `ms-python.black-formatter`, `charliermarsh.ruff`, `ms-azuretools.vscode-docker`.

Verify installs:

```powershell
python --version
git --version
```

Expected: `Python 3.13.x` and a git version string. If `python` is not
recognized, reopen PowerShell (PATH changes need a fresh shell) or
reinstall Python with "Add to PATH" checked.

### 2. Clone and open the project

```powershell
git clone <your-repo-url> AI_JOB_APPLICATION_PLATFORM
cd AI_JOB_APPLICATION_PLATFORM
code .
```

`code .` opens the folder in VS Code. In VS Code, open a new terminal via
**Terminal → New Terminal** — it defaults to PowerShell on Windows.

### 3. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If you see an error like *"running scripts is disabled on this system"*,
run this once (as your normal user, not admin) and retry:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Your prompt should now show `(.venv)` at the start of the line. In VS
Code, select this interpreter: **Ctrl+Shift+P → "Python: Select
Interpreter" → `.venv\Scripts\python.exe`**.

### 4. Install dependencies

```powershell
pip install --upgrade pip
pip install -r requirements\dev.txt
python -m playwright install --with-deps chromium
```

The Playwright install step downloads a Chromium browser binary; it is
needed later for the Automation module but is safe to install now.

### 5. Create your `.env` file

```powershell
Copy-Item .env.example .env
```

Then open `.env` in VS Code and fill in the Supabase values (see next
section).

## Supabase Setup

1. Create a free project at [supabase.com](https://supabase.com).
2. In **Project Settings → API**, copy the **Project URL** and the
   **anon** and **service_role** keys into `SUPABASE_URL`,
   `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` in `.env`.
3. In **Project Settings → Database → Connection string**, copy the URI
   and adapt it into `DATABASE_URL`, using the `postgresql+psycopg://`
   scheme (SQLAlchemy needs the driver name in the scheme):
   ```
   DATABASE_URL=postgresql+psycopg://postgres:<password>@<project-ref>.supabase.co:5432/postgres
   ```
4. Open the **SQL Editor** in the Supabase dashboard, paste the contents
   of `sql/001_foundation_schema.sql`, and run it. This creates the
   foundation tables (`system_configuration`, `scheduler_runs`,
   `system_logs`, `error_logs`). Later modules ship their own numbered
   migration files (e.g. `sql/002_candidate_schema.sql`) — run them in
   order.
5. In **Storage**, create a bucket matching `SUPABASE_STORAGE_BUCKET`
   in `.env` (default `job-platform-files`). This is used starting in
   Part 3 for resume/cover-letter storage.

## Environment Variables

Every variable is declared and documented in `.env.example` and loaded
by `src/shared/config/settings.py`. Never commit `.env` — it's already
excluded in `.gitignore`. Key groups:

- **Core** — environment name, debug flag
- **API** — host/port/CORS
- **Supabase** — project URL, keys, storage bucket, database URL
- **Logging** — level, rotation, retention, Supabase forwarding toggle
- **Scheduler** — timezone, misfire grace period
- **Retry/Timeouts** — defaults used by `retry_with_backoff`
- **AI** — provider, API key, model name
- **Browser Automation** — headless mode, browser type
- **Dashboard** — port, refresh interval
- **Application thresholds** — minimum match score to auto-apply, manual-review threshold

## Running the Application

With the virtual environment activated:

```powershell
# Start the API
uvicorn src.api.main:app --reload --port 8000
```

Expected output ends with `Uvicorn running on http://0.0.0.0:8000`.
Visit `http://localhost:8000/api/v1/health` — you should see:

```json
{"success": true, "data": {"status": "healthy", "database_connected": true, ...}}
```

If `database_connected` is `false`, see [Troubleshooting](#troubleshooting).

In a **second** PowerShell terminal (activate `.venv` again first):

```powershell
streamlit run src/dashboard/app.py
```

This opens a browser tab at `http://localhost:8501` showing the
Foundation-phase Home page, which pings the API health endpoint.

## Running Tests

```powershell
pytest
pytest --cov=src --cov-report=term-missing   # with coverage
```

Tests run against an in-memory SQLite database (see `tests/conftest.py`)
so they never touch real Supabase data and require no credentials.
Expected: all tests pass, e.g. `XX passed in Y.YYs`.

## Debugging in VS Code

Create `.vscode/launch.json` (VS Code will offer to create this
automatically the first time you hit **Run and Debug**) with:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI: Uvicorn",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["src.api.main:app", "--reload", "--port", "8000"],
      "jinja": true
    },
    {
      "name": "Pytest: Current File",
      "type": "debugpy",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}"]
    }
  ]
}
```

Set breakpoints by clicking left of a line number, then press **F5**
with the "FastAPI: Uvicorn" configuration selected.

## Docker

```powershell
docker compose build
docker compose up
```

This builds and starts both the API (port 8000) and dashboard (port
8501) containers, reading configuration from `.env`. Check container
health with:

```powershell
docker ps
docker compose logs -f api
```

To stop: `docker compose down`. To rebuild after a dependency change:
`docker compose build --no-cache`.

## Git Workflow

```powershell
git add .
git commit -m "Completed Project Foundation"
git tag v0.1.0-foundation
git push origin main
```

- `git add .` stages every new/changed file.
- `git commit -m "..."` records a snapshot with a descriptive message.
- `git tag v0.1.0-foundation` marks this exact commit as the foundation
  milestone, so it can be referenced or rolled back to later.
- `git push origin main` uploads the commit (and, with `--tags`, the tag)
  to your remote.

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| `python : The term 'python' is not recognized` | Python not on PATH | Reinstall Python with "Add to PATH" checked, reopen terminal |
| `cannot be loaded because running scripts is disabled` | PowerShell execution policy | `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |
| `ConfigurationError: DATABASE_URL is not set` | `.env` missing or not filled in | `Copy-Item .env.example .env` then fill in Supabase values |
| `/api/v1/health` shows `database_connected: false` | Wrong password/host in `DATABASE_URL`, or Supabase project paused | Re-copy connection string from Supabase dashboard; free-tier projects pause after inactivity — open the Supabase dashboard to wake it |
| `ModuleNotFoundError: No module named 'src'` | Running commands from wrong directory, or `.venv` not activated | Run commands from the repo root; confirm `(.venv)` prefix is showing |
| Playwright install fails on Windows | Missing OS dependencies | Run `python -m playwright install --with-deps chromium` again as the error message directs; may need to run PowerShell as Administrator once |

## Roadmap

This repository currently implements only the **Foundation** phase.
Planned phases (each will update this README when it lands):

- **Part 3 — Resume Intelligence & AI Matching**: Resume Parser, Candidate
  Profile, Job Discovery connectors, Job Normalizer, Duplicate Detection,
  Skill Intelligence, AI Matching Engine, Decision Engine, ATS
  Optimization.
- **Part 4 — Automation Layer**: Playwright automation engine, portal
  connectors, Authentication Manager, CAPTCHA/MFA detection, Application
  Queue, Email Monitor, Notifications, full Dashboard (Applications,
  Candidate, Job Queue, Scheduler, Analytics, Logs, Settings pages).
- **Part 5 — Production Hardening**: security review, performance
  optimization, monitoring, expanded CI/CD, full documentation set
  (ARCHITECTURE.md, API.md, CHANGELOG.md).

## License

Not yet chosen — add a `LICENSE` file before treating this as
distributable.
