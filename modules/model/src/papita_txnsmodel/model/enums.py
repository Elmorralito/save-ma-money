"""Enumeration types for the Papita Transactions v3 schema."""

from enum import Enum


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
