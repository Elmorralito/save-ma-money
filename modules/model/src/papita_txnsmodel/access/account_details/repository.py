"""Repositories for v3 account extension tables."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlmodel import Session, select

from papita_txnsmodel.access.account_details.dto import (
    AccountDetailsDTO,
    BankingAccountDetailsDTO,
    CreditCardAccountDetailsDTO,
    LoanAccountDetailsDTO,
    RealEstateAccountDetailsDTO,
    TradingAccountDetailsDTO,
)
from papita_txnsmodel.access.base.repository import BaseRepository
from papita_txnsmodel.database.connector import SQLDatabaseConnector
from papita_txnsmodel.utils.classutils import MetaSingleton

logger = logging.getLogger(__name__)


class AccountDetailsRepository(BaseRepository, metaclass=MetaSingleton):
    """Repository base for 1:1 extension tables keyed by ``account_id``."""

    __expected_dto__ = AccountDetailsDTO

    @SQLDatabaseConnector.connect
    def upsert_record(self, dto: AccountDetailsDTO, *, _db_session: Session, **kwargs) -> AccountDetailsDTO | None:
        """Insert or update an extension row using ``account_id`` as the primary key."""
        dao = dto.to_dao()
        account_id = dto.account_id
        dao_type = type(dto).__dao_type__
        existing = _db_session.exec(select(dao_type).where(dao_type.account_id == account_id)).first()

        if hasattr(dao, "updated_at"):
            setattr(dao, "updated_at", datetime.now())

        try:
            logger.debug("Upserting extension record for account_id '%s'", account_id)
            if existing is None:
                _db_session.add(dao)
            else:
                _db_session.merge(dao)
            _db_session.commit()
            _db_session.refresh(dao)
            return type(dto).model_validate(dao.model_dump(mode="python"))
        except Exception as exc:
            logger.exception("The extension upsert operation has failed due to: %s", exc)
            _db_session.rollback()

        return None


class BankingAccountDetailsRepository(AccountDetailsRepository, metaclass=MetaSingleton):
    """Repository for banking account details."""

    __expected_dto__ = BankingAccountDetailsDTO


class RealEstateAccountDetailsRepository(AccountDetailsRepository, metaclass=MetaSingleton):
    """Repository for real-estate account details."""

    __expected_dto__ = RealEstateAccountDetailsDTO


class TradingAccountDetailsRepository(AccountDetailsRepository, metaclass=MetaSingleton):
    """Repository for trading account details."""

    __expected_dto__ = TradingAccountDetailsDTO


class CreditCardAccountDetailsRepository(AccountDetailsRepository, metaclass=MetaSingleton):
    """Repository for credit card account details."""

    __expected_dto__ = CreditCardAccountDetailsDTO


class LoanAccountDetailsRepository(AccountDetailsRepository, metaclass=MetaSingleton):
    """Repository for loan account details."""

    __expected_dto__ = LoanAccountDetailsDTO
