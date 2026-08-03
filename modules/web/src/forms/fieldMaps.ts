/** OpenAPI AccountCreate/Update body paths → AccountFormState keys. */
export const ACCOUNT_SERVER_FIELD_MAP: Record<string, string> = {
  name: "name",
  description: "description",
  account_kind: "account_kind",
  ledger_side: "ledger_side",
  currency: "currency",
  initial_value: "initial_value",
  is_active: "is_active",
  "banking_details.entity": "banking_entity",
  "banking_details.account_number": "banking_account_number",
  "trading_details.buy_value": "trading_buy_value",
  "trading_details.units": "trading_units",
  "credit_card_details.credit_limit": "credit_limit",
  "loan_details.is_paid_off": "loan_is_paid_off",
  "loan_details.insurance_payment": "loan_insurance_payment",
  "loan_details.extras_payment": "loan_extras_payment",
  "real_estate_details.address": "re_address",
  "real_estate_details.city": "re_city",
  "real_estate_details.country": "re_country",
  "real_estate_details.total_area": "re_total_area",
  "real_estate_details.built_area": "re_built_area",
  "real_estate_details.area_unit": "re_area_unit",
  "real_estate_details.ownership": "re_ownership",
  "real_estate_details.participation": "re_participation",
};

/** OpenAPI CategoryCreate/Update body paths → CategoryFormState keys. */
export const CATEGORY_SERVER_FIELD_MAP: Record<string, string> = {
  name: "name",
  description: "description",
  category_type: "category_type",
  parent_id: "parent_id",
  icon: "icon",
  color: "color",
  is_active: "is_active",
};
