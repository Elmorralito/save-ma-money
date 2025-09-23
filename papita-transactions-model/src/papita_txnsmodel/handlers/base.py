from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.utils.classutils import FallbackAction

T = TypeVar("T", bound=BaseService)


class BaseHandler(BaseModel, Generic[T]):
    model_config = ConfigDict(extra="allow", arbitrary_types_allowed=True)

    service: T | None = None
    error_handler: FallbackAction = FallbackAction.RAISE

    def setup_service(self, service: T, **kwargs) -> "BaseHandler":
        if not isinstance(service, BaseService):
            raise TypeError("Service type not compatible with this handler.")

        self.service = service
        return self

    @property
    def checked_service(self) -> T:
        if not self.service:
            raise ValueError("The service has not being loaded.")

        self.connector.connected(on_disconnected=self.error_handler)
        return self.service
