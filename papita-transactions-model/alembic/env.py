import contextlib
import logging
import os
import sys
import urllib.parse
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.append(MODEL_PATH)

from papita_txnsmodel.model import *  # pylint: disable=wildcard-import,wrong-import-position # noqa: F403,E402,F401,E501 # pyright: ignore[reportMissingImports]

# Load environment variables from .env file if they are not already set
load_dotenv(override=True)

target_metadata = SQLModel.metadata

logger = logging.getLogger("alembic.env")
# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def load_url() -> None:
    logger.info("Loading database URL.")
    with contextlib.suppress(KeyError):
        if not config.get_main_option("sqlalchemy.url"):
            raise KeyError()

        return None

    db_driver = os.environ["DB_DRIVER"]
    db_user = os.environ["DB_USER"]
    db_password = os.environ["DB_PASSWORD"]
    db_name = os.environ["DB_NAME"]
    db_host = os.environ["DB_HOST"]
    db_port = os.environ["DB_PORT"]

    try:
        if not db_password:
            raise TypeError("Database password is not set.")

        encoded_password = urllib.parse.quote_plus(db_password)
        logger.info("Constructing database URL from environment variables.")
        database_url = f"{db_driver}://{db_user}:{encoded_password}@{db_host}:{db_port}/{db_name}"
    except TypeError:
        x_args = context.get_x_argument(as_dictionary=True)
        database_url = x_args.get(
            "url",
            x_args.get("dburl", os.getenv("DB_URL", os.getenv("DATABASE_URL"))),
        )

    if not database_url:
        raise ValueError("Database URL is not set. Please set the DB_URL or DATABASE_URL environment variable.")

    config.set_main_option("sqlalchemy.url", database_url)
    return None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    load_url()
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
    """Run migrations in 'online' mode."""

    def process_revision_directives(context, revision, directives):
        if config.cmd_opts.autogenerate:
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info("No changes in schema detected.")

    load_url()
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
            include_schemas=True,
            template_args={"schema_name": target_metadata.schema},
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
