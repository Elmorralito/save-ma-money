import inspect
import sys
from typing import Literal, Union

from pydantic import BaseModel, ConfigDict, Field

from papita_txnsmodel.access.base.dto import CoreTableDTO
from papita_txnsmodel.model.types import (
    AssetAccountTypes,
    LiabilityAccountTypes,
    TransactionCategories,
)


class TypesDTO(CoreTableDTO):
    model_config = ConfigDict(extra="allow")

    @property
    def row(self) -> dict:
        return self.model_dump(mode="python") | {"discriminator": getattr(self, "discriminator", "")}


class AssetAccountTypesDTO(TypesDTO):
    """DTO for AssetAccountTypes model."""

    __dao_type__ = AssetAccountTypes
    discriminator: Literal["asset_account_types"]


class LiabilityAccountTypesDTO(TypesDTO):
    """DTO for LiabilityAccountTypes model."""

    __dao_type__ = LiabilityAccountTypes
    discriminator: Literal["liability_account_types"]


class TransactionCategoriesDTO(TypesDTO):
    """DTO for TransactionCategories model."""

    __dao_type__ = TransactionCategories
    discriminator: Literal["transaction_categories"]


DTO_TYPES = [
    cls_
    for _, cls_ in inspect.getmembers(sys.modules[__name__], inspect.isclass)
    if issubclass(cls_, TypesDTO) and cls_ != TypesDTO
]


class DiscriminatedTypesModel(BaseModel):

    type_dto: Union[tuple(DTO_TYPES)] = Field(discriminator="discriminator")  # type: ignore
