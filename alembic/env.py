from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from src.shared.config.settings import get_settings
from src.shared.database.base import Base


# ============================================================================
# IMPORT ALL ORM MODELS
# ============================================================================
#
# Every SQLAlchemy ORM model must be imported here so that its table is
# registered in Base.metadata before Alembic performs autogeneration.
#

from src.modules.users.infrastructure.models.user_model import (  # noqa: F401
    UserModel,
)

from src.modules.resumes.infrastructure.models.resume_model import (  # noqa: F401
    ResumeModel,
    ResumeVersionModel,
)

from src.modules.automation.infrastructure.models.automation_model import (  # noqa: F401
    AutomationRunModel,
    AutomationLogModel,
)

from src.modules.job_discovery.infrastructure.models.job_model import (  # noqa: F401
    JobModel,
    JobMatchModel,
)


# ============================================================================
# ALEMBIC CONFIGURATION
# ============================================================================

config = context.config


# ============================================================================
# LOGGING
# ============================================================================

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ============================================================================
# APPLICATION SETTINGS
# ============================================================================

settings = get_settings()

if not settings.database_url:
    raise RuntimeError(
        "DATABASE_URL is not configured. "
        "Set DATABASE_URL in the project .env file."
    )


# ============================================================================
# DATABASE URL
# ============================================================================
#
# Use the exact same DATABASE_URL used by the application.
#

config.set_main_option(
    "sqlalchemy.url",
    settings.database_url.replace("%", "%%"),
)


# ============================================================================
# SQLALCHEMY METADATA
# ============================================================================

target_metadata = Base.metadata


# ============================================================================
# OFFLINE MIGRATIONS
# ============================================================================

def run_migrations_offline() -> None:
    """
    Run Alembic migrations in offline mode.

    This generates migration SQL without opening a database connection.
    """

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ============================================================================
# ONLINE MIGRATIONS
# ============================================================================

def run_migrations_online() -> None:
    """
    Run Alembic migrations in online mode.

    Alembic connects to the configured PostgreSQL database and compares
    the database schema against SQLAlchemy metadata.

    IMPORTANT:
    We intentionally DO NOT enable compare_server_default.

    PostgreSQL JSON defaults such as '{}'::json can cause Alembic's
    PostgreSQL implementation to execute a comparison equivalent to:

        SELECT '{}'::json = '{}'

    PostgreSQL does not provide the required equality operator for
    the JSON type, which causes:

        psycopg.errors.UndefinedFunction:
        operator does not exist: json = unknown

    Server defaults remain defined in the ORM models and migrations.
    We simply prevent Alembic autogenerate from attempting to compare
    those defaults automatically.
    """

    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section,
            {},
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ============================================================================
# MIGRATION ENTRY POINT
# ============================================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()