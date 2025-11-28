import contextlib
import logging
import os
import re
import sys
import urllib.parse
from logging.config import fileConfig

import sqlalchemy as sa
from alembic import context
from alembic.ddl.impl import DefaultImpl
from dotenv import load_dotenv
from sqlmodel import SQLModel


class AlembicDuckDBImpl(DefaultImpl):
    """Alembic implementation for DuckDB."""

    __dialect__ = "duckdb"


DB_URL_PATTERN = re.compile(
    r"^(?P<scheme>\w+)(?P<driver>\+\w+)://"
    r"(?:(?P<user>[^:]+)(?::(?P<password>[^@]*))?@)?"
    r"(?P<host>[^:/]+)"
    r"(?::(?P<port>\d+))?"
    r"(?:/(?P<database>[^?#]*))?"
    r"(?:\?(?P<query>.*))?"
    r"(?:#(?P<fragment>.*))?$"
)

MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))

DEFAULT_ENV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "docker", "alembic", "default.env"
)

sys.path.append(MODEL_PATH)

from papita_txnsmodel.model import *  # pylint: disable=wildcard-import,wrong-import-position # noqa: F403,E402,F401,E501 # pyright: ignore[reportMissingImports]

target_metadata = SQLModel.metadata

logger = logging.getLogger("alembic.env")

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def load_url() -> None:
    logger.info("Loading database URL.")
    x_args = context.get_x_argument(as_dictionary=True)
    if x_args.get("duckdbPath"):
        db_path = x_args.get("duckdbPath")
        logger.info("Using DuckDB database path from arguments.")
        config.set_main_option("sqlalchemy.url", db_path)
        return None

    load_dotenv(dotenv_path=x_args.get("envPath", x_args.get("env_path", DEFAULT_ENV_PATH)), override=True)
    with contextlib.suppress(KeyError):
        if not config.get_main_option("sqlalchemy.url"):
            raise KeyError()

        return None

    db_url = os.getenv("DB_URL", os.getenv("DATABASE_URL"))
    if DB_URL_PATTERN.match(db_url or ""):
        database_url = db_url
    else:
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
            database_url = x_args.get("dbUrl", x_args.get("db_url"))

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
    connectable = sa.engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=sa.pool.NullPool,
    )
    with connectable.connect() as connection:
        if not context.get_x_argument(as_dictionary=True).get("upgrading"):
            instpector = sa.inspect(connection)
            template_args = (
                None
                if instpector.has_schema(target_metadata.schema)
                else {
                    "schema_setup": (
                        f'op.execute(sa.schema.CreateSchema("{target_metadata.schema}", if_not_exists=True))'
                    ),
                    "schema_destroy": (
                        f'op.execute(sa.schema.DropSchema("{target_metadata.schema}", cascade=False, if_exists=True))'
                    ),
                }
            )
        else:
            template_args = None

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
            include_schemas=True,
            template_args=template_args,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
