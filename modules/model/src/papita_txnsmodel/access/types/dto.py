"""Types DTO module for the Papita Transactions system.

This module defines Data Transfer Objects (DTOs) for type entities in the system.
It provides flexible structures for representing different types of financial entities
such as assets, liabilities, and transactions, as well as their classifications.
Classes:
    TypesClassificationsDTO: DTO for type classification entities.
    TypesDTO: DTO for type entities with reference to their classification.
"""

# import uuid

from pydantic import ConfigDict

from papita_txnsmodel.access.base.dto import CoreTableDTO
from papita_txnsmodel.model.enums import TypesClassifications
from papita_txnsmodel.model.types import Types


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

    @property
    def row(self) -> dict:
        """Get a dictionary representation of this DTO.

        This property provides a convenient way to convert the DTO to a dictionary
        format suitable for data manipulation or serialization.

        Returns:
            dict: Dictionary representation of the DTO with all fields.
        """
        return self.model_dump(mode="python")
