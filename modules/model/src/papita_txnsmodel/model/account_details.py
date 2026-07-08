"""1:1 account extension tables (v3)."""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DECIMAL, Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy import SmallInteger, String
from sqlmodel import Field, Relationship

from .base import BaseSQLModel
from .contstants import (
    ACCOUNTS__TABLENAME,
    BANKING_ACCOUNT_DETAILS__TABLENAME,
    CREDIT_CARD_ACCOUNT_DETAILS__TABLENAME,
    LOAN_ACCOUNT_DETAILS__TABLENAME,
    REAL_ESTATE_ACCOUNT_DETAILS__TABLENAME,
    TRADING_ACCOUNT_DETAILS__TABLENAME,
)
from .enums import RealEstateAreaUnit, RealEstateOwnership

if TYPE_CHECKING:
    from .accounts import Accounts


class BankingAccountDetails(BaseSQLModel, table=True):  # type: ignore
    """Banking-specific account extension."""

    __tablename__ = BANKING_ACCOUNT_DETAILS__TABLENAME

    account_id: uuid.UUID = Field(foreign_key=f"{ACCOUNTS__TABLENAME}.id", primary_key=True)
    entity: str = Field(sa_type=String, nullable=False)
    account_number: str | None = Field(sa_type=String, nullable=True, default=None)

    account: "Accounts" = Relationship(back_populates="banking_details")


class RealEstateAccountDetails(BaseSQLModel, table=True):  # type: ignore
    """Real-estate-specific account extension."""

    __tablename__ = REAL_ESTATE_ACCOUNT_DETAILS__TABLENAME

    account_id: uuid.UUID = Field(foreign_key=f"{ACCOUNTS__TABLENAME}.id", primary_key=True)
    address: str = Field(sa_type=String, nullable=False)
    city: str = Field(sa_type=String, nullable=False)
    country: str = Field(sa_type=String, nullable=False)
    total_area: float = Field(sa_column=Column(DECIMAL(12, 4), nullable=False))
    built_area: float = Field(sa_column=Column(DECIMAL(12, 4), nullable=False))
    area_unit: RealEstateAreaUnit = Field(
        sa_column=Column(
            SAEnum(RealEstateAreaUnit, name="area_unit", schema="papita_transactions", create_type=False),
            nullable=False,
        )
    )
    ownership: RealEstateOwnership = Field(
        sa_column=Column(
            SAEnum(RealEstateOwnership, name="ownership", schema="papita_transactions", create_type=False),
            nullable=False,
        )
    )
    participation: float = Field(sa_column=Column(DECIMAL(4, 4), nullable=False), default=1.0)

    account: "Accounts" = Relationship(back_populates="real_estate_details")


class TradingAccountDetails(BaseSQLModel, table=True):  # type: ignore
    """Trading/investment account extension."""

    __tablename__ = TRADING_ACCOUNT_DETAILS__TABLENAME

    account_id: uuid.UUID = Field(foreign_key=f"{ACCOUNTS__TABLENAME}.id", primary_key=True)
    buy_value: float = Field(sa_column=Column(DECIMAL(22, 8), nullable=False))
    units: int = Field(sa_column=Column(SmallInteger, nullable=False), default=1)

    account: "Accounts" = Relationship(back_populates="trading_details")


class CreditCardAccountDetails(BaseSQLModel, table=True):  # type: ignore
    """Credit card account extension."""

    __tablename__ = CREDIT_CARD_ACCOUNT_DETAILS__TABLENAME

    account_id: uuid.UUID = Field(foreign_key=f"{ACCOUNTS__TABLENAME}.id", primary_key=True)
    credit_limit: float = Field(sa_column=Column(DECIMAL(22, 8), nullable=False))

    account: "Accounts" = Relationship(back_populates="credit_card_details")


class LoanAccountDetails(BaseSQLModel, table=True):  # type: ignore
    """Loan/mortgage account extension."""

    __tablename__ = LOAN_ACCOUNT_DETAILS__TABLENAME

    account_id: uuid.UUID = Field(foreign_key=f"{ACCOUNTS__TABLENAME}.id", primary_key=True)
    is_paid_off: bool = Field(nullable=False, default=False)
    insurance_payment: float = Field(sa_column=Column(DECIMAL(22, 8), nullable=False), default=0)
    extras_payment: float = Field(sa_column=Column(DECIMAL(22, 8), nullable=False), default=0)

    account: Optional["Accounts"] = Relationship(back_populates="loan_details")
