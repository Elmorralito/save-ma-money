import { apiFetch } from "@/api/http";
import type { SpendingReportResponse } from "@/types/domain";

const REPORTS_PATH = "/api/v1/reports";

export type SpendingGroupBy = "category" | "account";

export type SpendingReportParams = {
  start_date: string;
  end_date: string;
  group_by?: SpendingGroupBy;
  account_id?: string | null;
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
