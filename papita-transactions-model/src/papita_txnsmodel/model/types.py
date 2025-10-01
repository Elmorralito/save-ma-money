"""Types module for defining classification types in the Papita Transactions system.

This module defines the Types model which represents classification categories
for assets, liabilities, and transactions in the system. It provides a way to
categorize and organize different financial entities.

Classes:
    Types: Represents a classification type in the system.
"""

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
    """Classification type model for categorizing financial entities in the system.

    This class defines the structure for classification types that can be applied to
    assets, liabilities, and transactions. Types provide a way to categorize and
    organize different financial entities within the system.

    Attributes:
        id (uuid.UUID): Unique identifier for the type. Auto-generated UUID.
        name (str): Name of the type. Must be unique and is indexed for faster lookups.
        tags (List[str]): List of tags associated with the type. Must contain at least
            one tag and all tags must be unique.
        description (str): Detailed description of the type.
        discriminator (str): Identifier used to distinguish between different kinds
            of types in the system.
        asset_accounts (List[AssetAccounts]): List of asset accounts associated with
            this type. One-to-many relationship with cascade delete.
        liability_accounts (List[LiabilityAccounts]): List of liability accounts
            associated with this type. One-to-many relationship with cascade delete.
        identified_transactions (List[IdentifiedTransactions]): List of identified
            transactions associated with this type. One-to-many relationship with
            cascade delete.
    """

    __tablename__ = "types"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(nullable=False, index=True, unique=True)
    tags: List[str] = Field(sa_column=Column(ARRAY(String), nullable=False), min_items=1, unique_items=True)
    description: str = Field(nullable=False)
    discriminator: str = Field(nullable=False)

    asset_accounts: List["AssetAccounts"] = Relationship(back_populates="types", cascade_delete=True)
    liability_accounts: List["LiabilityAccounts"] = Relationship(back_populates="types", cascade_delete=True)
    identified_transactions: List["IdentifiedTransactions"] = Relationship(back_populates="types", cascade_delete=True)
