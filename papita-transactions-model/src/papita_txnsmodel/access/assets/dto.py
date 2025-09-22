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
    RealStateAssetAccounts,
    TradingAssetAccounts,
)
from papita_txnsmodel.model.enums import RealStateAssetAccountsAreaUnits, RealStateAssetAccountsOwnership
from papita_txnsmodel.utils.datautils import convert_dto_obj_on_serialize


class AssetAccountsDTO(TableDTO):
    """DTO for AssetAccounts model."""

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
        if v <= 0:
            raise ValueError("months_per_period must be greater than 0")
        return v

    @field_validator("initial_value")
    @classmethod
    def initial_value_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("initial_value must be greater than 0")
        return v

    @field_validator("last_value")
    @classmethod
    def last_value_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("last_value must be greater than 0")
        return v

    @field_validator("monthly_interest_rate")
    @classmethod
    def monthly_interest_rate_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("monthly_interest_rate must be greater than 0")
        return v

    @field_validator("yearly_interest_rate")
    @classmethod
    def yearly_interest_rate_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("yearly_interest_rate must be greater than 0")
        return v

    @field_validator("roi")
    @classmethod
    def roi_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("roi must be greater than 0")
        return v

    @field_validator("periodical_earnings")
    @classmethod
    def periodical_earnings_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("periodical_earnings must be greater than 0")
        return v

    @model_serializer()
    def _serialize(self) -> dict:
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

    asset_account: Annotated[uuid.UUID | AssetAccountsDTO, Field(alias="asset_account_id")]

    @model_serializer()
    def _serialize(self) -> dict:
        return convert_dto_obj_on_serialize(
            obj=self,
            id_field="asset_account",
            id_field_attr_name="id",
            target_field="asset_account_id",
            expected_intput_field_type=AssetAccountsDTO,
            expected_output_field_type=uuid.UUID,
        )


class BankingAssetAccountsDTO(ExtendedAssetAccountDTO):
    """DTO for BankingAssetAccounts model."""

    __dao_type__ = BankingAssetAccounts

    entity: str
    account_number: Optional[str] = None

    @field_validator("entity")
    @classmethod
    def entity_must_not_be_empty(cls, v: str) -> str:
        if not v or v.isspace():
            raise ValueError("entity cannot be empty")
        return v


class RealStateAssetAccountsDTO(ExtendedAssetAccountDTO):
    """DTO for RealStateAssetAccounts model."""

    __dao_type__ = RealStateAssetAccounts

    address: str
    city: str
    country: str
    total_area: Annotated[float, Field(gt=0.0)]
    built_area: Annotated[float, Field(gt=0.0)] | None = None
    area_unit: RealStateAssetAccountsAreaUnits = RealStateAssetAccountsAreaUnits.SQ_MT
    ownership: RealStateAssetAccountsOwnership
    participation: Annotated[float, Field(gt=0.0, le=1.0)] = 1


class TradingAssetAccountsDTO(ExtendedAssetAccountDTO):
    """DTO for TradingAssetAccounts model."""

    __dao_type__ = TradingAssetAccounts

    buy_value: float
    last_value: Optional[float] = None
    units: int = 1

    @field_validator("buy_value")
    @classmethod
    def buy_value_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("buy_value must be greater than 0")
        return v

    @field_validator("last_value")
    @classmethod
    def last_value_must_be_positive(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError("last_value must be greater than 0")
        return v

    @field_validator("units")
    @classmethod
    def units_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("units must be greater than 0")
        return v
