"""Service for account financing relationships."""

from papita_txnsmodel.access.account_financing.dto import AccountFinancingDTO
from papita_txnsmodel.access.account_financing.repository import AccountFinancingRepository
from papita_txnsmodel.services.base import BaseService


class AccountFinancingService(BaseService):
    """Service for managing asset–loan financing links."""

    dto_type: type[AccountFinancingDTO] = AccountFinancingDTO
    repository_type: type[AccountFinancingRepository] = AccountFinancingRepository
