
import uuid
from typing import TYPE_CHECKING, Optional
from sqlmodel import Field, Relationship, SQLModel

from .contstants import ACCOUNTS__TABLENAME, ACCOUNTS_INDEXER__TABLENAME, ASSET_ACCOUNTS__TABLENAME, CREDIT_CARD_LIABILITY_ACCOUNTS__TABLENAME, LIABILITY_ACCOUNTS__TABLENAME, ACCOUNTS_INDEXER__TABLENAME, ASSET_ACCOUNTS__TABLENAME, BANK_CREDIT_LIABILITY_ACCOUNTS__TABLENAME, BANKING_ASSET_ACCOUNTS__TABLENAME, TRADING_ASSET_ACCOUNTS__TABLENAME, REAL_ESTATE_ASSET_ACCOUNTS__TABLENAME, TYPES__TABLENAME

if TYPE_CHECKING:
    from .accounts import Accounts
    from .assets import AssetAccounts, BankingAssetAccounts, RealEstateAssetAccounts, TradingAssetAccounts
    from .liabilities import LiabilityAccounts, BankCreditLiabilityAccounts, CreditCardLiabilityAccounts
    from .types import Types


class AccountsIndexer(SQLModel, table=True):  # type: ignore

    __tablename__ = ACCOUNTS_INDEXER__TABLENAME

    account_id: uuid.UUID = Field(
        foreign_key=f"{ACCOUNTS__TABLENAME}.id", primary_key=True, nullable=False
    )

    type_id: uuid.UUID = Field(foreign_key=f"{TYPES__TABLENAME}.id", nullable=False)

    asset_account_id: Optional[uuid.UUID] = Field(
        foreign_key=f"{ASSET_ACCOUNTS__TABLENAME}.id", default=None, nullable=True
    )

    liability_account_id: Optional[uuid.UUID] = Field(
        foreign_key=f"{LIABILITY_ACCOUNTS__TABLENAME}.id", default=None, nullable=True
    )

    banking_asset_account_id: uuid.UUID | None = Field(
        foreign_key=f"{BANKING_ASSET_ACCOUNTS__TABLENAME}.id", default=None, nullable=True
    )

    real_estate_asset_account_id: uuid.UUID | None = Field(
        foreign_key=f"{REAL_ESTATE_ASSET_ACCOUNTS__TABLENAME}.id", default=None, nullable=True
    )

    trading_asset_account_id: uuid.UUID | None =  Field(
        foreign_key=f"{TRADING_ASSET_ACCOUNTS__TABLENAME}.id", default=None, nullable=True
    )

    bank_credit_liability_account_id: uuid.UUID | None = Field(
        foreign_key=f"{BANK_CREDIT_LIABILITY_ACCOUNTS__TABLENAME}.id", default=None, nullable=True
    )

    credit_card_liability_account_id: uuid.UUID | None = Field(
        foreign_key=f"{CREDIT_CARD_LIABILITY_ACCOUNTS__TABLENAME}.id", default=None, nullable=True
    )

    accounts: "Accounts" = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME,
        sa_relationship_kwargs={"uselist": False}
    )

    types: "Types" = Relationship(
        back_populates=TYPES__TABLENAME
    )

    asset_accounts: Optional["AssetAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME,
        sa_relationship_kwargs={"uselist": False},
    )

    liability_accounts: Optional["LiabilityAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME,
        sa_relationship_kwargs={"uselist": False}
    )

    banking_asset_accounts: Optional["BankingAssetAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME, sa_relationship_kwargs={"uselist": False}
    )

    trading_asset_accounts: Optional["TradingAssetAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME, sa_relationship_kwargs={"uselist": False}
    )

    real_estate_asset_accounts: Optional["RealEstateAssetAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME, sa_relationship_kwargs={"uselist": False}
    )

    bank_credit_liability_accounts: Optional["BankCreditLiabilityAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME, sa_relationship_kwargs={"uselist": False}
    )

    credit_card_liability_accounts: Optional["CreditCardLiabilityAccounts"] = Relationship(
        back_populates=ACCOUNTS_INDEXER__TABLENAME, sa_relationship_kwargs={"uselist": False}
    )
