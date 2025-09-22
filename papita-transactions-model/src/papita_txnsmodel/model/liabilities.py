import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DECIMAL, Column, SmallInteger
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .accounts import Accounts
    from .assets import AssetAccounts
    from .types import Types


class LiabilityAccounts(SQLModel, table=True):  # type: ignore

    __tablename__ = "liability_accounts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(nullable=False, foreign_key="accounts.id")
    type_id: uuid.UUID = Field(foreign_key="types.id", nullable=False)
    months_per_period: int = Field(sa_column=Column(SmallInteger, nullable=True), default=1, gt=0)
    initial_value: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False), gt=0)
    present_value: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False), gt=0)
    monthly_interest_rate: float = Field(sa_column=Column(DECIMAL[10, 4], nullable=True), gt=0)
    yearly_interest_rate: float = Field(sa_column=Column(DECIMAL[10, 4], nullable=True), gt=0)
    payment: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False), gt=0)
    total_paid: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False), default=0, gt=0)
    overall_periods: int = Field(sa_column=Column(SmallInteger, nullable=False), default=1, gt=0)
    periods_paid: int = Field(sa_column=Column(SmallInteger, nullable=False), default=1, gt=0)
    closing_day: int = Field(sa_column=Column(SmallInteger, nullable=False), gt=0, le=28)

    accounts: "Accounts" = Relationship(
        back_populates="liability_accounts",
    )
    types: "Types" = Relationship(back_populates="liability_accounts")
    bank_credit_liability_accounts: Optional["BankCreditLiabilityAccounts"] = Relationship(
        back_populates="liability_accounts", sa_relationship_kwargs={"uselist": False}, cascade_delete=True
    )
    credit_card_liability_accounts: Optional["CreditCardLiabilityAccounts"] = Relationship(
        back_populates="liability_accounts", sa_relationship_kwargs={"uselist": False}, cascade_delete=True
    )


class BankCreditLiabilityAccounts(SQLModel, table=True):  # type: ignore

    __tablename__ = "bank_credit_liability_accounts"

    liability_account_id: uuid.UUID = Field(
        foreign_key=f"{LiabilityAccounts.__tablename__}.id", primary_key=True, nullable=False
    )
    insurance_payment: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False))
    extras_payment: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False))

    liability_accounts: LiabilityAccounts = Relationship(back_populates="bank_credit_liability_accounts")

    asset_accounts: Optional["AssetAccounts"] = Relationship(back_populates="bank_credit_liability_accounts")


class CreditCardLiabilityAccounts(SQLModel, table=True):  # type: ignore

    __tablename__ = "credit_card_liability_accounts"

    liability_account_id: uuid.UUID = Field(
        foreign_key=f"{LiabilityAccounts.__tablename__}.id", primary_key=True, nullable=False
    )
    credit_limit: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False))

    liability_accounts: LiabilityAccounts = Relationship(back_populates="credit_card_liability_accounts")
