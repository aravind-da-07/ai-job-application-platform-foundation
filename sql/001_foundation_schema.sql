-- =============================================================================
-- AI Job Application Platform — Foundation Schema
-- =============================================================================
-- This migration creates the tables needed by the FOUNDATION phase only:
-- system configuration, activity/system logging, and scheduler run history.
-- Domain tables (candidates, jobs, applications, audit, etc.) are created by
-- their owning module's migration in later phases, so each module ships with
-- exactly the schema it needs and this file stays reviewable.
--
-- Run against your Supabase project's SQL editor, or via the Supabase CLI:
--   supabase db execute --file sql/001_foundation_schema.sql
-- =============================================================================

create extension if not exists "uuid-ossp";

-- -----------------------------------------------------------------------------
-- system_configuration
-- Key/value store for runtime-tunable settings that should be editable
-- without a redeploy (distinct from .env, which is deploy-time config).
-- -----------------------------------------------------------------------------
create table if not exists system_configuration (
    id uuid primary key default uuid_generate_v4(),
    config_key text not null unique,
    config_value jsonb not null,
    description text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

comment on table system_configuration is 'Runtime-editable key/value configuration, separate from deploy-time .env settings.';

-- -----------------------------------------------------------------------------
-- scheduler_runs
-- One row per execution of a scheduled job. scheduler_history is the same
-- table queried over time; a distinct history table is not needed while
-- runs are append-only.
-- -----------------------------------------------------------------------------
create table if not exists scheduler_runs (
    id uuid primary key default uuid_generate_v4(),
    job_id text not null,
    status text not null check (status in ('started', 'succeeded', 'failed', 'missed')),
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    duration_ms integer,
    error_message text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_scheduler_runs_job_id on scheduler_runs (job_id);
create index if not exists idx_scheduler_runs_started_at on scheduler_runs (started_at desc);

comment on table scheduler_runs is 'Execution history for every APScheduler job run, for observability and the dashboard Scheduler page.';

-- -----------------------------------------------------------------------------
-- system_logs
-- Durable copy of important structured log events (mirrors a subset of the
-- local Loguru file sink) so the dashboard Logs page can query history
-- without shelling into the server.
-- -----------------------------------------------------------------------------
create table if not exists system_logs (
    id uuid primary key default uuid_generate_v4(),
    level text not null check (level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')),
    module text not null,
    message text not null,
    context jsonb not null default '{}'::jsonb,
    occurred_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create index if not exists idx_system_logs_occurred_at on system_logs (occurred_at desc);
create index if not exists idx_system_logs_level on system_logs (level);

comment on table system_logs is 'Durable log events forwarded from the application logger, queried by the dashboard Logs page.';

-- -----------------------------------------------------------------------------
-- error_logs
-- Dedicated table for exceptions, kept separate from system_logs so error
-- rate / recent-errors dashboard widgets can query a narrow table.
-- -----------------------------------------------------------------------------
create table if not exists error_logs (
    id uuid primary key default uuid_generate_v4(),
    error_code text not null,
    message text not null,
    module text,
    request_path text,
    details jsonb not null default '{}'::jsonb,
    occurred_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create index if not exists idx_error_logs_occurred_at on error_logs (occurred_at desc);

comment on table error_logs is 'Captured exceptions across the platform, surfaced on the dashboard Home/Logs pages.';

-- -----------------------------------------------------------------------------
-- updated_at auto-touch trigger, reused by every future table in the project
-- -----------------------------------------------------------------------------
create or replace function set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_system_configuration_updated_at on system_configuration;
create trigger trg_system_configuration_updated_at
    before update on system_configuration
    for each row execute function set_updated_at();

drop trigger if exists trg_scheduler_runs_updated_at on scheduler_runs;
create trigger trg_scheduler_runs_updated_at
    before update on scheduler_runs
    for each row execute function set_updated_at();
