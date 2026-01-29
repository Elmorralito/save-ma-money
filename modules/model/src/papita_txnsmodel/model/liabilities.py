"""Liabilities module for managing liability accounts in the Papita Transactions system.

This module defines various liability account models including general liability accounts,
bank credit liabilities, and credit card liabilities. It provides the structure for
storing different types of liabilities with their specific attributes and relationships.

Classes:
    LiabilityAccounts: Base model for all liability accounts in the system.
    BankCreditLiabilityAccounts: Model for bank credit-related liability accounts.
    CreditCardLiabilityAccounts: Model for credit card liability accounts.
"""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DECIMAL, Column, SmallInteger
from sqlmodel import Field, Relationship

from .base import BaseSQLModel
from .contstants import (
    BANK_CREDIT_LIABILITY_ACCOUNTS__TABLENAME,
    CREDIT_CARD_LIABILITY_ACCOUNTS__TABLENAME,
    LIABILITY_ACCOUNTS__TABLENAME,
    USERS__TABLENAME,
)

if TYPE_CHECKING:
    from .assets import FinancedAssetAccounts
    from .indexers import AccountsIndexer
    from .users import Users


class LiabilityAccounts(BaseSQLModel, table=True):  # type: ignore
    """Liability accounts model representing financial liabilities in the system.

    This class defines the structure for liability accounts, which can be linked to
    regular accounts and types. It serves as the base model for more specific liability
    types like bank credits and credit cards.

    Attributes:
        id (uuid.UUID): Unique identifier for the liability account. Auto-generated UUID.
        account_id (uuid.UUID): Foreign key to the associated account.
        type_id (uuid.UUID): Foreign key to the liability type.
        months_per_period (int): Number of months per payment period. Must be positive.
        initial_value (float): Initial monetary value of the liability. Must be positive.
        present_value (float): Current monetary value of the liability. Must be positive.
        monthly_interest_rate (float): Monthly interest rate as a decimal. Must be positive.
        yearly_interest_rate (float): Yearly interest rate as a decimal. Must be positive.
        payment (float): Regular payment amount. Must be positive.
        total_paid (float): Total amount paid so far. Must be positive, defaults to 0.
        overall_periods (int): Total number of payment periods. Must be positive.
        periods_paid (int): Number of periods already paid. Must be positive.
        closing_day (int): Day of the month when payment is due. Must be between 1 and 28.
        accounts (Accounts): Related account information.
        types (Types): Related type information.
        bank_credit_liability_accounts (Optional[BankCreditLiabilityAccounts]): Optional related
            bank credit liability details with one-to-one relationship.
        credit_card_liability_accounts (Optional[CreditCardLiabilityAccounts]): Optional related
            credit card liability details with one-to-one relationship.
    """

    __tablename__ = LIABILITY_ACCOUNTS__TABLENAME

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
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
    owner_id: uuid.UUID = Field(foreign_key=f"{USERS__TABLENAME}.uid", nullable=False, index=True)

    owner: "Users" = Relationship(back_populates="owned_liabilities")

    accounts_indexer: "AccountsIndexer" = Relationship(
        back_populates=LIABILITY_ACCOUNTS__TABLENAME, sa_relationship_kwargs={"uselist": False}, cascade_delete=True
    )
    bank_credit_liability_accounts: Optional["BankCreditLiabilityAccounts"] = Relationship(
        back_populates=LIABILITY_ACCOUNTS__TABLENAME, sa_relationship_kwargs={"uselist": False}, cascade_delete=True
    )
    credit_card_liability_accounts: Optional["CreditCardLiabilityAccounts"] = Relationship(
        back_populates=LIABILITY_ACCOUNTS__TABLENAME, sa_relationship_kwargs={"uselist": False}, cascade_delete=True
    )


class ExtendedLiabilityAccounts(BaseSQLModel):
    """Base model for extended liability account information.

    This class serves as a base for specific liability types, providing a common
    primary key structure. It is inherited by models that add specialized fields
    for different kinds of liabilities.

    Attributes:
        id (uuid.UUID): Unique identifier for the extended liability record.
            Auto-generated UUID.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)


class BankCreditLiabilityAccounts(ExtendedLiabilityAccounts, table=True):  # type: ignore
    """Bank credit liability accounts model for loan-specific liability information.

    This class defines the structure for bank credit liability accounts, such as
    mortgages, personal loans, and other bank-issued credit products. It extends
    the base liability account with bank credit-specific attributes.

    Attributes:
        liability_account_id (uuid.UUID): Foreign key to the associated liability account.
            Serves as the primary key.
        insurance_payment (float): Amount paid for insurance related to this credit.
        extras_payment (float): Additional payments related to this credit.
        liability_accounts (LiabilityAccounts): Related liability account information.
        asset_accounts (Optional[AssetAccounts]): Optional related asset account,
            typically used for credits that finance specific assets.
    """

    __tablename__ = BANK_CREDIT_LIABILITY_ACCOUNTS__TABLENAME

    paid: bool = False
    insurance_payment: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False))
    extras_payment: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False))
    owner_id: uuid.UUID = Field(foreign_key=f"{USERS__TABLENAME}.uid", nullable=False)

    owner: "Users" = Relationship(back_populates="owned_bank_credit_liability_accounts")

    accounts_indexer: "AccountsIndexer" = Relationship(
        back_populates=BANK_CREDIT_LIABILITY_ACCOUNTS__TABLENAME,
        sa_relationship_kwargs={"uselist": False},
        cascade_delete=False,
    )

    financed_asset_accounts: Optional["FinancedAssetAccounts"] = Relationship(
        back_populates=BANK_CREDIT_LIABILITY_ACCOUNTS__TABLENAME,
        sa_relationship_kwargs={"uselist": False},
        cascade_delete=True,
    )


class CreditCardLiabilityAccounts(ExtendedLiabilityAccounts, table=True):  # type: ignore
    """Credit card liability accounts model for credit card-specific liability information.

    This class defines the structure for credit card liability accounts. It extends
    the base liability account with credit card-specific attributes.

    Attributes:
        liability_account_id (uuid.UUID): Foreign key to the associated liability account.
            Serves as the primary key.
        credit_limit (float): Maximum credit limit available on the card.
        liability_accounts (LiabilityAccounts): Related liability account information.
    """

    __tablename__ = CREDIT_CARD_LIABILITY_ACCOUNTS__TABLENAME

    credit_limit: float = Field(sa_column=Column(DECIMAL[22, 8], nullable=False))
    owner_id: uuid.UUID = Field(foreign_key=f"{USERS__TABLENAME}.uid", nullable=False)

    owner: "Users" = Relationship(back_populates="owned_credit_card_liability_accounts")

    accounts_indexer: "AccountsIndexer" = Relationship(
        back_populates=CREDIT_CARD_LIABILITY_ACCOUNTS__TABLENAME,
        sa_relationship_kwargs={"uselist": False},
        cascade_delete=False,
    )
