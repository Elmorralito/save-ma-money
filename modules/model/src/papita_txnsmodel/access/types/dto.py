"""Types DTO module for the Papita Transactions system.

This module defines Data Transfer Objects (DTOs) for type entities in the system.
It provides flexible structures for representing different types of financial entities
such as assets, liabilities, and transactions, as well as their classifications.
Classes:
    TypesClassificationsDTO: DTO for type classification entities.
    TypesDTO: DTO for type entities with reference to their classification.
"""

import hashlib
import uuid
from typing import Self

from pydantic import ConfigDict, model_validator

from papita_txnsmodel.access.base.dto import CoreTableDTO
from papita_txnsmodel.model.enums import TypesClassifications
from papita_txnsmodel.model.types import Types
from papita_txnsmodel.utils.configutils import DEFAULT_ENCODING


class TypesDTO(CoreTableDTO):
    """DTO for type entities in the Papita Transactions system.

    This class represents type entities that categorize different financial objects
    in the system. It extends CoreTableDTO to inherit common fields like name,
    description, and tags, while adding a classification field to associate the
    type with a specific classification category.

    The class allows for extra fields beyond those explicitly defined, which enables
    flexibility in representing different type categories with varying attributes.

    Attributes:
        model_config (ConfigDict): Configuration allowing extra fields beyond those defined.
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        classification (uuid.UUID | TypesClassificationsDTO): The classification of this type,
            can be either a UUID reference or a TypesClassificationsDTO object.
    """

    model_config = ConfigDict(extra="allow")
    __dao_type__ = Types

    classification: TypesClassifications
    owner_id: uuid.UUID | None = None

    @model_validator(mode="after")
    def _normalize_model(self) -> Self:
        """Normalize the model after initialization.

        This method normalizes the model by setting the classification field to the correct value.

        Returns:
            Self: The normalized model.
        """
        super()._normalize_model()
        self.id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            hashlib.sha256(f"{self.name}_{self.classification.value}".encode(DEFAULT_ENCODING)).hexdigest(),
        )
        return self
