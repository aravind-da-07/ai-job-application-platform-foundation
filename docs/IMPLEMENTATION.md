# IMPLEMENTATION.md — Foundation Phase (v0.1.0)

This guide walks through building this repository from an empty Windows
machine to a running, tested foundation. It documents what was actually
done to produce this repository, in order, so it can be reproduced or
audited step by step.

## Prerequisites Checklist

- [ ] Python 3.13+ installed, on PATH (`python --version`)
- [ ] Git installed (`git --version`)
- [ ] VS Code installed, with extensions: Python, Black Formatter, Ruff, Docker
- [ ] A free Supabase account and project created

## Step 1 — Create the directory structure

From the repo root in PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path `
  docs, `
  src\modules, `
  src\shared\config, src\shared\core, src\shared\database, `
  src\shared\models, src\shared\repositories, src\shared\services, `
  src\shared\schemas, src\shared\middleware, src\shared\events, `
  src\shared\scheduler, src\shared\logging, src\shared\notifications, `
  src\shared\utils, src\dashboard, src\api\routers, `
  tests\unit, tests\integration, tests\fixtures, `
  scripts, docker, sql, requirements, sample_data, `
  .github\workflows
```

**Why each top-level folder exists:**

| Folder | Purpose |
|---|---|
| `docs/` | Project-wide docs (this file, RUNBOOK.md, future ARCHITECTURE.md) |
| `src/modules/` | Home for each domain feature once implemented (Part 3+) — kept separate from `shared/` so business logic never gets mistaken for infrastructure |
| `src/shared/` | Infrastructure every module depends on: config, DB, logging, events, scheduler, base repository/service classes |
| `src/api/` | FastAPI app and routers |
| `src/dashboard/` | Streamlit app |
| `tests/` | Mirrors `src/` — `unit/` for isolated logic, `integration/` for cross-component (e.g. API + DB) tests |
| `sql/` | Numbered, ordered migration files run manually against Supabase |
| `requirements/` | Split by purpose (`base`, `dev`, `prod`) so production images don't install test/lint tooling |
| `docker/` | Secondary Dockerfiles (dashboard) that don't belong at repo root |
| `.github/workflows/` | CI pipeline definitions |

## Step 2 — Initialize Git

```powershell
git init
git branch -M main
```

## Step 3 — Create the virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Expected: prompt shows `(.venv)` prefix. If activation fails with an
execution-policy error, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

## Step 4 — Add configuration files

Files created in this step: `pyproject.toml`, `requirements/base.txt`,
`requirements/dev.txt`, `requirements/prod.txt`, `.env.example`,
`.gitignore`.

`pyproject.toml` centralizes tool config (Black line length, Ruff
rules, pytest paths) so every contributor's editor and the CI pipeline
apply identical rules — no per-developer formatting drift.

Install:

```powershell
pip install -r requirements\dev.txt
```

Expected: pip resolves and installs FastAPI, SQLAlchemy, Loguru,
APScheduler, Streamlit, Playwright, pytest, Ruff, Black, and their
dependencies without version conflicts.

## Step 5 — Build the configuration layer

Files: `src/shared/config/settings.py`, `src/shared/config/constants.py`.

`settings.py` defines a single `Settings(BaseSettings)` class covering
every tunable value in the platform (API, database, logging, scheduler,
retry, AI, browser, dashboard, thresholds), loaded from environment
variables or `.env`. `get_settings()` is `@lru_cache`d so repeated calls
across the app don't re-parse the environment.

`constants.py` holds true domain constants (enums like
`ApplicationStatus`, `EventType`) — never environment-specific, so it
has no `Settings` dependency.

**Why this matters for later modules**: the Resume Parser will read
`settings.default_request_timeout_seconds`; the Automation module will
read `settings.browser_headless` and `settings.browser_navigation_timeout_ms`;
the Decision Engine will read `settings.minimum_match_score_to_apply`.
Declaring them now means those modules never hardcode a magic number.

## Step 6 — Build the exception hierarchy

File: `src/shared/core/exceptions.py`.

A single `PlatformError` base class, with subclasses per concern
(`DatabaseError`, `ResumeParsingError`, `AutomationError`,
`CaptchaDetectedError`, etc.), each carrying an HTTP status and a
machine-readable `code`. This lets `src/shared/middleware/error_handlers.py`
catch one type and still return the right status code and message for
every different failure — and lets future modules raise a specific,
already-wired-up exception instead of inventing a new one.

## Step 7 — Build the logging system

File: `src/shared/logging/logger.py`.

Uses Loguru with two sinks: colorized console (dev readability) and a
rotating, JSON-serialized file sink (durable local logs, rotated per
`settings.log_rotation`, retained per `settings.log_retention`). Every
module calls `get_logger(__name__)` rather than configuring its own
logger — this guarantees one consistent format and rotation policy
platform-wide. A Supabase-forwarding sink is intentionally deferred to
Part 4 (Automation) so this module has no database dependency yet.

## Step 8 — Build the database layer

Files: `src/shared/database/session.py`, `src/shared/database/base.py`.

`base.py` defines the SQLAlchemy `Base` plus two mixins
(`UUIDPrimaryKeyMixin`, `TimestampMixin`) that every future ORM model
will inherit — this is what guarantees every table has a UUID `id` and
`created_at`/`updated_at`, per the project's mandatory-columns
requirement, without repeating those columns in every model.

`session.py` builds a single pooled `Engine` (lazy, cached), exposes
`get_db_session()` for FastAPI's `Depends()`, `session_scope()` for
non-request contexts (scheduler jobs, scripts), and
`check_database_health()` for the `/health` endpoint. Connection pooling
uses `pool_pre_ping=True` so dead connections (e.g. after a Supabase
project cold-start) are detected and recycled automatically.

## Step 9 — Build the repository and service base classes

Files: `src/shared/repositories/base_repository.py`,
`src/shared/services/base_service.py`.

`BaseRepository[ModelType]` is a generic class implementing create,
get_by_id, list, count, update, delete against any ORM model — future
repositories (e.g. `CandidateRepository`) subclass it and add only
domain-specific queries (`get_by_email`), inheriting CRUD for free.
`BaseService` is a thin marker base that future services extend,
holding the injected `Session` and a bound logger.

**Why the split matters**: repositories touch the database and nothing
else; services hold business logic and are the only thing API routers
are allowed to call. This is the Repository Pattern requirement from
the project's coding standards, made structurally enforceable rather
than just a convention.

## Step 10 — Build the event bus

File: `src/shared/events/event_bus.py`.

A synchronous in-process pub/sub bus keyed by `EventType`. A failing
subscriber is caught and logged without breaking the publisher or other
subscribers — critical once multiple future modules (Notifications,
Dashboard, Automation) all subscribe to the same events (e.g.
`CAPTCHA_DETECTED`) and one must never be able to break another.

## Step 11 — Build the scheduler infrastructure

File: `src/shared/scheduler/scheduler_manager.py`.

Wraps `APScheduler`'s `BackgroundScheduler` with `add_interval_job` /
`add_cron_job` convenience methods and centralized job-event logging
(`EVENT_JOB_ERROR`, `EVENT_JOB_MISSED`). Contains **no business jobs** —
future modules (Job Discovery's hourly search, Analytics' daily report)
call `get_scheduler_manager().add_interval_job(...)` from their own
code; this file never needs to change when a new scheduled job is added.

## Step 12 — Build the FastAPI application

Files: `src/api/main.py`, `src/api/routers/system.py`,
`src/shared/middleware/error_handlers.py`,
`src/shared/middleware/request_logging.py`,
`src/shared/schemas/response_models.py`.

`create_app()` wires CORS, request-logging middleware, centralized
error handlers, and the `system` router (`/health`, `/version`,
`/config`) behind `settings.api_prefix`. The `lifespan` context starts
the scheduler on startup and shuts it down gracefully on exit — this is
the hook future modules use to register their scheduled jobs at
process start.

Run it:

```powershell
uvicorn src.api.main:app --reload --port 8000
```

Expected console output ends with `Application startup complete.` Visit
`http://localhost:8000/docs` for the interactive OpenAPI UI (FastAPI
generates this automatically from the routers and Pydantic models).

## Step 13 — Build shared utilities

Files: `src/shared/utils/retry.py`, `hash_helpers.py`, `date_helpers.py`,
`file_helpers.py`, `json_helpers.py`.

`retry_with_backoff` is a decorator any future HTTP/browser/AI call can
apply. `fingerprint_job()` in `hash_helpers.py` is specifically shaped
for the Part 3 Duplicate Detection requirement (hashes
company+role+location). `validate_resume_extension()` in
`file_helpers.py` enforces the supported-format list from
`constants.py` and will be the first call the Part 3 Resume Parser
makes on an uploaded file.

## Step 14 — Write the SQL schema

File: `sql/001_foundation_schema.sql`.

Creates only the tables the Foundation phase needs:
`system_configuration`, `scheduler_runs`, `system_logs`, `error_logs` —
plus a reusable `set_updated_at()` trigger function every future
table's migration will attach to. Domain tables (candidates, jobs,
applications, application audit, etc.) are deliberately **not** created
here; each owns its schema in its own numbered migration file when its
module is implemented, keeping this file reviewable and matching what
code actually exists right now.

Run it in the Supabase SQL Editor (paste and execute), or via the
Supabase CLI:

```powershell
supabase db execute --file sql/001_foundation_schema.sql
```

## Step 15 — Write tests

Files: `tests/conftest.py`, `tests/unit/test_settings.py`,
`tests/unit/test_exceptions.py`, `tests/unit/test_base_repository.py`,
`tests/unit/test_event_bus.py`, `tests/integration/test_system_endpoints.py`.

`conftest.py`'s `db_session` fixture creates an isolated in-memory
SQLite database per test using the same `Base.metadata` that targets
Supabase Postgres in production — so `BaseRepository` is tested for
real, with zero Supabase credentials required in CI. `api_client` spins
up the full FastAPI app via `TestClient` for integration tests.

Run:

```powershell
pytest -v
pytest --cov=src --cov-report=term-missing
```

Expected: all tests pass. The `test_config_endpoint_never_leaks_secrets`
test is a guardrail — it fails the build if a future change accidentally
adds a secret-sounding field to the public `/config` endpoint.

## Step 16 — Docker

Files: `Dockerfile`, `docker/Dockerfile.dashboard`, `docker-compose.yml`,
`.dockerignore`.

The API `Dockerfile` installs Playwright's Chromium binary now (Part 4
dependency) so the image doesn't need rebuilding when Automation lands.
Build:

```powershell
docker compose build
```

Expected: both `api` and `dashboard` images build without error.

## Step 17 — CI/CD

File: `.github/workflows/ci.yml`.

Three jobs, each depending on the previous: `lint` (Ruff + Black check)
→ `test` (pytest with coverage, no real Supabase needed) → `docker-build`
(confirms the image still builds). This runs on every push/PR to `main`
or `develop`.

## Step 18 — Verify and commit

```powershell
pytest
ruff check src tests
black --check src tests
docker compose build
```

Once all four succeed, proceed to the Git Workflow section of
`README.md`:

```powershell
git add .
git commit -m "Completed Project Foundation"
git tag v0.1.0-foundation
git push origin main
```

## Verification Checkpoints Summary

| Checkpoint | Command | Expected Result |
|---|---|---|
| Dependencies install | `pip install -r requirements\dev.txt` | No errors |
| Settings load | `python -c "from src.shared.config.settings import get_settings; print(get_settings().app_name)"` | Prints app name |
| API starts | `uvicorn src.api.main:app --reload` | `Application startup complete.` |
| Health check | Browser → `localhost:8000/api/v1/health` | JSON with `"success": true` |
| Tests pass | `pytest` | All green |
| Lint passes | `ruff check src tests` | No errors |
| Docker builds | `docker compose build` | Both images build |

Only once every row above passes should Part 3 (Resume Intelligence,
Job Discovery, AI Matching) begin — it will import and depend on every
file listed in this document.
