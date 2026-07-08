SCHEMA_NAME = "papita_transactions"

ACCOUNTS__TABLENAME = "accounts"
USERS__TABLENAME = "users"

CATEGORIES__TABLENAME = "categories"
TRANSACTION_TEMPLATES__TABLENAME = "transaction_templates"
TRANSACTIONS__TABLENAME = "transactions"
ACCOUNT_FINANCING__TABLENAME = "account_financing"

BANKING_ACCOUNT_DETAILS__TABLENAME = "banking_account_details"
REAL_ESTATE_ACCOUNT_DETAILS__TABLENAME = "real_estate_account_details"
TRADING_ACCOUNT_DETAILS__TABLENAME = "trading_account_details"
CREDIT_CARD_ACCOUNT_DETAILS__TABLENAME = "credit_card_account_details"
LOAN_ACCOUNT_DETAILS__TABLENAME = "loan_account_details"

ACCOUNT_BALANCES_VIEW = "account_balances"
OWNER_YEARLY_BALANCES_VIEW = "owner_yearly_balances"
OWNER_MONTHLY_BALANCES_VIEW = "owner_monthly_balances"
OWNER_QUARTERLY_BALANCES_VIEW = "owner_quarterly_balances"
OWNER_BIANNUAL_BALANCES_VIEW = "owner_biannual_balances"

EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{5,255}$"
USERNAME_REGEX = r"^[a-zA-Z0-9_]{6,255}$"
PASSWORD_REGEX = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,128}$"
