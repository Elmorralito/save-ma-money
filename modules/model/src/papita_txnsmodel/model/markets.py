import hashlib
import re
import uuid
from typing import TYPE_CHECKING, List, Self

from pydantic import field_validator, model_validator
from sqlalchemy import Text
from sqlmodel import Column, Field, Relationship

from papita_txnsmodel.utils.configutils import DEFAULT_ENCODING
from papita_txnsmodel.utils.modelutils import URLStr

from .base import CoreTableSQLModel
from .constants import MARKET_ASSET_GROUPS__TABLENAME, MARKET_ASSETS__TABLENAME, fk_id

if TYPE_CHECKING:
    from .assets import TradingAssetAccounts


class MarketAssetGroups(CoreTableSQLModel, table=True):  # type: ignore
    """Model for market groups.

    This model represents the groups of markets that are supported by the system.

    Attributes:
        id (uuid.UUID): Unique identifier for the market group. Auto-generated UUID.
        name (str): Name of the market group. Indexed for faster lookups.
        description (str): Detailed description of the market group.
        tags (List[str]): List of tags associated with the market group. Must contain at least
            one tag and all tags must be unique.
    """

    __tablename__ = MARKET_ASSET_GROUPS__TABLENAME

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    markets: List["MarketAssets"] = Relationship(back_populates="market_group", cascade_delete=True)

    @model_validator(mode="after")
    def _normalize_model(self) -> Self:
        """Normalize the model after initialization."""
        super()._normalize_model()
        code = re.sub(r"[^a-zA-Z0-9-_.]", "", self.name.lower())
        self.id = uuid.uuid5(uuid.NAMESPACE_URL, hashlib.sha256(code.encode(DEFAULT_ENCODING)).hexdigest())
        return self


class MarketAssets(CoreTableSQLModel, table=True):  # type: ignore
    """Model for markets.

    This model represents the markets that are supported by the system.

    Attributes:
        id (uuid.UUID): Unique identifier for the market. Auto-generated UUID.
        name (str): Name of the market. Indexed for faster lookups.
        description (str): Detailed description of the market.
        tags (List[str]): List of tags associated with the market. Must contain at least
            one tag and all tags must be unique.
    """

    __tablename__ = MARKET_ASSETS__TABLENAME

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    market_group_id: uuid.UUID = Field(foreign_key=fk_id(MARKET_ASSET_GROUPS__TABLENAME), nullable=False)

    symbol: str = Field(nullable=False, index=True, unique=True)
    code: str = Field(nullable=False, index=True, unique=True, min_length=1, max_length=10)
    precision: int = Field(nullable=False, index=True, unique=True, ge=0, le=18)
    icon: URLStr | None = Field(sa_column=Column(Text, nullable=True, index=False, unique=False), default=None)
    source: URLStr | None = Field(sa_column=Column(Text, nullable=True, index=False, unique=False), default=None)

    market_group: "MarketAssetGroups" = Relationship(back_populates="markets")

    trading_asset_accounts: List["TradingAssetAccounts"] = Relationship(
        back_populates="market_asset",
        cascade_delete=True,
        sa_relationship_kwargs={"foreign_keys": "TradingAssetAccounts.market_asset_id"},
    )

    @field_validator("code")
    @classmethod
    def _validate_code(cls, code: str) -> str:
        """Validate the internal code."""
        if not re.match(r"^[A-Za-z0-9-_]+$", code):
            raise ValueError("The code must contain only letters, numbers, dashes, and underscores")

        if len(code) > 10:
            raise ValueError("The code must be less than 10 characters")

        return code.upper()

    @model_validator(mode="after")
    def _normalize_model(self) -> Self:
        """Normalize the model after initialization."""
        super()._normalize_model()
        self.id = uuid.uuid5(uuid.NAMESPACE_URL, hashlib.sha256(self.code.encode(DEFAULT_ENCODING)).hexdigest())
        return self
