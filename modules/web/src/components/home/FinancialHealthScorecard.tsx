import { Link } from "react-router-dom";

import { formatMoney } from "@/lib/formatMoney";
import type { FinancialHealthReportResponse } from "@/types/domain";

export type FinancialHealthScorecardProps = {
  report: FinancialHealthReportResponse | undefined;
  isPending: boolean;
  isError: boolean;
  onSelectCurrency?: (currency: string) => void;
};

/**
 * API-driven Financial Health Scorecard (PPT-088 / #181).
 *
 * Pure presentation: Net Worth, Liquid Cash Runway, Monthly Debt Service,
 * Debt-to-Asset ratio, and Margin LTV are all computed by the backend.
 */
export function FinancialHealthScorecard({
  report,
  isPending,
  isError,
  onSelectCurrency,
}: FinancialHealthScorecardProps) {
  if (isPending) {
    return (
      <section aria-label="Financial Health Scorecard" className="space-y-3">
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="text-sm font-semibold tracking-tight">Financial Health Scorecard</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {["Net Worth", "Liquid Runway", "Debt Service", "Debt / LTV"].map((label) => (
            <div
              key={label}
              className="rounded-lg border border-border bg-card p-4 text-card-foreground"
            >
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {label}
              </p>
              <p className="mt-2 text-lg font-semibold text-muted-foreground">Loading…</p>
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (isError || !report) {
    return (
      <section aria-label="Financial Health Scorecard" className="space-y-2">
        <h2 className="text-sm font-semibold tracking-tight">Financial Health Scorecard</h2>
        <div className="rounded-lg border border-border bg-card p-4 text-sm text-destructive">
          Could not load financial health scorecard.
        </div>
      </section>
    );
  }

  const { currency, scorecard, multi_currency_warning, available_currencies } = report;
  const netWorth = scorecard.reconciled_net_worth ?? 0;
  const totalAssets = scorecard.total_assets ?? 0;
  const totalLiabilities = scorecard.total_liabilities ?? 0;
  const liquidCashTotal = scorecard.liquid_cash_total ?? 0;
  const baselineBurn = scorecard.baseline_monthly_burn ?? 0;
  const monthlyDebtService = scorecard.monthly_debt_service ?? 0;
  const monthlyInterestDrag = scorecard.total_monthly_interest_drag ?? 0;
  const runway = scorecard.liquid_runway_months;
  const targetMonths = scorecard.target_liquidity_months ?? 4;
  const runwayTone =
    runway === null || runway === undefined
      ? "text-muted-foreground"
      : runway >= targetMonths
        ? "text-emerald-700 dark:text-emerald-400"
        : "text-amber-700 dark:text-amber-400";

  const netWorthTone =
    netWorth >= 0 ? "text-emerald-700 dark:text-emerald-400" : "text-destructive";

  const dtaLabel =
    scorecard.debt_to_asset_ratio_pct !== null && scorecard.debt_to_asset_ratio_pct !== undefined
      ? `${scorecard.debt_to_asset_ratio_pct.toFixed(1)}%`
      : "N/A";

  const marginLtvLabel =
    scorecard.margin_ltv_pct !== null && scorecard.margin_ltv_pct !== undefined
      ? `Margin LTV ${scorecard.margin_ltv_pct.toFixed(1)}%`
      : "No margin-linked collateral";

  return (
    <section aria-label="Financial Health Scorecard" className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold tracking-tight">Financial Health Scorecard</h2>
          <p className="text-xs text-muted-foreground">
            Active balance-included accounts ({currency})
            {multi_currency_warning && available_currencies?.length
              ? ` · Multi-currency detected (${available_currencies.join(", ")})`
              : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {available_currencies && available_currencies.length > 1 && onSelectCurrency ? (
            <div
              role="group"
              aria-label="Scorecard currency"
              className="inline-flex rounded-md border border-border bg-muted/40 p-0.5 text-xs"
            >
              {available_currencies.map((code) => {
                const active = code === currency;
                return (
                  <button
                    key={code}
                    type="button"
                    aria-pressed={active}
                    onClick={() => {
                      onSelectCurrency(code);
                    }}
                    className={`rounded px-2 py-0.5 font-medium transition-colors ${
                      active
                        ? "bg-background text-foreground shadow-xs"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {code}
                  </button>
                );
              })}
            </div>
          ) : null}
          <Link
            to="/accounts"
            className="text-xs font-medium text-primary underline-offset-4 hover:underline"
          >
            Manage accounts
          </Link>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-lg border border-border bg-card p-4 text-card-foreground">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Reconciled Net Worth
          </p>
          <p className={`mt-1 text-xl font-semibold tabular-nums ${netWorthTone}`}>
            {formatMoney(netWorth, currency)}
          </p>
          <p className="mt-1 text-xs text-muted-foreground tabular-nums">
            Assets {formatMoney(totalAssets, currency)} · Liabilities{" "}
            {formatMoney(totalLiabilities, currency)}
          </p>
        </div>

        <div className="rounded-lg border border-border bg-card p-4 text-card-foreground">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Liquid Cash Runway
          </p>
          <p className={`mt-1 text-xl font-semibold tabular-nums ${runwayTone}`}>
            {runway !== null && runway !== undefined ? `${runway.toFixed(1)} mos` : "N/A"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground tabular-nums">
            Liquid {formatMoney(liquidCashTotal, currency)} · Burn{" "}
            {formatMoney(baselineBurn, currency)}/mo
          </p>
        </div>

        <div className="rounded-lg border border-border bg-card p-4 text-card-foreground">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Monthly Debt Service
          </p>
          <p className="mt-1 text-xl font-semibold tabular-nums">
            {formatMoney(monthlyDebtService, currency)}
          </p>
          <p className="mt-1 text-xs text-muted-foreground tabular-nums">
            Interest drag {formatMoney(monthlyInterestDrag, currency)}/mo
          </p>
        </div>

        <div className="rounded-lg border border-border bg-card p-4 text-card-foreground">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Debt-to-Asset / LTV
          </p>
          <p className="mt-1 text-xl font-semibold tabular-nums">{dtaLabel}</p>
          <p className="mt-1 text-xs text-muted-foreground tabular-nums">{marginLtvLabel}</p>
        </div>
      </div>
    </section>
  );
}
