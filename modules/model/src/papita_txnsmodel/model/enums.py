"""Enumeration types for the Papita Transactions v3 schema."""

from __future__ import annotations

from enum import Enum


class ProviderType(str, Enum):
    """Signup / identity channel for ``users.provider_type``.

    ``EMAIL`` is password (or magic-link) registration. ``GOOGLE`` and ``GITHUB``
    are Supabase Auth OAuth providers; values match Supabase provider ids.
    """

    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"

    @classmethod
    def oauth_members(cls) -> frozenset[ProviderType]:
        """Providers that complete via Supabase OAuth / ``POST /auth/sso``."""
        return frozenset({cls.GOOGLE, cls.GITHUB})

    def is_oauth(self) -> bool:
        """Return whether this provider uses the OAuth/SSO path."""
        return self in self.oauth_members()


class AccountKind(str, Enum):
    """Discriminator for consolidated account rows."""

    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    CASH = "CASH"
    INVESTMENT_BROKERAGE = "INVESTMENT_BROKERAGE"
    REAL_ESTATE = "REAL_ESTATE"
    CREDIT_CARD = "CREDIT_CARD"
    LOAN_MORTGAGE = "LOAN_MORTGAGE"
    OTHER_ASSET = "OTHER_ASSET"
    OTHER_LIABILITY = "OTHER_LIABILITY"


class LedgerSide(str, Enum):
    """Balance sheet side for an account."""

    ASSET = "ASSET"
    LIABILITY = "LIABILITY"


class InterestRateBasis(str, Enum):
    """Canonical interest rate representation."""

    NOMINAL_MONTHLY = "NOMINAL_MONTHLY"
    APY = "APY"


class CategoryKind(str, Enum):
    """Income vs expense taxonomy for categories."""

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"


class TransactionKind(str, Enum):
    """Ledger transaction semantics."""

    INCOME = "INCOME"
    EXPENSE = "EXPENSE"
    TRANSFER = "TRANSFER"


class TransactionStatus(str, Enum):
    """Posting status for transactions."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class RealEstateOwnership(str, Enum):
    """Real estate ownership mode."""

    FULL = "FULL"
    PARTIAL = "PARTIAL"


class RealEstateAreaUnit(str, Enum):
    """Area measurement units for real estate accounts."""

    SQ_MT = "SQ_MT"
    SQ_FT = "SQ_FT"
    AC = "AC"
    HA = "HA"
    BLK = "BLK"
