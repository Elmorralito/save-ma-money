import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import {
  accountsListQueryOptions,
  clientContractQueryOptions,
  debtPaydownReportQueryOptions,
  operatingCashflowReportQueryOptions,
  plannedVsActualReportQueryOptions,
  reportWindowMaxDays,
  simulateDebtPaydown,
  spendingReportQueryOptions,
} from "@/api";
import { QueryState } from "@/components/QueryState";
import { CashflowWaterfallView } from "@/components/reports/CashflowWaterfallView";
import { DebtPaydownView } from "@/components/reports/DebtPaydownView";
import { KpiSummaryStrip } from "@/components/reports/KpiSummaryStrip";
import { PlannedVsActualView } from "@/components/reports/PlannedVsActualView";
import { ReportFilters, type ReportFilterValues } from "@/components/reports/ReportFilters";
import { SpendingReportView } from "@/components/reports/SpendingReportView";
import { formatApiError } from "@/lib/formatApiError";
import { defaultReportWindowDates, validateReportWindow } from "@/lib/reportWindow";
import type { DebtPaydownSimulationRequest } from "@/types/domain";

const ACCOUNT_LIST_PARAMS = { limit: 100, skip: 0, is_active: true } as const;

type ReportTab = "waterfall" | "variance" | "debt" | "spending";

const TABS: ReadonlyArray<{ id: ReportTab; label: string }> = [
  { id: "waterfall", label: "Operating Cashflow" },
  { id: "variance", label: "Planned vs. Actual" },
  { id: "debt", label: "Debt Paydown" },
  { id: "spending", label: "Spending" },
];

function resolveTab(raw: string | null): ReportTab {
  if (raw === "variance" || raw === "debt" || raw === "spending") {
    return raw;
  }
  return "waterfall";
}

function initialFilters(): ReportFilterValues {
  const window = defaultReportWindowDates();
  return {
    startDate: window.startDate,
    endDate: window.endDate,
    accountId: "",
    currency: "",
    groupBy: "category",
  };
}

/** Executive Reports workspace (PPT-054 + PPT-091 / #184). Zero TS domain math. */
export function ReportsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = resolveTab(searchParams.get("tab"));

  const [draft, setDraft] = useState<ReportFilterValues>(initialFilters);
  const [applied, setApplied] = useState<ReportFilterValues>(initialFilters);

  const contractQuery = useQuery(clientContractQueryOptions());
  const accountsQuery = useQuery(accountsListQueryOptions(ACCOUNT_LIST_PARAMS));
  const maxDays = reportWindowMaxDays(contractQuery.data);

  const draftWindow = useMemo(
    () => validateReportWindow(draft.startDate, draft.endDate, maxDays),
    [draft.startDate, draft.endDate, maxDays],
  );
  const appliedWindow = useMemo(
    () => validateReportWindow(applied.startDate, applied.endDate, maxDays),
    [applied.startDate, applied.endDate, maxDays],
  );

  const currencyParam = applied.currency === "" ? null : applied.currency;
  const accountParam = applied.accountId === "" ? null : applied.accountId;

  const waterfallQuery = useQuery({
    ...operatingCashflowReportQueryOptions({
      start_date: applied.startDate,
      end_date: applied.endDate,
      currency: currencyParam,
      account_id: accountParam,
      include_monthly_series: true,
    }),
    enabled: appliedWindow.ok,
  });

  const varianceQuery = useQuery({
    ...plannedVsActualReportQueryOptions({
      start_date: applied.startDate,
      end_date: applied.endDate,
      currency: currencyParam,
      account_id: accountParam,
    }),
    enabled: appliedWindow.ok,
  });

  const debtQuery = useQuery(
    debtPaydownReportQueryOptions({
      currency: currencyParam,
      include_excluded: true,
    }),
  );

  const spendingQuery = useQuery({
    ...spendingReportQueryOptions({
      start_date: applied.startDate,
      end_date: applied.endDate,
      group_by: applied.groupBy,
      account_id: accountParam,
    }),
    enabled: appliedWindow.ok && activeTab === "spending",
  });

  const simulationMutation = useMutation({
    mutationFn: (request: DebtPaydownSimulationRequest) => simulateDebtPaydown(request),
  });

  const accounts = (accountsQuery.data?.items ?? []).map((account) => ({
    id: account.id,
    name: account.name,
  }));

  const availableCurrencies = useMemo(() => {
    const merged = new Set<string>();
    for (const c of waterfallQuery.data?.available_currencies ?? []) merged.add(c);
    for (const c of varianceQuery.data?.available_currencies ?? []) merged.add(c);
    for (const c of debtQuery.data?.available_currencies ?? []) merged.add(c);
    for (const acct of accountsQuery.data?.items ?? []) {
      if (acct.currency) merged.add(acct.currency);
    }
    return Array.from(merged).sort();
  }, [
    accountsQuery.data?.items,
    debtQuery.data?.available_currencies,
    varianceQuery.data?.available_currencies,
    waterfallQuery.data?.available_currencies,
  ]);

  const displayCurrency =
    waterfallQuery.data?.currency ??
    debtQuery.data?.currency ??
    varianceQuery.data?.currency ??
    (applied.currency || accountsQuery.data?.items?.[0]?.currency) ??
    "USD";

  const multiCurrencyWarning = Boolean(
    waterfallQuery.data?.multi_currency_warning ||
    varianceQuery.data?.multi_currency_warning ||
    debtQuery.data?.multi_currency_warning,
  );

  const isAnyFetching =
    waterfallQuery.isFetching ||
    varianceQuery.isFetching ||
    debtQuery.isFetching ||
    spendingQuery.isFetching;

  function selectTab(tab: ReportTab): void {
    const next = new URLSearchParams(searchParams);
    next.set("tab", tab);
    setSearchParams(next, { replace: true });
  }

  function applyFilterValues(next: ReportFilterValues): void {
    if (next.currency !== applied.currency) {
      simulationMutation.reset();
    }
    setApplied({ ...next });
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
        <p className="text-sm text-muted-foreground">
          Operating Free Cashflow, template variance, and debt paydown analytics computed by the
          API.
        </p>
      </div>

      <KpiSummaryStrip
        currency={displayCurrency}
        waterfall={waterfallQuery.data}
        variance={varianceQuery.data}
        debt={debtQuery.data}
      />

      <ReportFilters
        value={draft}
        onChange={setDraft}
        onSubmit={() => {
          if (!draftWindow.ok) {
            return;
          }
          applyFilterValues(draft);
        }}
        onApplyPreset={(next) => {
          const check = validateReportWindow(next.startDate, next.endDate, maxDays);
          if (check.ok) {
            applyFilterValues(next);
          }
        }}
        accounts={accounts}
        availableCurrencies={availableCurrencies}
        showGroupBy={activeTab === "spending"}
        maxDays={maxDays}
        windowError={draftWindow.ok ? null : draftWindow.message}
        isSubmitting={isAnyFetching}
      />

      {multiCurrencyWarning ? (
        <div
          role="status"
          className="rounded-md border border-amber-500/40 bg-amber-500/5 px-4 py-2.5 text-xs text-amber-800 dark:text-amber-300"
        >
          Multiple currencies detected ({availableCurrencies.join(", ")}). Metrics below are scoped
          exclusively to <strong>{displayCurrency}</strong>; switch Currency in Filters to inspect
          another currency.
        </div>
      ) : null}

      <div
        role="tablist"
        aria-label="Report views"
        className="flex flex-wrap gap-1 border-b border-border pb-2"
      >
        {TABS.map((tab) => {
          const selected = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              id={`tab-${tab.id}`}
              aria-selected={selected}
              aria-controls={`panel-${tab.id}`}
              onClick={() => {
                selectTab(tab.id);
              }}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                selected
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {activeTab === "waterfall" ? (
        <section
          role="tabpanel"
          id="panel-waterfall"
          aria-labelledby="tab-waterfall"
          aria-label="Operating cashflow waterfall"
          className="space-y-3"
        >
          {!appliedWindow.ok ? (
            <p className="text-sm text-muted-foreground" role="status">
              Fix the date window to load a report.
            </p>
          ) : (
            <QueryState
              isPending={waterfallQuery.isPending}
              isError={waterfallQuery.isError}
              error={waterfallQuery.error}
              isEmpty={false}
              emptyTitle="No report"
              onRetry={() => {
                void waterfallQuery.refetch();
              }}
            >
              {waterfallQuery.data ? <CashflowWaterfallView report={waterfallQuery.data} /> : null}
            </QueryState>
          )}
        </section>
      ) : null}

      {activeTab === "variance" ? (
        <section
          role="tabpanel"
          id="panel-variance"
          aria-labelledby="tab-variance"
          aria-label="Planned vs actual variance"
          className="space-y-3"
        >
          {!appliedWindow.ok ? (
            <p className="text-sm text-muted-foreground" role="status">
              Fix the date window to load a report.
            </p>
          ) : (
            <QueryState
              isPending={varianceQuery.isPending}
              isError={varianceQuery.isError}
              error={varianceQuery.error}
              isEmpty={false}
              emptyTitle="No report"
              onRetry={() => {
                void varianceQuery.refetch();
              }}
            >
              {varianceQuery.data ? <PlannedVsActualView report={varianceQuery.data} /> : null}
            </QueryState>
          )}
        </section>
      ) : null}

      {activeTab === "debt" ? (
        <section
          role="tabpanel"
          id="panel-debt"
          aria-labelledby="tab-debt"
          aria-label="Debt paydown and simulator"
          className="space-y-3"
        >
          <QueryState
            isPending={debtQuery.isPending}
            isError={debtQuery.isError}
            error={debtQuery.error}
            isEmpty={false}
            emptyTitle="No liabilities"
            onRetry={() => {
              void debtQuery.refetch();
            }}
          >
            {debtQuery.data ? (
              <DebtPaydownView
                report={debtQuery.data}
                simulation={simulationMutation.data}
                isSimulating={simulationMutation.isPending}
                simulationError={
                  simulationMutation.isError ? formatApiError(simulationMutation.error) : null
                }
                onSimulate={(request) => {
                  simulationMutation.mutate(request);
                }}
              />
            ) : null}
          </QueryState>
        </section>
      ) : null}

      {activeTab === "spending" ? (
        <section
          role="tabpanel"
          id="panel-spending"
          aria-labelledby="tab-spending"
          aria-label="Spending report"
          className="space-y-3"
        >
          <h2 className="text-sm font-semibold">Spending</h2>
          {!appliedWindow.ok ? (
            <p className="text-sm text-muted-foreground" role="status">
              Fix the date window to load a report.
            </p>
          ) : (
            <QueryState
              isPending={spendingQuery.isPending}
              isError={spendingQuery.isError}
              error={spendingQuery.error}
              isEmpty={false}
              emptyTitle="No report"
              onRetry={() => {
                void spendingQuery.refetch();
              }}
            >
              {spendingQuery.data ? (
                <SpendingReportView report={spendingQuery.data} currency={displayCurrency} />
              ) : null}
            </QueryState>
          )}
        </section>
      ) : null}
    </div>
  );
}
