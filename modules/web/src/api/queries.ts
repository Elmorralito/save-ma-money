import { queryOptions } from "@tanstack/react-query";

import { getAccount, listAccounts, type ListAccountsParams } from "@/api/accounts";
import { getCategory, listCategories, type ListCategoriesParams } from "@/api/categories";
import { getHealth, getHealthLive } from "@/api/health";
import {
  getLatestIngestionRun,
  listIngestionConnections,
  listIngestionRuns,
  type LatestIngestionRunParams,
  type ListIngestionConnectionsParams,
  type ListIngestionRunsParams,
} from "@/api/ingestion";
import { getClientContract } from "@/api/meta";
import { queryKeys } from "@/api/queryKeys";
import {
  getDebtPaydownReport,
  getFinancialHealthReport,
  getOperatingCashflowReport,
  getPlannedVsActualReport,
  getSpendingReport,
  type DebtPaydownReportParams,
  type FinancialHealthReportParams,
  type OperatingCashflowReportParams,
  type PlannedVsActualReportParams,
  type SpendingGroupBy,
  type SpendingReportParams,
} from "@/api/reports";
import { getTransaction, listTransactions, type ListTransactionsParams } from "@/api/transactions";
import {
  getTransactionTemplate,
  listTransactionTemplates,
  listUpcomingDues,
  type ListTransactionTemplatesParams,
  type ListUpcomingDuesParams,
} from "@/api/transactionTemplates";

/** Shared query definition for PPT-044 client-contract discovery. */
export function clientContractQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.meta.clientContract(),
    queryFn: ({ signal }) => getClientContract(signal).then((result) => result.contract),
  });
}

/** Shared query definition for aggregate API health. */
export function healthQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.health.root(),
    queryFn: ({ signal }) => getHealth(signal),
  });
}

/** Shared query definition for liveness (no DB/Auth/Redis). */
export function healthLiveQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.health.live(),
    queryFn: ({ signal }) => getHealthLive(signal),
  });
}

function accountsListFilters(
  params: Omit<ListAccountsParams, "signal">,
): Record<string, string | number | boolean | undefined> {
  return {
    account_kind: params.account_kind,
    ledger_side: params.ledger_side,
    is_active: params.is_active,
    skip: params.skip,
    limit: params.limit,
  };
}

function categoriesListFilters(
  params: Omit<ListCategoriesParams, "signal">,
): Record<string, string | number | boolean | undefined> {
  return {
    parent_id: params.parent_id,
    category_type: params.category_type,
    skip: params.skip,
    limit: params.limit,
  };
}

/** Shared query definition for paginated accounts list. */
export function accountsListQueryOptions(params: Omit<ListAccountsParams, "signal"> = {}) {
  return queryOptions({
    queryKey: queryKeys.accounts.list(accountsListFilters(params)),
    queryFn: ({ signal }) => listAccounts({ ...params, signal }),
  });
}

/** Shared query definition for a single account. */
export function accountDetailQueryOptions(accountId: string) {
  return queryOptions({
    queryKey: queryKeys.accounts.detail(accountId),
    queryFn: ({ signal }) => getAccount(accountId, signal),
    enabled: accountId.length > 0,
  });
}

/** Shared query definition for paginated categories list. */
export function categoriesListQueryOptions(params: Omit<ListCategoriesParams, "signal"> = {}) {
  return queryOptions({
    queryKey: queryKeys.categories.list(categoriesListFilters(params)),
    queryFn: ({ signal }) => listCategories({ ...params, signal }),
  });
}

/** Shared query definition for a single category. */
export function categoryDetailQueryOptions(categoryId: string) {
  return queryOptions({
    queryKey: queryKeys.categories.detail(categoryId),
    queryFn: ({ signal }) => getCategory(categoryId, signal),
    enabled: categoryId.length > 0,
  });
}

function transactionsListFilters(
  params: Omit<ListTransactionsParams, "signal">,
): Record<string, string | number | boolean | undefined> {
  return {
    account_id: params.account_id,
    source_account_id: params.source_account_id,
    destination_account_id: params.destination_account_id,
    category_id: params.category_id,
    transaction_type: params.transaction_type,
    exclude_transfer: params.exclude_transfer,
    status: params.status,
    settlement_status: params.settlement_status,
    start_date: params.start_date,
    end_date: params.end_date,
    min_amount: params.min_amount,
    max_amount: params.max_amount,
    search: params.search,
    skip: params.skip,
    limit: params.limit,
  };
}

function spendingReportFilters(
  params: Omit<SpendingReportParams, "signal">,
): Record<string, string | number | boolean | undefined | null> {
  return {
    start_date: params.start_date,
    end_date: params.end_date,
    group_by: params.group_by,
    account_id: params.account_id ?? null,
  };
}

/** Shared query definition for paginated transactions list. */
export function transactionsListQueryOptions(params: Omit<ListTransactionsParams, "signal"> = {}) {
  return queryOptions({
    queryKey: queryKeys.transactions.list(transactionsListFilters(params)),
    queryFn: ({ signal }) => listTransactions({ ...params, signal }),
  });
}

/** Shared query definition for a single transaction. */
export function transactionDetailQueryOptions(transactionId: string) {
  return queryOptions({
    queryKey: queryKeys.transactions.detail(transactionId),
    queryFn: ({ signal }) => getTransaction(transactionId, signal),
    enabled: transactionId.length > 0,
  });
}

/** Shared query definition for ``GET /reports/spending``. */
export function spendingReportQueryOptions(
  params: Omit<SpendingReportParams, "signal"> & { group_by?: SpendingGroupBy },
) {
  return queryOptions({
    queryKey: queryKeys.reports.spending(spendingReportFilters(params)),
    queryFn: ({ signal }) => getSpendingReport({ ...params, signal }),
  });
}

function operatingCashflowFilters(
  params: Omit<OperatingCashflowReportParams, "signal">,
): Record<string, string | number | boolean | undefined | null> {
  return {
    start_date: params.start_date,
    end_date: params.end_date,
    currency: params.currency ?? null,
    account_id: params.account_id ?? null,
    include_monthly_series: params.include_monthly_series ?? false,
  };
}

function plannedVsActualFilters(
  params: Omit<PlannedVsActualReportParams, "signal">,
): Record<string, string | number | boolean | undefined | null> {
  return {
    start_date: params.start_date,
    end_date: params.end_date,
    currency: params.currency ?? null,
    account_id: params.account_id ?? null,
    cashflow_bucket: params.cashflow_bucket ?? null,
  };
}

function debtPaydownFilters(
  params: Omit<DebtPaydownReportParams, "signal">,
): Record<string, string | number | boolean | undefined | null> {
  return {
    currency: params.currency ?? null,
    include_excluded: params.include_excluded ?? false,
    target_liquidity_months: params.target_liquidity_months ?? 4,
  };
}

/** Shared query definition for ``GET /reports/operating-cashflow``. */
export function operatingCashflowReportQueryOptions(
  params: Omit<OperatingCashflowReportParams, "signal">,
) {
  return queryOptions({
    queryKey: queryKeys.reports.operatingCashflow(operatingCashflowFilters(params)),
    queryFn: ({ signal }) => getOperatingCashflowReport({ ...params, signal }),
  });
}

/** Shared query definition for ``GET /reports/planned-vs-actual``. */
export function plannedVsActualReportQueryOptions(
  params: Omit<PlannedVsActualReportParams, "signal">,
) {
  return queryOptions({
    queryKey: queryKeys.reports.plannedVsActual(plannedVsActualFilters(params)),
    queryFn: ({ signal }) => getPlannedVsActualReport({ ...params, signal }),
  });
}

/** Shared query definition for ``GET /reports/debt-paydown``. */
export function debtPaydownReportQueryOptions(
  params: Omit<DebtPaydownReportParams, "signal"> = {},
) {
  return queryOptions({
    queryKey: queryKeys.reports.debtPaydown(debtPaydownFilters(params)),
    queryFn: ({ signal }) => getDebtPaydownReport({ ...params, signal }),
  });
}

function financialHealthFilters(
  params: Omit<FinancialHealthReportParams, "signal">,
): Record<string, string | number | boolean | undefined | null> {
  return {
    currency: params.currency ?? null,
    target_liquidity_months: params.target_liquidity_months,
  };
}

/** Shared query definition for ``GET /reports/financial-health``. */
export function financialHealthReportQueryOptions(
  params: Omit<FinancialHealthReportParams, "signal"> = {},
) {
  return queryOptions({
    queryKey: queryKeys.reports.financialHealth(financialHealthFilters(params)),
    queryFn: ({ signal }) => getFinancialHealthReport({ ...params, signal }),
  });
}

function latestIngestionRunFilters(
  params: Omit<LatestIngestionRunParams, "signal">,
): Record<string, string | number | boolean | undefined | null> {
  return {
    connection_id: params.connection_id ?? null,
  };
}

function ingestionRunsFilters(
  params: Omit<ListIngestionRunsParams, "signal">,
): Record<string, string | number | boolean | undefined | null> {
  return {
    connection_id: params.connection_id ?? null,
    skip: params.skip,
    limit: params.limit,
  };
}

function ingestionConnectionsFilters(
  params: Omit<ListIngestionConnectionsParams, "signal">,
): Record<string, string | number | boolean | undefined | null> {
  return {
    skip: params.skip,
    limit: params.limit,
  };
}

/** Shared query definition for ``GET /ingestion/runs/latest``. */
export function latestIngestionRunQueryOptions(
  params: Omit<LatestIngestionRunParams, "signal"> = {},
) {
  return queryOptions({
    queryKey: queryKeys.ingestion.latestRun(latestIngestionRunFilters(params)),
    queryFn: ({ signal }) => getLatestIngestionRun({ ...params, signal }),
  });
}

/** Shared query definition for ``GET /ingestion/runs``. */
export function ingestionRunsQueryOptions(params: Omit<ListIngestionRunsParams, "signal"> = {}) {
  return queryOptions({
    queryKey: queryKeys.ingestion.runs(ingestionRunsFilters(params)),
    queryFn: ({ signal }) => listIngestionRuns({ ...params, signal }),
  });
}

/** Shared query definition for ``GET /ingestion/connections``. */
export function ingestionConnectionsQueryOptions(
  params: Omit<ListIngestionConnectionsParams, "signal"> = {},
) {
  return queryOptions({
    queryKey: queryKeys.ingestion.connections(ingestionConnectionsFilters(params)),
    queryFn: ({ signal }) => listIngestionConnections({ ...params, signal }),
  });
}

function transactionTemplatesListFilters(
  params: Omit<ListTransactionTemplatesParams, "signal">,
): Record<string, string | number | boolean | undefined> {
  return {
    category_id: params.category_id,
    is_active: params.is_active,
    skip: params.skip,
    limit: params.limit,
  };
}

function upcomingDuesFilters(
  params: Omit<ListUpcomingDuesParams, "signal">,
): Record<string, string | number | boolean | undefined> {
  return {
    as_of: params.as_of,
    window_days: params.window_days,
    include_paid: params.include_paid,
  };
}

/** Shared query definition for paginated transaction templates (payment dues). */
export function transactionTemplatesListQueryOptions(
  params: Omit<ListTransactionTemplatesParams, "signal"> = {},
) {
  return queryOptions({
    queryKey: queryKeys.transactionTemplates.list(transactionTemplatesListFilters(params)),
    queryFn: ({ signal }) => listTransactionTemplates({ ...params, signal }),
  });
}

/** Shared query definition for a single transaction template. */
export function transactionTemplateDetailQueryOptions(templateId: string) {
  return queryOptions({
    queryKey: queryKeys.transactionTemplates.detail(templateId),
    queryFn: ({ signal }) => getTransactionTemplate(templateId, signal),
    enabled: templateId.length > 0,
  });
}

/** Shared query definition for ``GET /transaction-templates/upcoming-dues``. */
export function upcomingDuesQueryOptions(params: Omit<ListUpcomingDuesParams, "signal"> = {}) {
  return queryOptions({
    queryKey: queryKeys.transactionTemplates.upcomingDues(upcomingDuesFilters(params)),
    queryFn: ({ signal }) => listUpcomingDues({ ...params, signal }),
  });
}
