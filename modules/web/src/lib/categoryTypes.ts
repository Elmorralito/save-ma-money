/** API ``category_type`` slugs (lowercase) for form selects. */
export const CATEGORY_TYPE_SLUGS = ["income", "expense"] as const;

export type CategoryTypeSlug = (typeof CATEGORY_TYPE_SLUGS)[number];

/** API ``cashflow_bucket`` slugs (lowercase) for Operating Cashflow waterfall assignment. */
export const CASHFLOW_BUCKET_SLUGS = [
  "income_fixed",
  "income_variable",
  "loan_payment",
  "fixed_expense",
  "variable_expense",
  "unexpected_expense",
  "savings",
  "capital_deployment",
  "non_operating_inflow",
] as const;

export type CashflowBucketSlug = (typeof CASHFLOW_BUCKET_SLUGS)[number];

export const CASHFLOW_BUCKET_LABELS: Record<CashflowBucketSlug, string> = {
  income_fixed: "Fixed income",
  income_variable: "Variable income",
  loan_payment: "Loan / debt payment",
  fixed_expense: "Fixed expense",
  variable_expense: "Variable expense",
  unexpected_expense: "Unexpected expense",
  savings: "Savings",
  capital_deployment: "Capital deployment",
  non_operating_inflow: "Non-operating inflow",
};
