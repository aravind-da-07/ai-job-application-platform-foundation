from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from src.shared.config.settings import get_settings
from src.shared.database.base import Base

# ---------------------------------------------------------------------------
# Import ORM models so SQLAlchemy registers them with Base.metadata.
# ---------------------------------------------------------------------------

from src.modules.users.infrastructure.models.user_model import UserModel  # noqa: F401
from src.modules.resumes.infrastructure.models.resume_model import (  # noqa: F401
    ResumeModel,
    ResumeVersionModel,
)
from src.modules.automation.infrastructure.models.automation_model import (  # noqa: F401
    AutomationRunModel,
    AutomationLogModel,
)


# ---------------------------------------------------------------------------
# Alembic configuration object.
# ---------------------------------------------------------------------------

config = context.config


# ---------------------------------------------------------------------------
# Configure Python logging using alembic.ini.
# ---------------------------------------------------------------------------

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# ---------------------------------------------------------------------------
# Load application settings from .env.
# ---------------------------------------------------------------------------

settings = get_settings()

if not settings.database_url:
    raise RuntimeError(
        "DATABASE_URL is not configured. "
        "Set DATABASE_URL in the project .env file."
    )


# ---------------------------------------------------------------------------
# Make Alembic use the same database URL as the application.
# ---------------------------------------------------------------------------

config.set_main_option(
    "sqlalchemy.url",
    settings.database_url.replace("%", "%%"),
)


# ---------------------------------------------------------------------------
# SQLAlchemy metadata used by Alembic autogenerate.
# ---------------------------------------------------------------------------

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in offline mode.

    Alembic generates SQL without opening a database connection.
    """

    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in online mode.

    Alembic connects to PostgreSQL and executes migrations.
    """

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()