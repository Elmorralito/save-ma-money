import { Link } from "react-router-dom";

import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import type { IngestionRunResponse, OperatingCashflowReportResponse } from "@/types/domain";

export type LivePulseSectionProps = {
  ingestionRun: IngestionRunResponse | null | undefined;
  ingestionPending: boolean;
  ingestionError: boolean;
  cashflow: OperatingCashflowReportResponse | undefined;
  cashflowPending: boolean;
  cashflowError: boolean;
  monthLabel: string;
};

function ingestionStatusBadgeClass(status: string): string {
  const normalized = status.toLowerCase();
  if (normalized === "succeeded") {
    return "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300";
  }
  if (normalized === "partial" || normalized === "running") {
    return "bg-amber-500/15 text-amber-700 dark:text-amber-300";
  }
  return "bg-destructive/15 text-destructive";
}

/**
 * Live Pulse cards: Ingestion Run Status + Monthly Operating Free Cashflow (PPT-088 / #181).
 */
export function LivePulseSection({
  ingestionRun,
  ingestionPending,
  ingestionError,
  cashflow,
  cashflowPending,
  cashflowError,
  monthLabel,
}: LivePulseSectionProps) {
  return (
    <div className="grid gap-6 sm:grid-cols-2">
      <section aria-label="Ingestion status" className="space-y-3">
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="text-sm font-semibold tracking-tight">Ingestion status</h2>
          <Link
            to="/transactions"
            className="text-xs font-medium text-primary underline-offset-4 hover:underline"
          >
            Review ledger
          </Link>
        </div>

        <div className="rounded-lg border border-border bg-card p-4 text-card-foreground">
          {ingestionPending ? (
            <p className="text-sm text-muted-foreground">Loading ingestion status…</p>
          ) : ingestionError ? (
            <p className="text-sm text-destructive">Could not load ingestion status.</p>
          ) : !ingestionRun ? (
            <div className="space-y-1">
              <p className="text-sm font-medium">No ingestion runs recorded yet</p>
              <p className="text-xs text-muted-foreground">
                Automated email and broker sync runs will appear here once scheduled.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    {ingestionRun.flow_name || ingestionRun.deployment_name || "Ingestion run"}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Started {formatDate(ingestionRun.started_at)}
                    {ingestionRun.finished_at
                      ? ` · Finished ${formatDate(ingestionRun.finished_at)}`
                      : ""}
                  </p>
                </div>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${ingestionStatusBadgeClass(ingestionRun.status)}`}
                >
                  {ingestionRun.status}
                </span>
              </div>

              <div className="grid grid-cols-4 gap-2 border-t border-border pt-3 text-xs">
                <div>
                  <p className="text-muted-foreground">Fetched</p>
                  <p className="font-semibold tabular-nums">{String(ingestionRun.fetched)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Created</p>
                  <p className="font-semibold tabular-nums">{String(ingestionRun.created)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Updated</p>
                  <p className="font-semibold tabular-nums">{String(ingestionRun.updated)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Failed</p>
                  <p
                    className={`font-semibold tabular-nums ${
                      ingestionRun.failed > 0 ? "text-destructive" : ""
                    }`}
                  >
                    {String(ingestionRun.failed)}
                  </p>
                </div>
              </div>

              {ingestionRun.error_summary ? (
                <p className="text-xs text-destructive">{ingestionRun.error_summary}</p>
              ) : null}
            </div>
          )}
        </div>
      </section>

      <section aria-label="Operating Free Cashflow" className="space-y-3">
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="text-sm font-semibold tracking-tight">
            Operating Free Cashflow ({monthLabel})
          </h2>
          <Link
            to="/reports"
            className="text-xs font-medium text-primary underline-offset-4 hover:underline"
          >
            Full waterfall
          </Link>
        </div>

        <div className="rounded-lg border border-border bg-card p-4 text-card-foreground">
          {cashflowPending ? (
            <p className="text-sm text-muted-foreground">Loading monthly cashflow…</p>
          ) : cashflowError || !cashflow ? (
            <p className="text-sm text-destructive">Could not load Operating Free Cashflow.</p>
          ) : (
            <div className="space-y-3">
              <div className="flex items-baseline justify-between gap-2">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Monthly Operating FCF ({cashflow.currency})
                  </p>
                  <p
                    className={`mt-1 text-xl font-semibold tabular-nums ${
                      cashflow.waterfall.operating_free_cashflow >= 0
                        ? "text-emerald-700 dark:text-emerald-400"
                        : "text-destructive"
                    }`}
                  >
                    {formatMoney(cashflow.waterfall.operating_free_cashflow, cashflow.currency)}
                  </p>
                </div>
                <div className="text-right text-xs text-muted-foreground tabular-nums">
                  <p>Organic margin {cashflow.waterfall.organic_fcf_margin_pct.toFixed(1)}%</p>
                  <p>Debt load {cashflow.waterfall.debt_service_to_income_pct.toFixed(1)}%</p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 border-t border-border pt-3 text-xs">
                <div>
                  <p className="text-muted-foreground">Inflows</p>
                  <p className="font-semibold tabular-nums">
                    {formatMoney(cashflow.waterfall.total_external_income, cashflow.currency)}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Outflows</p>
                  <p className="font-semibold tabular-nums">
                    {formatMoney(cashflow.waterfall.total_operating_outflows, cashflow.currency)}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">In-transit</p>
                  <p className="font-semibold tabular-nums">
                    {cashflow.in_transit
                      ? `${String(cashflow.in_transit.count)} (${formatMoney(cashflow.in_transit.total_volume, cashflow.currency)})`
                      : "0"}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
