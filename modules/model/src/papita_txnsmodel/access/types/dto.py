"""Types DTO module for the Papita Transactions system.

This module defines Data Transfer Objects (DTOs) for type entities in the system.
It provides flexible structures for representing different types of financial entities
such as assets, liabilities, and transactions, as well as their classifications.
Classes:
    TypesClassificationsDTO: DTO for type classification entities.
    TypesDTO: DTO for type entities with reference to their classification.
"""

import uuid

from pydantic import ConfigDict, model_serializer

from papita_txnsmodel.access.base.dto import CoreTableDTO
from papita_txnsmodel.model.types import Types, TypesClassifications
from papita_txnsmodel.utils.datautils import convert_dto_obj_on_serialize


class TypesClassificationsDTO(CoreTableDTO):
    """DTO for type classification entities in the Papita Transactions system.

    This class represents classification entities that categorize different types
    in the system. It extends CoreTableDTO to inherit common fields like id, name,
    description, and tags. These classifications serve as categories for the various
    types defined in the system.
    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to,
            set to TypesClassifications.
    """

    __dao_type__ = TypesClassifications


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

    classification: uuid.UUID | TypesClassificationsDTO

    @model_serializer()
    def _serialize(self) -> dict:
        """Serialize the DTO to a dictionary.

        This serializer method converts TypesClassificationsDTO objects in the
        'classification' field to UUID references for proper serialization.

        Returns:
            dict: Serialized representation of the DTO with classification
                converted to a UUID if needed.
        """
        return convert_dto_obj_on_serialize(
            obj=self,
            id_field="classification",
            id_field_attr_name="id",
            target_field="classification",
            expected_intput_field_type=TypesClassificationsDTO,
            expected_output_field_type=uuid.UUID,
        )

    @property
    def row(self) -> dict:
        """Get a dictionary representation of this DTO.

        This property provides a convenient way to convert the DTO to a dictionary
        format suitable for data manipulation or serialization.

        Returns:
            dict: Dictionary representation of the DTO with all fields.
        """
        return self.model_dump(mode="python")
