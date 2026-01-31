"""AccountsIndexer Data Transfer Object module.

This module defines the AccountsIndexerDTO class which serves as a data transfer object
for the AccountsIndexer model. It facilitates the serialization and deserialization of
AccountsIndexer instances while enforcing data integrity rules that maintain the
polymorphic account relationship structure. The DTO ensures that accounts are properly
linked according to their types and that relationship constraints are maintained.
"""

import uuid
from typing import get_args

from pydantic import Field, field_serializer, model_validator

from papita_txnsmodel.access.base.dto import TableDTO

from papita_txnsmodel.access.accounts.dto import AccountsDTO
from papita_txnsmodel.access.assets.dto import (
    AssetAccountsDTO,
    BankingAssetAccountsDTO,
    ExtendedAssetAccountsDTO,
    RealEstateAssetAccountsDTO,
    TradingAssetAccountsDTO,
)
from papita_txnsmodel.access.users.dto import OwnedTableDTO
from papita_txnsmodel.access.liabilities.dto import (
    BankCreditLiabilityAccountsDTO,
    CreditCardLiabilityAccountsDTO,
    ExtendedLiabilityAccountsDTO,
    LiabilityAccountsDTO,
)
from papita_txnsmodel.access.types.dto import TypesDTO
from papita_txnsmodel.model.indexers import AccountsIndexer


class AccountsIndexerDTO(OwnedTableDTO):
    """Data transfer object for the AccountsIndexer model.

    This class represents the data structure for account indexing in the transaction model.
    It enforces validation rules to ensure the integrity of account relationships,
    specifically that an account can only be either an asset or a liability (not both),
    and that extended account types are properly linked to their parent types.

    Attributes:
        account: Base account reference or ID.
        type: Account type reference or ID.
        asset_account: Optional reference to an asset account.
        liability_account: Optional reference to a liability account.
        banking_asset_account: Optional reference to a banking asset account.
        real_estate_asset_account: Optional reference to a real estate asset account.
        trading_asset_account: Optional reference to a trading asset account.
        bank_credit_liability_account: Optional reference to a bank credit liability account.
        credit_card_liability_account: Optional reference to a credit card liability account.
    """

    __dao_type__ = AccountsIndexer

    account: uuid.UUID | AccountsDTO = Field(..., serialization_alias="account_id")
    type: uuid.UUID | TypesDTO = Field(..., serialization_alias="type_id")
    asset_account: uuid.UUID | AssetAccountsDTO | None = Field(default=None, serialization_alias="asset_account_id")
    liability_account: uuid.UUID | LiabilityAccountsDTO | None = Field(
        default=None, serialization_alias="liability_account_id"
    )
    banking_asset_account: uuid.UUID | BankingAssetAccountsDTO | None = Field(
        default=None, serialization_alias="banking_asset_account_id"
    )
    real_estate_asset_account: uuid.UUID | RealEstateAssetAccountsDTO | None = Field(
        default=None, serialization_alias="real_estate_asset_account_id"
    )
    trading_asset_account: uuid.UUID | TradingAssetAccountsDTO | None = Field(
        default=None, serialization_alias="trading_asset_account_id"
    )
    bank_credit_liability_account: uuid.UUID | BankCreditLiabilityAccountsDTO | None = Field(
        default=None, serialization_alias="bank_credit_liability_account_id"
    )
    credit_card_liability_account: uuid.UUID | CreditCardLiabilityAccountsDTO | None = Field(
        default=None, serialization_alias="credit_card_liability_account_id"
    )

    @field_serializer(
        "account",
        "type",
        "asset_account",
        "liability_account",
        "banking_asset_account",
        "real_estate_asset_account",
        "trading_asset_account",
        "bank_credit_liability_account",
        "credit_card_liability_account",
    )
    def _serialize_relations(self, value: uuid.UUID | TableDTO | None) -> uuid.UUID | None:
        """Serialize relationship fields to their ID values.

        This serializer ensures that relationship fields are consistently represented as UUIDs
        in the serialized output, regardless of whether they were provided as full DTO objects
        or just UUIDs.

        Args:
            value: The relationship value to serialize, either a UUID, TableDTO instance, or None.

        Returns:
            uuid.UUID or None: The UUID of the related entity, or None if no relation exists.
        """
        if not value:
            return None

        return value.id if isinstance(value, TableDTO) else value

    @model_validator(mode="after")
    def _model_validate(self) -> "AccountsIndexerDTO":
        """Validate the model after initialization.

        This method performs a series of validations to ensure that account relationships
        are properly structured according to business rules. It checks that:
        1. The account is either an asset or a liability (not both or neither)
        2. Only one extended account type is specified
        3. Extended account types match the base account type

        Returns:
            AccountsIndexerDTO: The validated instance

        Raises:
            ValueError: If any validation check fails
        """
        self._validate_accounts()
        self._validate_extended_accounts()
        self._validate_linked_accounts()
        return self

    def _validate_accounts(self) -> "AccountsIndexerDTO":
        """Validate base account relationship integrity.

        Ensures that the account must be either an asset or a liability, but not both
        and not neither. This enforces the basic classification constraint for accounts.

        Returns:
            AccountsIndexerDTO: The instance with validated accounts

        Raises:
            ValueError: If both asset and liability are None or if both are set
        """
        match self.asset_account, self.liability_account:
            case None, None:
                raise ValueError("The index cannot contain empty asset and liability.")
            case _, _:
                raise ValueError("The index cannot contain both asset and liability.")
        return self

    def _validate_extended_accounts(self) -> "AccountsIndexerDTO":
        """Validate that only one extended account type is specified.

        Ensures that an account cannot be of multiple extended types simultaneously,
        which would violate the account type hierarchy. The method checks all fields
        annotated with extended account types to ensure at most one is set.

        Returns:
            AccountsIndexerDTO: The instance with validated extended accounts

        Raises:
            ValueError: If more than one extended account is set
        """
        extended_account_fields = [
            field_name
            for field_name, info in self.__class__.model_fields.items()
            if ExtendedAssetAccountsDTO in get_args(info.annotation)
            or ExtendedLiabilityAccountsDTO in get_args(info.annotation)
        ]
        extended_accounts_count = sum(1 for field in extended_account_fields if getattr(self, field) is not None)
        if extended_accounts_count > 1:
            raise ValueError("The index cannot contain more than extended account.")

        return self

    def _validate_linked_accounts(self) -> "AccountsIndexerDTO":
        """Validate that extended accounts match their parent type.

        Ensures that extended accounts (e.g., banking assets) are consistent with their
        base account type (e.g., asset). This prevents incorrect account type linkages
        by checking that any extended account field references an account of the
        appropriate base type.

        Returns:
            AccountsIndexerDTO: The instance with validated linked accounts

        Raises:
            ValueError: If an extended account type doesn't match its parent type
        """
        match self.asset_account, self.liability_account:
            case None, _:
                extended_account_type = ExtendedAssetAccountsDTO
            case _, None:
                extended_account_type = ExtendedLiabilityAccountsDTO

        extended_account_fields = [
            field_name
            for field_name, info in self.__class__.model_fields.items()
            if extended_account_type in get_args(info.annotation)
            or ExtendedLiabilityAccountsDTO in get_args(info.annotation)
        ]
        extended_accounts_count = sum(1 for field in extended_account_fields if getattr(self, field) is not None)
        if extended_accounts_count > 0:
            raise ValueError(f"Extended account is not of type {extended_account_type.__name__}")

        return self
