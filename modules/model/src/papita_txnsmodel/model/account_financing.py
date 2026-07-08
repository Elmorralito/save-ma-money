"""Asset–loan financing join table (v3)."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DECIMAL, Column, Index
from sqlmodel import Field, Relationship

from .base import SCHEMA_NAME, BaseSQLModel
from .contstants import ACCOUNT_FINANCING__TABLENAME, ACCOUNTS__TABLENAME, USERS__TABLENAME

if TYPE_CHECKING:
    from .accounts import Accounts
    from .users import Users


class AccountFinancing(BaseSQLModel, table=True):  # type: ignore
    """Links an asset account to its financing loan account."""

    __tablename__ = ACCOUNT_FINANCING__TABLENAME
    __table_args__ = (
        Index("ix_account_financing_loan_account_id", "loan_account_id"),
        {"schema": SCHEMA_NAME},
    )

    asset_account_id: uuid.UUID = Field(foreign_key=f"{ACCOUNTS__TABLENAME}.id", primary_key=True)
    loan_account_id: uuid.UUID = Field(foreign_key=f"{ACCOUNTS__TABLENAME}.id", primary_key=True)
    financing_share: float = Field(sa_column=Column(DECIMAL(4, 4), nullable=False), default=1.0, gt=0, le=1)
    owner_id: uuid.UUID = Field(foreign_key=f"{USERS__TABLENAME}.id", nullable=False, index=True)

    owner: "Users" = Relationship(back_populates="owned_account_financing")
    asset_account: "Accounts" = Relationship(
        back_populates="financing_as_asset",
        sa_relationship_kwargs={"foreign_keys": "AccountFinancing.asset_account_id"},
    )
    loan_account: "Accounts" = Relationship(
        back_populates="financing_as_loan",
        sa_relationship_kwargs={"foreign_keys": "AccountFinancing.loan_account_id"},
    )
