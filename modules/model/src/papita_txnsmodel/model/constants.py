SCHEMA_NAME = "papita_transactions"


def fk_id(related_tablename: str) -> str:
    """Return a schema-qualified ``table.id`` string for SQLModel/SQLAlchemy foreign keys.

    Required so Alembic and MetaData can resolve referenced tables under ``SCHEMA_NAME``.
    """
    return f"{SCHEMA_NAME}.{related_tablename}.id"


ACCOUNTS__TABLENAME = "accounts"

ACCOUNTS_INDEXER__TABLENAME = "accounts_indexer"

ASSET_ACCOUNTS__TABLENAME = "assets_accounts"

FINANCED_ASSET_ACCOUNTS__TABLENAME = "financed_asset_accounts"

BANKING_ASSET_ACCOUNTS__TABLENAME = "banking_asset_accounts"

REAL_ESTATE_ASSET_ACCOUNTS__TABLENAME = "real_estate_asset_accounts"

TRADING_ASSET_ACCOUNTS__TABLENAME = "trading_asset_accounts"

LIABILITY_ACCOUNTS__TABLENAME = "liability_accounts"

BANK_CREDIT_LIABILITY_ACCOUNTS__TABLENAME = "bank_credit_liability_accounts"

CREDIT_CARD_LIABILITY_ACCOUNTS__TABLENAME = "credit_card_liability_accounts"

TYPES_CLASSIFICATIONS__TABLENAME = "types_classifications"

TYPES__TABLENAME = "types"

IDENTIFIED_TRANSACTIONS__TABLENAME = "identified_transactions"

MARKET_ASSET_GROUPS__TABLENAME = "market_asset_groups"

MARKET_ASSETS__TABLENAME = "market_assets"

TRANSACTIONS__TABLENAME = "transactions"

USERS__TABLENAME = "users"

ROLES__TABLENAME = "roles"

USER_ROLES__TABLENAME = "user_roles"

EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}$"

USERNAME_REGEX = r"^[a-zA-Z0-9_]{6,255}$"

PASSWORD_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,128}$"
