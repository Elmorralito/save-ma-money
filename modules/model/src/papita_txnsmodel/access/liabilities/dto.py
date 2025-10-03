"""Liabilities DTO module for the Papita Transactions system.

This module defines the Data Transfer Objects (DTOs) for liability entities in the system.
It provides validation and data structures for different types of liabilities, including
general liabilities, bank credit liabilities, and credit card liabilities. These DTOs
ensure data integrity when transferring liability data between different layers of the
application.

Classes:
    LiabilityAccountsDTO: Base DTO for all liability accounts.
    ExtendedLiabilityAccountsDTO: Base DTO for specialized liability accounts.
    BankCreditLiabilityAccountsDTO: DTO for bank credit liability accounts.
    CreditCardLiabilityAccountsDTO: DTO for credit card liability accounts.
"""

import uuid
from typing import Annotated

from pydantic import Field, model_serializer

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.types.dto import (
    TypesDTO,
)
from papita_txnsmodel.model.liabilities import (
    BankCreditLiabilityAccounts,
    CreditCardLiabilityAccounts,
    LiabilityAccounts,
)
from papita_txnsmodel.utils.datautils import convert_dto_obj_on_serialize


class LiabilityAccountsDTO(TableDTO):
    """DTO for liability accounts with financial attributes and relationships.

    This class represents liability accounts in the system and includes validation
    rules to ensure data integrity. It extends TableDTO to inherit common
    functionality and links to the LiabilityAccounts ORM model.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        account (uuid.UUID | AccountsDTO): The account associated with this liability.
        account_type (uuid.UUID | TypesDTO): The type of this liability account.
        months_per_period (int): Number of months in each accounting period. Defaults to 1.
        initial_value (float): Initial value of the liability. Must be positive.
        present_value (float): Current value of the liability. Must be positive.
        monthly_interest_rate (float): Monthly interest rate. Must be positive.
        yearly_interest_rate (float): Yearly interest rate. Must be positive.
        payment (float): Regular payment amount. Must be positive.
        total_paid (float): Total amount paid so far. Defaults to 0.
        overall_periods (int): Total number of payment periods. Defaults to 1.
        periods_paid (int): Number of periods already paid. Defaults to 1.
        closing_day (int): Day of the month when the payment is due (1-28).
    """

    __dao_type__ = LiabilityAccounts

    account: Annotated[uuid.UUID | AccountsDTO, Field(alias="account_id")]
    account_type: Annotated[uuid.UUID | TypesDTO, Field(alias="account_type_id")]
    months_per_period: int = Field(gt=0, default=1, description="Number of months in each accounting period")
    initial_value: float = Field(gt=0, description="Initial value of the liability")
    present_value: float = Field(gt=0, description="Current value of the liability")
    monthly_interest_rate: float = Field(gt=0, description="Monthly interest rate")
    yearly_interest_rate: float = Field(gt=0, description="Yearly interest rate")
    payment: float = Field(gt=0, description="Regular payment amount")
    total_paid: float = Field(gt=0, default=0, description="Total amount paid so far")
    overall_periods: int = Field(gt=0, default=1, description="Total number of payment periods")
    periods_paid: int = Field(gt=0, default=1, description="Number of periods already paid")
    closing_day: int = Field(gt=0, le=28, description="Day of the month when the payment is due (1-28)")

    @model_serializer()
    def _serialize(self) -> dict:
        """Serialize the DTO to a dictionary, handling nested DTOs.

        This method converts nested DTO objects to their ID values for proper
        serialization to database models.

        Returns:
            dict: Dictionary representation of the DTO with proper ID references.
        """
        result = convert_dto_obj_on_serialize(
            obj=self,
            id_field="account",
            id_field_attr_name="id",
            target_field="account_id",
            expected_intput_field_type=AccountsDTO,
            expected_output_field_type=uuid.UUID,
        )
        result |= convert_dto_obj_on_serialize(
            obj=self,
            id_field="account_type",
            id_field_attr_name="id",
            target_field="account_type_id",
            expected_intput_field_type=TypesDTO,
            expected_output_field_type=uuid.UUID,
        )
        return result


class ExtendedLiabilityAccountsDTO(TableDTO):
    """Base DTO for specialized liability account types.

    This class serves as a base for more specific liability account DTOs, providing
    a common structure for linking to the base liability account.

    Attributes:
        liability_account (uuid.UUID | LiabilityAccountsDTO): The base liability account
            associated with this specialized liability account.
    """

    liability_account: Annotated[uuid.UUID | LiabilityAccountsDTO, Field(alias="liability_account_id")]

    @model_serializer()
    def _serialize(self) -> dict:
        """Serialize the DTO to a dictionary, handling nested DTOs.

        This method converts the nested liability_account DTO to its ID value for proper
        serialization to database models.

        Returns:
            dict: Dictionary representation of the DTO with proper ID references.
        """
        return convert_dto_obj_on_serialize(
            obj=self,
            id_field="liability_account",
            id_field_attr_name="id",
            target_field="liability_account_id",
            expected_intput_field_type=LiabilityAccountsDTO,
            expected_output_field_type=uuid.UUID,
        )


class BankCreditLiabilityAccountsDTO(ExtendedLiabilityAccountsDTO):
    """DTO for bank credit liability accounts.

    This class represents bank credit liability accounts in the system, such as
    mortgages, personal loans, and auto loans. It extends ExtendedLiabilityAccountsDTO
    to inherit the liability account relationship.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        insurance_payment (float): Additional payment for insurance. Cannot be negative.
        extras_payment (float): Additional miscellaneous payments. Cannot be negative.
    """

    __dao_type__ = BankCreditLiabilityAccounts

    insurance_payment: float = Field(ge=0, description="Additional payment for insurance")
    extras_payment: float = Field(ge=0, description="Additional miscellaneous payments")


class CreditCardLiabilityAccountsDTO(ExtendedLiabilityAccountsDTO):
    """DTO for credit card liability accounts.

    This class represents credit card liability accounts in the system. It extends
    ExtendedLiabilityAccountsDTO to inherit the liability account relationship.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        credit_limit (float): Maximum credit limit. Must be positive.
    """

    __dao_type__ = CreditCardLiabilityAccounts

    credit_limit: float = Field(gt=0, description="Maximum credit limit")
