import { apiFetch } from "@/api/http";
import type {
  DebtPaydownReportResponse,
  DebtPaydownSimulationRequest,
  DebtPaydownSimulationResponse,
  FinancialHealthReportResponse,
  OperatingCashflowReportResponse,
  PlannedVsActualReportResponse,
  SpendingReportResponse,
} from "@/types/domain";

const REPORTS_PATH = "/api/v1/reports";

export type SpendingGroupBy = "category" | "account";

export type SpendingReportParams = {
  start_date: string;
  end_date: string;
  group_by?: SpendingGroupBy;
  account_id?: string | null;
  signal?: AbortSignal;
};

export type OperatingCashflowReportParams = {
  start_date: string;
  end_date: string;
  currency?: string | null;
  account_id?: string | null;
  include_monthly_series?: boolean;
  signal?: AbortSignal;
};

export type PlannedVsActualReportParams = {
  start_date: string;
  end_date: string;
  currency?: string | null;
  account_id?: string | null;
  cashflow_bucket?: string | null;
  signal?: AbortSignal;
};

export type DebtPaydownReportParams = {
  currency?: string | null;
  include_excluded?: boolean;
  target_liquidity_months?: number;
  signal?: AbortSignal;
};

export type FinancialHealthReportParams = {
  currency?: string | null;
  target_liquidity_months?: number;
  signal?: AbortSignal;
};

function buildQuery(params: Record<string, string | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, value);
    }
  }
  const qs = search.toString();
  return qs === "" ? "" : `?${qs}`;
}

/** ``GET /api/v1/reports/spending`` — tenant spending/income totals + breakdown. */
export async function getSpendingReport(
  params: SpendingReportParams,
): Promise<SpendingReportResponse> {
  const { signal, start_date, end_date, group_by, account_id } = params;
  const path = `${REPORTS_PATH}/spending${buildQuery({
    start_date,
    end_date,
    group_by,
    account_id: account_id ?? undefined,
  })}`;
  const result = await apiFetch<SpendingReportResponse>(path, { signal });
  return result.data;
}

/** ``GET /api/v1/reports/operating-cashflow`` — Operating Free Cashflow waterfall. */
export async function getOperatingCashflowReport(
  params: OperatingCashflowReportParams,
): Promise<OperatingCashflowReportResponse> {
  const { signal, start_date, end_date, currency, account_id, include_monthly_series } = params;
  const path = `${REPORTS_PATH}/operating-cashflow${buildQuery({
    start_date,
    end_date,
    currency: currency ?? undefined,
    account_id: account_id ?? undefined,
    include_monthly_series: include_monthly_series ? "true" : undefined,
  })}`;
  const result = await apiFetch<OperatingCashflowReportResponse>(path, { signal });
  return result.data;
}

/** ``GET /api/v1/reports/planned-vs-actual`` — template variance and reconciliation alerts. */
export async function getPlannedVsActualReport(
  params: PlannedVsActualReportParams,
): Promise<PlannedVsActualReportResponse> {
  const { signal, start_date, end_date, currency, account_id, cashflow_bucket } = params;
  const path = `${REPORTS_PATH}/planned-vs-actual${buildQuery({
    start_date,
    end_date,
    currency: currency ?? undefined,
    account_id: account_id ?? undefined,
    cashflow_bucket: cashflow_bucket ?? undefined,
  })}`;
  const result = await apiFetch<PlannedVsActualReportResponse>(path, { signal });
  return result.data;
}

/** ``GET /api/v1/reports/debt-paydown`` — active liabilities ranked by EA & interest drag. */
export async function getDebtPaydownReport(
  params: DebtPaydownReportParams = {},
): Promise<DebtPaydownReportResponse> {
  const { signal, currency, include_excluded, target_liquidity_months } = params;
  const path = `${REPORTS_PATH}/debt-paydown${buildQuery({
    currency: currency ?? undefined,
    include_excluded: include_excluded ? "true" : undefined,
    target_liquidity_months:
      target_liquidity_months !== undefined ? String(target_liquidity_months) : undefined,
  })}`;
  const result = await apiFetch<DebtPaydownReportResponse>(path, { signal });
  return result.data;
}

/** ``POST /api/v1/reports/debt-paydown/simulate`` — backend prepayment simulation. */
export async function simulateDebtPaydown(
  body: DebtPaydownSimulationRequest,
): Promise<DebtPaydownSimulationResponse> {
  const result = await apiFetch<DebtPaydownSimulationResponse>(
    `${REPORTS_PATH}/debt-paydown/simulate`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
  );
  return result.data;
}

/** ``GET /api/v1/reports/financial-health`` — API-computed Financial Health Scorecard. */
export async function getFinancialHealthReport(
  params: FinancialHealthReportParams = {},
): Promise<FinancialHealthReportResponse> {
  const { signal, currency, target_liquidity_months } = params;
  const path = `${REPORTS_PATH}/financial-health${buildQuery({
    currency: currency ?? undefined,
    target_liquidity_months:
      target_liquidity_months !== undefined ? String(target_liquidity_months) : undefined,
  })}`;
  const result = await apiFetch<FinancialHealthReportResponse>(path, { signal });
  return result.data;
}
