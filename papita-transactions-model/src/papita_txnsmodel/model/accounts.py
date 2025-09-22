import datetime
import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import ARRAY, TIMESTAMP, Column, String
from sqlmodel import Field, Relationship

from .base import BaseSQLModel

if TYPE_CHECKING:
    from .assets import AssetAccounts
    from .liabilities import LiabilityAccounts
    from .transactions import Transactions


class Accounts(BaseSQLModel, table=True):  # type: ignore

    __tablename__ = "accounts"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, index=True)
    description: str = Field(nullable=False)
    tags: List[str] = Field(sa_column=Column(ARRAY(String)), min_items=1, unique_items=True)
    start_ts: datetime.datetime = Field(
        sa_column=Column(TIMESTAMP, nullable=False, index=True), default_factory=datetime.datetime.now
    )
    end_ts: Optional[datetime.datetime] = Field(sa_column=Column(TIMESTAMP, nullable=True, index=True), default=None)

    asset_accounts: "AssetAccounts" = Relationship(
        back_populates="accounts",
        sa_relationship_kwargs={"uselist": False, "foreign_keys": "AssetAccounts.account_id"},
        cascade_delete=True,
    )

    liability_accounts: Optional["LiabilityAccounts"] = Relationship(
        back_populates="accounts",
        sa_relationship_kwargs={"uselist": False, "foreign_keys": "LiabilityAccounts.account_id"},
        cascade_delete=True,
    )

    transactions_from_accounts: List["Transactions"] = Relationship(
        back_populates="from_accounts",
        sa_relationship_kwargs={"foreign_keys": "Transactions.from_account_id"},
        cascade_delete=True,
    )

    transactions_to_accounts: List["Transactions"] = Relationship(
        back_populates="to_accounts",
        sa_relationship_kwargs={"foreign_keys": "Transactions.to_account_id"},
        cascade_delete=True,
    )
