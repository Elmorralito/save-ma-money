from datetime import datetime as base_datetime

from pydantic import Field
from sqlalchemy import TIMESTAMP, Column
from sqlmodel import SQLModel

SCHEMA_NAME = "papita_transactions"
SQLModel.metadata.schema = SCHEMA_NAME


class BaseSQLModel(SQLModel, table=False):  # type: ignore

    __table_args__ = {"schema": SCHEMA_NAME}

    active: bool = Field(nullable=False, default=True)
    deleted_at: base_datetime | None = Field(sa_column=Column(TIMESTAMP, nullable=False), default=None)
