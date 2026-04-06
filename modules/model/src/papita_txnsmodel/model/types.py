"""Types module for defining classification types in the Papita Transactions system.

This module defines the Types model which represents classification categories
for assets, liabilities, and transactions in the system. It provides a way to
categorize and organize different financial entities.

Classes:
    Types: Represents a classification type in the system.
"""

import uuid
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Column, Text
from sqlmodel import Field, Relationship

from papita_txnsmodel.utils.modelutils import URLStr

from .base import CoreTableSQLModel
from .constants import TYPES__TABLENAME, USERS__TABLENAME, fk_id
from .enums import TypesClassifications

if TYPE_CHECKING:
    from .indexers import AccountsIndexer
    from .transactions import IdentifiedTransactions
    from .users import Users


class Types(CoreTableSQLModel, table=True):  # type: ignore
    """Classification type model for categorizing financial entities in the system.

    This class defines the structure for classification types that can be applied to
    assets, liabilities, and transactions. Types provide a way to categorize and
    organize different financial entities within the system.

    Attributes:
        id (uuid.UUID): Unique identifier for the type. Auto-generated UUID.
        classification (TypesClassifications): Classification of the type.
        icon (URLStr | None): Icon of the type.
        owner_id (uuid.UUID | None): ID of the owner of the type.
        owner (Users | None): Owner of the type.
        description (str): Detailed description of the type.
        transactions (List[Transactions]): List of transactions associated with the type.
        accounts_indexer (List[AccountsIndexer]): List of accounts indexer associated with the type.
        identified_transactions (List[IdentifiedTransactions]): List of identified transactions associated
            with the type. One-to-many relationship with cascade delete.
    """

    __tablename__ = TYPES__TABLENAME

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    classification: TypesClassifications = Field(nullable=False, index=True)
    icon: URLStr | None = Field(sa_column=Column(Text, nullable=True, index=False, unique=False), default=None)
    owner_id: uuid.UUID | None = Field(foreign_key=fk_id(USERS__TABLENAME), nullable=True, index=True)

    owner: Optional["Users"] = Relationship(back_populates="owned_types")

    accounts_indexer: List["AccountsIndexer"] = Relationship(back_populates=TYPES__TABLENAME, cascade_delete=True)
    identified_transactions: List["IdentifiedTransactions"] = Relationship(
        back_populates=TYPES__TABLENAME, cascade_delete=True
    )
