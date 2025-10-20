import uuid
from typing import Dict, Generic, Self, Tuple, Type, TypeVarTuple

import pandas as pd
from pydantic import model_validator

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.services.base import BaseService
from papita_txnsregistrar.handlers.abstract import AbstractLoadHandler, S

ServiceDependencies = TypeVarTuple("ServiceDependencies")


class BaseLoadTableHandler(AbstractLoadHandler[S], Generic[*ServiceDependencies]):

    dependency_types: Tuple[*ServiceDependencies]
    depedencies: Dict[str, Type[BaseService] | BaseService]

    @model_validator(mode="after")
    def _validate_model(self) -> Self:
        # TODO: Make the logic to validate the dependencies.
        return self

    def get_record(
        self, dto: TableDTO | dict | str | uuid.UUID, from_dependecy: BaseService | None = None, **kwargs
    ) -> TableDTO:
        pass

    def get_records(
        self, dto: TableDTO | dict | str | uuid.UUID, from_dependecy: BaseService | None = None, **kwargs
    ) -> pd.DataFrame:
        pass
