import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import ARRAY, Column, String
from sqlmodel import Field, Relationship

from .base import BaseSQLModel

if TYPE_CHECKING:
    from .assets import AssetAccounts
    from .liabilities import LiabilityAccounts
    from .transactions import IdentifiedTransactions


class Types(BaseSQLModel, table=True):  # type: ignore

    __tablename__ = "types"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, index=True, unique=True)
    tags: List[str] = Field(sa_column=Column(ARRAY(String), nullable=False), min_items=1, unique_items=True)
    description: str = Field(nullable=False)
    discriminator: str = Field(nullable=False)

    asset_accounts: List["AssetAccounts"] = Relationship(back_populates="types", cascade_delete=True)
    liability_accounts: List["LiabilityAccounts"] = Relationship(back_populates="types", cascade_delete=True)
    identified_transactions: List["IdentifiedTransactions"] = Relationship(back_populates="types", cascade_delete=True)
