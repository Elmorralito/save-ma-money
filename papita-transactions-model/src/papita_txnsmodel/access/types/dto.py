from typing import Literal

from pydantic import ConfigDict

from papita_txnsmodel.access.base.dto import CoreTableDTO
from papita_txnsmodel.model.types import Types


class TypesDTO(CoreTableDTO):
    model_config = ConfigDict(extra="allow")
    __dao_type__ = Types
    discriminator: Literal["assets", "liabilities", "transactions"]

    @property
    def row(self) -> dict:
        return self.model_dump(mode="python")
