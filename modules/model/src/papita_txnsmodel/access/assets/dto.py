"""Assets DTO module for the Papita Transactions system.

This module defines the Data Transfer Objects (DTOs) for asset entities in the system.
It provides validation and data structures for different types of assets, including
general assets, banking assets, real estate assets, and trading assets. These DTOs
ensure data integrity when transferring asset data between different layers of the
application.

Classes:
    AssetAccountsDTO: Base DTO for all asset accounts.
    ExtendedAssetAccountsDTO: Base DTO for specialized asset accounts.
    FinancedAssetAccountsDTO: DTO for assets that are partially or fully financed.
    BankingAssetAccountsDTO: DTO for banking-related asset accounts.
    RealEstateAssetAccountsDTO: DTO for real estate asset accounts.
    TradingAssetAccountsDTO: DTO for trading and investment asset accounts.
"""

import uuid
from typing import Annotated, Optional

from pydantic import Field, model_serializer

from papita_txnsmodel.access.liabilities.dto import BankCreditLiabilityAccountsDTO
from papita_txnsmodel.access.users.dto import OwnedTableDTO
from papita_txnsmodel.model.assets import (
    AssetAccounts,
    BankingAssetAccounts,
    RealEstateAssetAccounts,
    TradingAssetAccounts,
)
from papita_txnsmodel.model.enums import RealEstateAssetAccountsAreaUnits, RealEstateAssetAccountsOwnership
from papita_txnsmodel.utils.datautils import convert_dto_obj_on_serialize
from papita_txnsmodel.utils.modelutils import validate_interest_rate


class AssetAccountsDTO(OwnedTableDTO):
    """DTO for asset accounts with financial attributes and relationships.

    This class represents asset accounts in the system and includes validation
    rules to ensure data integrity. It extends TableDTO to inherit common
    functionality and links to the AssetAccounts ORM model.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        account (uuid.UUID | AccountsDTO): The account associated with this asset.
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

    months_per_period: Annotated[int, Field(gt=0)] = 1
    initial_value: Annotated[Optional[float], Field(gt=0)] = None
    last_value: Annotated[Optional[float], Field(gt=0)] = None
    monthly_interest_rate: Annotated[Optional[float], Field(gt=0), validate_interest_rate] = None
    yearly_interest_rate: Annotated[Optional[float], Field(gt=0), validate_interest_rate] = None
    roi: Annotated[Optional[float], Field(gt=0), validate_interest_rate] = None
    periodical_earnings: Annotated[Optional[float], Field(gt=0)] = None


class ExtendedAssetAccountsDTO(OwnedTableDTO):
    """Base DTO for specialized asset account types.

    This class serves as a base for more specific asset account DTOs, providing
    a common structure for linking to the base asset account.

    Attributes:
        asset_account (uuid.UUID | AssetAccountsDTO): The base asset account
            associated with this specialized asset account.
    """


class FinancedAssetAccountsDTO(ExtendedAssetAccountsDTO):
    """DTO for financed asset accounts.

    This class represents asset accounts that are partially or fully financed through
    credit or loans. It extends ExtendedAssetAccountsDTO to inherit the asset account
    relationship structure and provides attributes for tracking financing details.
    Attributes:
        bank_credit_liability_account (Optional[uuid.UUID | BankCreditLiabilityAccountsDTO]):
            The bank credit or loan account associated with financing this asset.
        asset_account (Optional[uuid.UUID | AssetAccountsDTO]):
            The base asset account associated with this financed asset.
        financing_share (float): The portion of the asset that is financed (0.0-1.0).
            Must be greater than 0 and less than or equal to 1. Defaults to 0.0.
    """

    bank_credit_liability_account: uuid.UUID | BankCreditLiabilityAccountsDTO | None = Field(
        serialization_alias="bank_credit_liability_account_id"
    )
    asset_account: uuid.UUID | AssetAccountsDTO | None = Field(default=None, serialization_alias="asset_account_id")
    financing_share: Annotated[float, Field(le=1, gt=0)] = 0.0

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
            id_field="bank_credit_liability_account",
            id_field_attr_name="id",
            target_field="bank_credit_liability_account_id",
            expected_intput_field_type=BankCreditLiabilityAccountsDTO,
            expected_output_field_type=uuid.UUID,
        )
        result |= convert_dto_obj_on_serialize(
            obj=self,
            id_field="asset_account",
            id_field_attr_name="id",
            target_field="asset_account_id",
            expected_intput_field_type=AssetAccountsDTO,
            expected_output_field_type=uuid.UUID,
        )

        return result


class BankingAssetAccountsDTO(ExtendedAssetAccountsDTO):
    """DTO for banking-related asset accounts.

    This class represents banking asset accounts in the system, such as checking
    accounts, savings accounts, and certificates of deposit. It extends
    ExtendedAssetAccountsDTO to inherit the asset account relationship.
    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        entity (str): The banking entity or institution name.
        account_number (Optional[str]): The account number at the banking institution.
    """

    __dao_type__ = BankingAssetAccounts

    entity: Annotated[str, Field(min_length=1, pattern=r"\S")]
    account_number: Optional[str] = None


class RealEstateAssetAccountsDTO(ExtendedAssetAccountsDTO):
    """DTO for real estate asset accounts.

    This class represents real estate asset accounts in the system, such as
    houses, apartments, and land. It extends ExtendedAssetAccountsDTO to inherit
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


class TradingAssetAccountsDTO(ExtendedAssetAccountsDTO):
    """DTO for trading and investment asset accounts.

    This class represents trading asset accounts in the system, such as stocks,
    bonds, and other investment vehicles. It extends ExtendedAssetAccountsDTO to
    inherit the asset account relationship.

    Attributes:
        __dao_type__ (type): The ORM model class this DTO corresponds to.
        buy_value (float): The purchase value of the asset.
        last_value (Optional[float]): The most recent value of the asset.
        units (int): The number of units owned. Defaults to 1.
    """

    __dao_type__ = TradingAssetAccounts

    buy_value: Annotated[float, Field(gt=0)]
    last_value: Annotated[Optional[float], Field(gt=0)] = None
    units: Annotated[int, Field(gt=0)] = 1
