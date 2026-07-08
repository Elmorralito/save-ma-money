"""DTO for asset–loan financing join rows."""

import uuid

from pydantic import Field

from papita_txnsmodel.access.users.dto import OwnedTableDTO
from papita_txnsmodel.model.account_financing import AccountFinancing


class AccountFinancingDTO(OwnedTableDTO):
    """DTO for account financing relationships."""

    __dao_type__ = AccountFinancing

    asset_account_id: uuid.UUID
    loan_account_id: uuid.UUID
    financing_share: float = Field(default=1.0, gt=0, le=1)

    def to_dao(self):
        """Convert to DAO, excluding the generic TableDTO id field."""
        data = self.model_dump(mode="python", exclude_unset=True, exclude_none=True, exclude={"id"})
        return self.__dao_type__.model_validate(data)
