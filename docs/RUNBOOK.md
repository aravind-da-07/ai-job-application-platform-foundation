# RUNBOOK.md — Foundation Phase (v0.1.0)

Operational procedures for running, checking, and recovering this
service. Scope is limited to what exists today: the FastAPI service,
the scheduler infrastructure, and the Streamlit dashboard shell. Queue
recovery, browser session recovery, and email-monitor procedures will
be added to this file when Part 4 (Automation) lands.

## Starting the Platform

**Local (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn src.api.main:app --reload --port 8000
```

In a second terminal:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run src/dashboard/app.py
```

**Docker:**

```powershell
docker compose up -d
```

## Stopping the Platform

**Local:** `Ctrl+C` in each terminal. The API's `lifespan` shutdown
hook calls `scheduler.shutdown(wait=True)`, so in-flight scheduled jobs
are allowed to finish before the process exits — do not force-kill
(`Ctrl+C` twice) unless the process is hung, as that skips this
graceful shutdown.

**Docker:** `docker compose down`

## Restart Procedure

```powershell
docker compose restart api
```

or, for a full rebuild after a dependency/code change:

```powershell
docker compose down
docker compose build --no-cache
docker compose up -d
```

## Health Checks

| Check | Command | Healthy Result |
|---|---|---|
| API process | `curl http://localhost:8000/api/v1/health` | `"status": "healthy"` |
| Database connectivity | Same endpoint, `data.database_connected` | `true` |
| Scheduler running | `docker compose logs api \| Select-String "Scheduler started"` | Log line present |
| Dashboard reachable | Browser → `http://localhost:8501` | Home page renders, shows "API is healthy" |

If `database_connected` is `false`:

1. Check the Supabase project isn't paused (free tier pauses after 7
   days of inactivity) — open the Supabase dashboard, which wakes it.
2. Verify `DATABASE_URL` in `.env` matches the current connection
   string from **Project Settings → Database** in Supabase (the
   password is only shown once at project creation; reset it there if
   lost).
3. Confirm the `postgresql+psycopg://` scheme prefix is present —
   plain `postgresql://` will fail because SQLAlchemy needs the driver
   name.

## Supabase Connectivity Check (manual)

```powershell
python -c "from src.shared.database.session import check_database_health; print(check_database_health())"
```

Expected: `True`. On failure, this raises a `DatabaseError` with the
underlying cause in its message — read that message first before
escalating.

## Log Locations

| Log | Location |
|---|---|
| Local rotating file logs | `logs/platform_YYYY-MM-DD.log` (JSON lines) |
| Console output | stderr of the `uvicorn` / `streamlit` process, or `docker compose logs -f api` |
| Durable structured logs (future) | `system_logs` / `error_logs` tables in Supabase, once `LOG_TO_SUPABASE=true` and the Supabase sink (Part 4) is wired in |

Tail logs live:

```powershell
Get-Content -Path "logs\platform_$(Get-Date -Format 'yyyy-MM-dd').log" -Wait -Tail 50
```

## Scheduler Checks

```powershell
python -c "from src.shared.scheduler.scheduler_manager import get_scheduler_manager; m = get_scheduler_manager(); m.start(); print(m.list_jobs())"
```

The Foundation phase registers no business jobs, so an empty list `[]`
is the expected, correct result — this only confirms the scheduler
itself starts without error. Job listings will become meaningful once
Part 3/4 modules register real jobs.

## Backup Strategy

Supabase performs automatic daily backups on paid tiers; on the free
tier, export critical tables manually via **Database → Backups** or
`pg_dump` against the connection string in `.env` before any destructive
migration:

```powershell
pg_dump "$env:DATABASE_URL" -f backup_$(Get-Date -Format 'yyyyMMdd').sql
```

(Requires the PostgreSQL client tools installed locally.)

## Recovery Steps (corrupted local state)

Local state in this phase is limited to `logs/` and the `.venv`. Both
are disposable:

```powershell
Remove-Item -Recurse -Force logs
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements\dev.txt
```

No candidate, job, or application data is ever stored locally per the
project's storage policy — all persistent state lives in Supabase, so
local recovery never risks data loss.

## Maintenance Checklist (weekly)

- [ ] `pip list --outdated` — review dependency updates
- [ ] `docker compose build --no-cache` — confirm image still builds clean
- [ ] `pytest --cov=src` — confirm coverage hasn't regressed
- [ ] Check Supabase project isn't approaching free-tier storage/row limits
- [ ] Rotate `SUPABASE_SERVICE_ROLE_KEY` if it may have been exposed (Supabase dashboard → API settings)

## Incident Response (API down / 500s)

1. `docker compose logs --tail=200 api` — read the most recent error.
2. If it's a `PlatformError` subclass, the log line names the specific
   `code` (e.g. `database_error`) — cross-reference
   `src/shared/core/exceptions.py` for what raises it.
3. If it's an unhandled exception, the full traceback is in the log
   (Loguru's `logger.exception` call in `error_handlers.py`) even
   though the client only received a generic 500 — never expand traceback
   visibility to clients, even temporarily, to debug.
4. Restart per the procedure above once the root cause is identified
   and fixed; restarting without a fix will just recur.
