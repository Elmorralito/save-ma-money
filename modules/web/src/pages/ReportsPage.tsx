import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import {
  accountsListQueryOptions,
  clientContractQueryOptions,
  reportWindowMaxDays,
  spendingReportQueryOptions,
} from "@/api";
import { ReportFilters, type ReportFilterValues } from "@/components/reports/ReportFilters";
import { SpendingReportView } from "@/components/reports/SpendingReportView";
import { QueryState } from "@/components/QueryState";
import { defaultReportWindowDates, validateReportWindow } from "@/lib/reportWindow";

const ACCOUNT_LIST_PARAMS = { limit: 100, skip: 0, is_active: true } as const;

function initialFilters(): ReportFilterValues {
  const window = defaultReportWindowDates();
  return {
    startDate: window.startDate,
    endDate: window.endDate,
    accountId: "",
    groupBy: "category",
  };
}

/** Spending report UI (PPT-054). Cash-flow / trends / export land in follow-up slices. */
export function ReportsPage() {
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

  const spendingQuery = useQuery({
    ...spendingReportQueryOptions({
      start_date: applied.startDate,
      end_date: applied.endDate,
      group_by: applied.groupBy,
      account_id: applied.accountId === "" ? null : applied.accountId,
    }),
    enabled: appliedWindow.ok,
  });

  const accounts = (accountsQuery.data?.items ?? []).map((account) => ({
    id: account.id,
    name: account.name,
  }));

  const displayCurrency = accountsQuery.data?.items?.[0]?.currency ?? "USD";

  return (
    <div className="mx-auto w-full max-w-5xl space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
        <p className="text-sm text-muted-foreground">
          Spending from the API report endpoints. Aggregations stay in the model layer.
        </p>
      </div>

      <ReportFilters
        value={draft}
        onChange={setDraft}
        onSubmit={() => {
          if (!draftWindow.ok) {
            return;
          }
          setApplied({ ...draft });
        }}
        accounts={accounts}
        maxDays={maxDays}
        windowError={draftWindow.ok ? null : draftWindow.message}
        isSubmitting={spendingQuery.isFetching}
      />

      <section aria-label="Spending report" className="space-y-3">
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
    </div>
  );
}
