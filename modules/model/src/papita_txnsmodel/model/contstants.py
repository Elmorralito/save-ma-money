SCHEMA_NAME = "papita_transactions"

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

TRANSACTIONS__TABLENAME = "transactions"

USERS__TABLENAME = "users"

EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{5,255}$"

USERNAME_REGEX = r"^[a-zA-Z0-9_]{6,255}$"

PASSWORD_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,128}$"
