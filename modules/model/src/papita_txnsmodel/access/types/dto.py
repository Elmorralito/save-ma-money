"""Types DTO module for the Papita Transactions system.

This module defines the Data Transfer Object (DTO) for type entities in the system.
It provides a flexible structure for representing different types of financial entities
such as assets, liabilities, and transactions. The TypesDTO extends CoreTableDTO to
inherit common functionality while adding type-specific attributes.

Classes:
    TypesDTO: DTO for type entities with discriminator for categorization.
"""

import uuid

from pydantic import ConfigDict, model_serializer

from papita_txnsmodel.access.base.dto import CoreTableDTO
from papita_txnsmodel.model.types import Types, TypesClassifications
from papita_txnsmodel.utils.datautils import convert_dto_obj_on_serialize


class TypesClassificationsDTO(CoreTableDTO):

    __dao_type__ = TypesClassifications


class TypesDTO(CoreTableDTO):
    """DTO for type entities in the Papita Transactions system.

    This class represents type entities that categorize different financial objects
    in the system. It extends CoreTableDTO to inherit common fields like name,
    description, and tags, while adding a discriminator field to identify the
    category of the type.

    The class allows for extra fields beyond those explicitly defined, which enables
    flexibility in representing different type categories with varying attributes.

    Attributes:
        model_config (ConfigDict): Configuration allowing extra fields beyond those defined.
        __dao_type__ (type): The ORM model class this DTO corresponds to.
    """

    model_config = ConfigDict(extra="allow")
    __dao_type__ = Types

    classification: uuid.UUID | TypesClassificationsDTO

    @model_serializer()
    def _serialize(self) -> dict:
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
