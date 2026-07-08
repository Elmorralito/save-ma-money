"""Repository for account financing rows."""

from papita_txnsmodel.access.account_financing.dto import AccountFinancingDTO
from papita_txnsmodel.access.base.repository import OwnedTableRepository
from papita_txnsmodel.utils.classutils import MetaSingleton


class AccountFinancingRepository(OwnedTableRepository, metaclass=MetaSingleton):
    """Repository for account financing relationships."""

    __expected_dto__ = AccountFinancingDTO
