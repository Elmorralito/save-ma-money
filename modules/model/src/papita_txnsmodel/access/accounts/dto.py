"""Accounts DTO module for the Papita Transactions system.

This module defines the Data Transfer Object (DTO) for account entities in the system.
It provides validation and data structure for account information, ensuring data
integrity when transferring account data between different layers of the application.

Classes:
    AccountsDTO: Data Transfer Object for account entities with validation rules.
"""

import datetime
from typing import Optional

from pydantic import Field, field_validator

from papita_txnsmodel.access.base.dto import CoreTableDTO
from papita_txnsmodel.access.users.dto import OwnedTableDTO
from papita_txnsmodel.model.accounts import Accounts


class AccountsDTO(OwnedTableDTO, CoreTableDTO):
    """DTO for Accounts model with field validations matching ORM constraints.

    This class represents account data in the system and includes validation
    rules to ensure data integrity. It extends CoreTableDTO to inherit common
    functionality for all table DTOs and links to the Accounts ORM model.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        start_ts (datetime.datetime): Timestamp when the account becomes active.
            Defaults to the current datetime.
        end_ts (Optional[datetime.datetime]): Timestamp when the account becomes
            inactive. Defaults to None, indicating the account is still active.
    """

    __dao_type__ = Accounts

    start_ts: datetime.datetime = Field(default_factory=datetime.datetime.now)
    end_ts: Optional[datetime.datetime] = None

    @field_validator("end_ts")
    @classmethod
    def end_ts_must_be_after_start_ts(cls, value: Optional[datetime.datetime], info) -> Optional[datetime.datetime]:
        """Validate that end_ts is after start_ts if provided.

        This validator ensures temporal consistency by checking that when an end
        timestamp is provided, it occurs after the start timestamp.

        Args:
            value: The end timestamp value to validate.
            info: Validation context containing other field values.

        Returns:
            Optional[datetime.datetime]: The validated end timestamp.

        Raises:
            ValueError: If end_ts is not after start_ts when both are provided.
        """
        if value is not None:
            start_ts = info.data.get("start_ts")
            if start_ts and value <= start_ts:
                raise ValueError("end_ts must be after start_ts")

        return value
