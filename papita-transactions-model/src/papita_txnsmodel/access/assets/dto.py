"""Assets DTO module for the Papita Transactions system.

This module defines the Data Transfer Objects (DTOs) for asset entities in the system.
It provides validation and data structures for different types of assets, including
general assets, banking assets, real estate assets, and trading assets. These DTOs
ensure data integrity when transferring asset data between different layers of the
application.

Classes:
    AssetAccountsDTO: Base DTO for all asset accounts.
    ExtendedAssetAccountDTO: Base DTO for specialized asset accounts.
    BankingAssetAccountsDTO: DTO for banking-related asset accounts.
    RealEstateAssetAccountsDTO: DTO for real estate asset accounts.
    TradingAssetAccountsDTO: DTO for trading and investment asset accounts.
"""

import uuid
from typing import Annotated, Optional

from pydantic import Field, field_validator, model_serializer

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.liabilities.dto import BankCreditLiabilityAccountsDTO
from papita_txnsmodel.access.types.dto import TypesDTO
from papita_txnsmodel.model.assets import (
    AssetAccounts,
    BankingAssetAccounts,
    RealEstateAssetAccounts,
    TradingAssetAccounts,
)
from papita_txnsmodel.model.enums import RealEstateAssetAccountsAreaUnits, RealEstateAssetAccountsOwnership
from papita_txnsmodel.utils.datautils import convert_dto_obj_on_serialize


class AssetAccountsDTO(TableDTO):
    """DTO for asset accounts with financial attributes and relationships.

    This class represents asset accounts in the system and includes validation
    rules to ensure data integrity. It extends TableDTO to inherit common
    functionality and links to the AssetAccounts ORM model.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        account (uuid.UUID | AccountsDTO): The account associated with this asset.
        account_type (uuid.UUID | TypesDTO): The type of this asset account.
        bank_credit_liability_account (Optional[uuid.UUID | BankCreditLiabilityAccountsDTO]):
            Associated bank credit liability account, if any.
        months_per_period (int): Number of months in each accounting period. Defaults to 1.
        initial_value (Optional[float]): Initial value of the asset. Must be positive if provided.
        last_value (Optional[float]): Most recent value of the asset. Must be positive if provided.
        monthly_interest_rate (Optional[float]): Monthly interest rate. Must be positive if provided.
        yearly_interest_rate (Optional[float]): Yearly interest rate. Must be positive if provided.
        roi (Optional[float]): Return on investment. Must be positive if provided.
        periodical_earnings (Optional[float]): Earnings per period. Must be positive if provided.
    """

    __dao_type__ = AssetAccounts

    account: Annotated[uuid.UUID | AccountsDTO, Field(alias="account_id")]
    account_type: Annotated[uuid.UUID | TypesDTO, Field(alias="account_type_id")]
    bank_credit_liability_account: Optional[
        Annotated[uuid.UUID | BankCreditLiabilityAccountsDTO, Field(alias="bank_credit_liability_account_id")]
    ] = None
    months_per_period: int = 1
    initial_value: Optional[float] = None
    last_value: Optional[float] = None
    monthly_interest_rate: Optional[float] = None
    yearly_interest_rate: Optional[float] = None
    roi: Optional[float] = None
    periodical_earnings: Optional[float] = None

    @field_validator("months_per_period")
    @classmethod
    def months_per_period_must_be_positive(cls, v: int) -> int:
        """Validate that months_per_period is positive.

        Args:
            v: The months_per_period value to validate.

        Returns:
            int: The validated months_per_period.

        Raises:
            ValueError: If months_per_period is not greater than 0.
        """
        if v <= 0:
            raise ValueError("months_per_period must be greater than 0")
        return v

    @field_validator("initial_value")
    @classmethod
    def initial_value_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        """Validate that initial_value is positive if provided.

        Args:
            v: The initial_value to validate.

        Returns:
            Optional[float]: The validated initial_value.

        Raises:
            ValueError: If initial_value is not greater than 0.
        """
        if v is not None and v <= 0:
            raise ValueError("initial_value must be greater than 0")
        return v

    @field_validator("last_value")
    @classmethod
    def last_value_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        """Validate that last_value is positive if provided.

        Args:
            v: The last_value to validate.

        Returns:
            Optional[float]: The validated last_value.

        Raises:
            ValueError: If last_value is not greater than 0.
        """
        if v is not None and v <= 0:
            raise ValueError("last_value must be greater than 0")
        return v

    @field_validator("monthly_interest_rate")
    @classmethod
    def monthly_interest_rate_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        """Validate that monthly_interest_rate is positive if provided.

        Args:
            v: The monthly_interest_rate to validate.

        Returns:
            Optional[float]: The validated monthly_interest_rate.

        Raises:
            ValueError: If monthly_interest_rate is not greater than 0.
        """
        if v is not None and v <= 0:
            raise ValueError("monthly_interest_rate must be greater than 0")
        return v

    @field_validator("yearly_interest_rate")
    @classmethod
    def yearly_interest_rate_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        """Validate that yearly_interest_rate is positive if provided.

        Args:
            v: The yearly_interest_rate to validate.

        Returns:
            Optional[float]: The validated yearly_interest_rate.

        Raises:
            ValueError: If yearly_interest_rate is not greater than 0.
        """
        if v is not None and v <= 0:
            raise ValueError("yearly_interest_rate must be greater than 0")
        return v

    @field_validator("roi")
    @classmethod
    def roi_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        """Validate that roi is positive if provided.

        Args:
            v: The roi value to validate.

        Returns:
            Optional[float]: The validated roi.

        Raises:
            ValueError: If roi is not greater than 0.
        """
        if v is not None and v <= 0:
            raise ValueError("roi must be greater than 0")
        return v

    @field_validator("periodical_earnings")
    @classmethod
    def periodical_earnings_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        """Validate that periodical_earnings is positive if provided.

        Args:
            v: The periodical_earnings value to validate.

        Returns:
            Optional[float]: The validated periodical_earnings.

        Raises:
            ValueError: If periodical_earnings is not greater than 0.
        """
        if v is not None and v <= 0:
            raise ValueError("periodical_earnings must be greater than 0")
        return v

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
        if isinstance(self.bank_credit_liability_account, (BankCreditLiabilityAccountsDTO, uuid.UUID)):
            result |= convert_dto_obj_on_serialize(
                obj=self,
                id_field="bank_credit_liability_account",
                id_field_attr_name="id",
                target_field="bank_credit_liability_account_id",
                expected_intput_field_type=BankCreditLiabilityAccountsDTO,
                expected_output_field_type=uuid.UUID,
            )

        return result


class ExtendedAssetAccountDTO(TableDTO):
    """Base DTO for specialized asset account types.

    This class serves as a base for more specific asset account DTOs, providing
    a common structure for linking to the base asset account.

    Attributes:
        asset_account (uuid.UUID | AssetAccountsDTO): The base asset account
            associated with this specialized asset account.
    """

    asset_account: Annotated[uuid.UUID | AssetAccountsDTO, Field(alias="asset_account_id")]

    @model_serializer()
    def _serialize(self) -> dict:
        """Serialize the DTO to a dictionary, handling nested DTOs.

        This method converts the nested asset_account DTO to its ID value for proper
        serialization to database models.

        Returns:
            dict: Dictionary representation of the DTO with proper ID references.
        """
        return convert_dto_obj_on_serialize(
            obj=self,
            id_field="asset_account",
            id_field_attr_name="id",
            target_field="asset_account_id",
            expected_intput_field_type=AssetAccountsDTO,
            expected_output_field_type=uuid.UUID,
        )


class BankingAssetAccountsDTO(ExtendedAssetAccountDTO):
    """DTO for banking-related asset accounts.

    This class represents banking asset accounts in the system, such as checking
    accounts, savings accounts, and certificates of deposit. It extends
    ExtendedAssetAccountDTO to inherit the asset account relationship.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        entity (str): The banking entity or institution name.
        account_number (Optional[str]): The account number at the banking institution.
    """

    __dao_type__ = BankingAssetAccounts

    entity: str
    account_number: Optional[str] = None

    @field_validator("entity")
    @classmethod
    def entity_must_not_be_empty(cls, v: str) -> str:
        """Validate that entity is not empty.

        Args:
            v: The entity value to validate.

        Returns:
            str: The validated entity.

        Raises:
            ValueError: If entity is empty or contains only whitespace.
        """
        if not v or v.isspace():
            raise ValueError("entity cannot be empty")
        return v


class RealEstateAssetAccountsDTO(ExtendedAssetAccountDTO):
    """DTO for real estate asset accounts.

    This class represents real estate asset accounts in the system, such as
    houses, apartments, and land. It extends ExtendedAssetAccountDTO to inherit
    the asset account relationship.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        address (str): The physical address of the property.
        city (str): The city where the property is located.
        country (str): The country where the property is located.
        total_area (float): The total area of the property (must be positive).
        built_area (float | None): The built area of the property (must be positive if provided).
        area_unit (RealEstateAssetAccountsAreaUnits): The unit of measurement for areas.
            Defaults to square meters.
        ownership (RealEstateAssetAccountsOwnership): The type of ownership of the property.
        participation (float): The ownership participation percentage (0.0-1.0).
            Defaults to 1.0 (100%).
    """

    __dao_type__ = RealEstateAssetAccounts

    address: str
    city: str
    country: str
    total_area: Annotated[float, Field(gt=0.0)]
    built_area: Annotated[float, Field(gt=0.0)] | None = None
    area_unit: RealEstateAssetAccountsAreaUnits = RealEstateAssetAccountsAreaUnits.SQ_MT
    ownership: RealEstateAssetAccountsOwnership
    participation: Annotated[float, Field(gt=0.0, le=1.0)] = 1


class TradingAssetAccountsDTO(ExtendedAssetAccountDTO):
    """DTO for trading and investment asset accounts.

    This class represents trading asset accounts in the system, such as stocks,
    bonds, and other investment vehicles. It extends ExtendedAssetAccountDTO to
    inherit the asset account relationship.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        buy_value (float): The purchase value of the asset.
        last_value (Optional[float]): The most recent value of the asset.
        units (int): The number of units owned. Defaults to 1.
    """

    __dao_type__ = TradingAssetAccounts

    buy_value: float
    last_value: Optional[float] = None
    units: int = 1

    @field_validator("buy_value")
    @classmethod
    def buy_value_must_be_positive(cls, v: float) -> float:
        """Validate that buy_value is positive.

        Args:
            v: The buy_value to validate.

        Returns:
            float: The validated buy_value.

        Raises:
            ValueError: If buy_value is not greater than 0.
        """
        if v <= 0:
            raise ValueError("buy_value must be greater than 0")
        return v

    @field_validator("last_value")
    @classmethod
    def last_value_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        """Validate that last_value is positive if provided.

        Args:
            v: The last_value to validate.

        Returns:
            Optional[float]: The validated last_value.

        Raises:
            ValueError: If last_value is not greater than 0.
        """
        if v is not None and v <= 0:
            raise ValueError("last_value must be greater than 0")
        return v

    @field_validator("units")
    @classmethod
    def units_must_be_positive(cls, v: int) -> int:
        """Validate that units is positive.

        Args:
            v: The units value to validate.

        Returns:
            int: The validated units.

        Raises:
            ValueError: If units is not greater than 0.
        """
        if v <= 0:
            raise ValueError("units must be greater than 0")
        return v
