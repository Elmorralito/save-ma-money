"""Unit tests for account extension DTOs, repositories, and services."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from sqlmodel import Session

from papita_txnsmodel.access.account_details.dto import BankingAccountDetailsDTO, CreditCardAccountDetailsDTO
from papita_txnsmodel.access.account_details.repository import CreditCardAccountDetailsRepository
from papita_txnsmodel.model.account_details import BankingAccountDetails, CreditCardAccountDetails
from papita_txnsmodel.services.account_details import CreditCardAccountDetailsService


def test_account_details_to_dao_preserves_cashflow_only() -> None:
    """Ensure CreditCardAccountDetailsDTO.to_dao preserves explicit boolean and base to_dao strips id."""
    acct_id = uuid.uuid4()
    banking = BankingAccountDetailsDTO(account_id=acct_id, entity="Bank Co")
    banking_dao = banking.to_dao()
    assert isinstance(banking_dao, BankingAccountDetails)
    assert banking_dao.entity == "Bank Co"

    cc_default = CreditCardAccountDetailsDTO(account_id=acct_id, credit_limit=5000.0)
    cc_default_dao = cc_default.to_dao()
    assert isinstance(cc_default_dao, CreditCardAccountDetails)
    assert cc_default_dao.cashflow_only is False

    cc_flagged = CreditCardAccountDetailsDTO(account_id=acct_id, credit_limit=5000.0, cashflow_only=True)
    assert cc_flagged.to_dao().cashflow_only is True


def test_credit_card_details_repository_and_service_batch_lookup() -> None:
    """Cover empty/non-empty batch lookups on AccountDetailsRepository and _AccountDetailsServiceBase."""
    repo = CreditCardAccountDetailsRepository()
    session = MagicMock(spec=Session)
    assert repo.get_by_account_ids([], _db_session=session) == []
    session.exec.assert_not_called()

    acct_id = uuid.uuid4()
    dao_row = CreditCardAccountDetails(account_id=acct_id, credit_limit=3000.0, cashflow_only=True)
    session.exec.return_value.all.return_value = [dao_row]
    rows = repo.get_by_account_ids([acct_id], _db_session=session)
    assert len(rows) == 1
    assert rows[0].account_id == acct_id
    assert rows[0].cashflow_only is True

    service = CreditCardAccountDetailsService()
    assert service.get_map_by_account_ids([]) == {}

    mock_repo = MagicMock()
    mock_repo.get_by_account_ids.return_value = rows
    service._repository = mock_repo
    result_map = service.get_map_by_account_ids([acct_id])
    assert result_map[acct_id].cashflow_only is True

    service._repository = None
    assert service.get_map_by_account_ids([acct_id]) == {}
