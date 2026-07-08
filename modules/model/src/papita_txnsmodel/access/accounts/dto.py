"""Accounts DTO module for the Papita Transactions system.

This module defines the Data Transfer Object (DTO) for account entities in the system.
It provides validation and data structure for account information, ensuring data
integrity when transferring account data between different layers of the application.

Classes:
    AccountsDTO: Data Transfer Object for v3 account entities with validation rules.
"""

import datetime
from typing import Optional

from pydantic import Field, field_validator

from papita_txnsmodel.access.base.dto import CoreTableDTO
from papita_txnsmodel.access.users.dto import OwnedTableDTO
from papita_txnsmodel.model.accounts import Accounts
from papita_txnsmodel.model.enums import AccountKind, InterestRateBasis, LedgerSide


class AccountsDTO(OwnedTableDTO, CoreTableDTO):
    """DTO for Accounts model with field validations matching ORM constraints.

    This class represents v3 consolidated account data in the system. It extends
    CoreTableDTO to inherit common functionality for all table DTOs and links to
    the Accounts ORM model.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        account_kind (AccountKind): Discriminator for the consolidated account row.
        ledger_side (LedgerSide): Balance sheet side (asset or liability).
        currency (str): ISO 4217 currency code.
        opened_at (datetime.datetime): Timestamp when the account was opened.
        closed_at (Optional[datetime.datetime]): Timestamp when the account was closed.
    """

    __dao_type__ = Accounts

    account_kind: AccountKind
    ledger_side: LedgerSide
    currency: str = Field(min_length=3, max_length=3, default="USD")
    opened_at: datetime.datetime = Field(default_factory=datetime.datetime.now)
    closed_at: Optional[datetime.datetime] = None
    initial_value: float | None = Field(default=None, ge=0)
    current_value: float | None = Field(default=None, ge=0)
    current_value_as_of: datetime.datetime | None = None
    months_per_period: int | None = Field(default=1, gt=0)
    interest_rate: float | None = None
    interest_rate_basis: InterestRateBasis | None = None
    periodic_payment: float | None = None
    total_paid: float | None = Field(default=0, ge=0)
    overall_periods: int | None = None
    periods_paid: int | None = None
    closing_day: int | None = Field(default=None, ge=1, le=31)
    roi: float | None = None
    periodic_earnings: float | None = None

    @field_validator("closed_at")
    @classmethod
    def closed_at_must_be_after_opened_at(cls, value: Optional[datetime.datetime], info) -> Optional[datetime.datetime]:
        """Validate that closed_at is after opened_at if provided.

        Args:
            value: The closed timestamp value to validate.
            info: Validation context containing other field values.

        Returns:
            Optional[datetime.datetime]: The validated closed timestamp.

        Raises:
            ValueError: If closed_at is not after opened_at when both are provided.
        """
        if value is not None:
            opened_at = info.data.get("opened_at")
            if opened_at and value <= opened_at:
                raise ValueError("closed_at must be after opened_at")

        return value
