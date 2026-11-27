import { apiFetch } from "@/api/http";

export type RateConvention = "CO_EA" | "US_APR" | "US_APY" | "MONTHLY_MV";
export type AmortizationMethod = "french_fixed" | "german_constant_principal";
export type InvestmentType =
  | "hysa_co"
  | "fiduciary_co"
  | "cdt_co"
  | "voluntary_pension"
  | "us_equity_etf"
  | "crypto"
  | "private_equity"
  | "real_estate_fund";

export type PortfolioAccountProjectionItem = {
  id: string;
  name: string;
  account_kind: string;
  currency: string;
  balance: number;
  group: "debt" | "credit_card" | "real_estate" | "investment";
  config: Record<string, unknown>;
};

export type PortfolioProjectionsResponse = {
  debts: PortfolioAccountProjectionItem[];
  credit_cards: PortfolioAccountProjectionItem[];
  real_estate: PortfolioAccountProjectionItem[];
  investments: PortfolioAccountProjectionItem[];
};

export type LoanAmortizationRequest = {
  principal: number;
  annual_rate_pct: number;
  rate_convention: RateConvention;
  remaining_months: number;
  monthly_insurance: number;
  extra_monthly_payment: number;
  extra_lump_sum?: number;
  lump_sum_month?: number;
  method: AmortizationMethod;
  currency: string;
};

export type LoanAmortizationRow = {
  month: number;
  payment_date: string;
  opening_balance: number;
  scheduled_payment: number;
  principal_paid: number;
  interest_paid: number;
  insurance_paid: number;
  extra_paid: number;
  total_outflow: number;
  closing_balance: number;
  cumulative_interest: number;
};

export type LoanAmortizationResponse = {
  currency: string;
  rate_convention: RateConvention;
  annual_rate_pct: number;
  monthly_rate_pct: number;
  effective_annual_rate_pct: number;
  scheduled_monthly_payment: number;
  total_monthly_outflow: number;
  payoff_months: number;
  total_interest: number;
  total_insurance: number;
  total_paid: number;
  interest_saved_vs_baseline: number;
  months_saved_vs_baseline: number;
  schedule: LoanAmortizationRow[];
};

export type CreditCardProjectionRequest = {
  balance: number;
  annual_rate_pct: number;
  rate_convention: RateConvention;
  monthly_payment: number;
  monthly_new_spend: number;
  handling_fee: number;
  pay_in_one_installment: boolean;
  currency: string;
};

export type CreditCardProjectionRow = {
  month: number;
  payment_date: string;
  opening_balance: number;
  new_spend: number;
  interest_charged: number;
  fee_charged: number;
  payment: number;
  closing_balance: number;
};

export type CreditCardProjectionResponse = {
  currency: string;
  rate_convention: RateConvention;
  monthly_rate_pct: number;
  effective_annual_rate_pct: number;
  months_to_payoff: number | null;
  total_interest: number;
  total_fees: number;
  total_paid: number;
  warning: string | null;
  schedule: CreditCardProjectionRow[];
};

export type RealEstateProjectionRequest = {
  current_value: number;
  annual_appreciation_pct: number;
  horizon_years: number;
  monthly_rent_income: number;
  occupancy_pct: number;
  annual_rent_growth_pct: number;
  monthly_hoa_and_maintenance: number;
  annual_property_tax_pct: number;
  mortgage_balance: number;
  mortgage_annual_rate_pct: number;
  mortgage_rate_convention: RateConvention;
  mortgage_remaining_months: number;
  mortgage_monthly_insurance: number;
  currency: string;
};

export type RealEstateProjectionYear = {
  year: number;
  property_value: number;
  mortgage_balance: number;
  net_equity: number;
  annual_gross_rent: number;
  annual_operating_costs: number;
  annual_mortgage_service: number;
  annual_net_cashflow: number;
  cumulative_net_cashflow: number;
};

export type RealEstateProjectionResponse = {
  currency: string;
  current_net_equity: number;
  projected_property_value: number;
  projected_mortgage_balance: number;
  projected_net_equity: number;
  cumulative_net_cashflow: number;
  gross_rental_yield_pct: number;
  cap_rate_pct: number;
  schedule: RealEstateProjectionYear[];
};

export type InvestmentProjectionRequest = {
  initial_amount: number;
  investment_type: InvestmentType;
  expected_annual_return_pct: number;
  rate_convention: RateConvention;
  horizon_years: number;
  monthly_contribution: number;
  annual_fee_pct: number;
  annual_inflation_pct: number;
  tax_on_gains_pct: number;
  annual_fx_drift_pct: number;
  currency: string;
};

export type InvestmentProjectionYear = {
  year: number;
  contributed: number;
  gross_value: number;
  cumulative_gain: number;
  real_value: number;
  after_tax_value: number;
};

export type InvestmentProjectionResponse = {
  currency: string;
  investment_type: InvestmentType;
  rate_convention: RateConvention;
  effective_net_annual_pct: number;
  total_contributed: number;
  final_gross_value: number;
  final_real_value: number;
  estimated_tax: number;
  final_after_tax_value: number;
  total_net_gain: number;
  schedule: InvestmentProjectionYear[];
};

const BASE = "/api/v1/projections";

export async function getProjectionPortfolio(
  signal?: AbortSignal,
): Promise<PortfolioProjectionsResponse> {
  const res = await apiFetch<PortfolioProjectionsResponse>(`${BASE}/portfolio`, { signal });
  return res.data;
}

export async function saveAccountProjectionConfig(
  accountId: string,
  config: Record<string, unknown>,
): Promise<void> {
  await apiFetch(`${BASE}/config/${accountId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
}

export async function computeLoanProjection(
  payload: LoanAmortizationRequest,
): Promise<LoanAmortizationResponse> {
  const res = await apiFetch<LoanAmortizationResponse>(`${BASE}/loan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.data;
}

export async function computeCreditCardProjection(
  payload: CreditCardProjectionRequest,
): Promise<CreditCardProjectionResponse> {
  const res = await apiFetch<CreditCardProjectionResponse>(`${BASE}/credit-card`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.data;
}

export async function computeRealEstateProjection(
  payload: RealEstateProjectionRequest,
): Promise<RealEstateProjectionResponse> {
  const res = await apiFetch<RealEstateProjectionResponse>(`${BASE}/real-estate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.data;
}

export async function computeInvestmentProjection(
  payload: InvestmentProjectionRequest,
): Promise<InvestmentProjectionResponse> {
  const res = await apiFetch<InvestmentProjectionResponse>(`${BASE}/investment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.data;
}
