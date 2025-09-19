import datetime
from typing import Optional

from pydantic import Field, field_validator

from papita_txnsmodel.access.base.dto import CoreTableDTO
from papita_txnsmodel.model.accounts import Accounts


class AccountsDTO(CoreTableDTO):
    """DTO for Accounts model.

    Includes field validations that match the constraints in the ORM model.
    """

    __dao_type__ = Accounts

    start_ts: datetime.datetime = Field(default_factory=datetime.datetime.now)
    end_ts: Optional[datetime.datetime] = None

    @field_validator("end_ts")
    @classmethod
    def end_ts_must_be_after_start_ts(cls, value: Optional[datetime.datetime], info) -> Optional[datetime.datetime]:
        if value is not None:
            start_ts = info.data.get("start_ts")
            if start_ts and value <= start_ts:
                raise ValueError("end_ts must be after start_ts")

        return value
