import abc
from typing import Self

from pydantic import BaseModel


class AbstractCLIUtils(BaseModel, abc.ABC):

    @classmethod
    @abc.abstractmethod
    def load(cls, **kwargs) -> Self:
        pass
