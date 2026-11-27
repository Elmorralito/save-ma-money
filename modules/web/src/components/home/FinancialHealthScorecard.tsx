import { CreditCard, Scale, ShieldCheck, Wallet } from "lucide-react";
import { Link } from "react-router-dom";

import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import { useLocale, useMessages } from "@/i18n/LocaleProvider";
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
  const { locale } = useLocale();
  const m = useMessages().dashboard;
  const scorecardAi = useScopedAIToggle();
  if (isPending) {
    return (
      <section aria-label={m.scorecardTitle} className="space-y-3">
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="text-sm font-semibold tracking-tight">{m.scorecardTitle}</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[m.netWorth, m.runway, m.debtService, m.dtaLtv].map((label) => (
            <div
              key={label}
              className="rounded-xl border border-border bg-card p-5 text-card-foreground"
            >
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                {label}
              </p>
              <div
                aria-hidden="true"
                className="mt-2.5 h-7 w-28 animate-pulse rounded-md bg-muted"
              />
              <div
                aria-hidden="true"
                className="mt-2 h-3.5 w-36 animate-pulse rounded bg-muted/70"
              />
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
        <div
          role="alert"
          className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"
        >
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
        ? "text-success"
        : "text-warning";

  const netWorthTone = netWorth >= 0 ? "text-success" : "text-destructive";

  const dtaLabel =
    scorecard.debt_to_asset_ratio_pct !== null && scorecard.debt_to_asset_ratio_pct !== undefined
      ? `${scorecard.debt_to_asset_ratio_pct.toFixed(1)}%`
      : "N/A";

  const marginLtvLabel =
    scorecard.margin_ltv_pct !== null && scorecard.margin_ltv_pct !== undefined
      ? `Margin LTV ${scorecard.margin_ltv_pct.toFixed(1)}%`
      : m.noMarginCollateral;

  const runwayPct =
    runway !== null && runway !== undefined && targetMonths > 0
      ? Math.min(100, Math.max(6, Math.round((runway / targetMonths) * 100)))
      : null;

  return (
    <section aria-label={m.scorecardTitle} className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold tracking-tight">{m.scorecardTitle}</h2>
          <p className="text-xs text-muted-foreground">
            {m.scorecardActiveAccounts} ({currency})
            {multi_currency_warning && available_currencies?.length
              ? ` · ${available_currencies.join(", ")}`
              : ""}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {available_currencies && available_currencies.length > 1 && onSelectCurrency ? (
            <div
              role="group"
              aria-label="Scorecard currency"
              className="inline-flex rounded-lg border border-border bg-card p-0.5 text-xs shadow-xs"
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
                    className={`rounded-md px-2.5 py-0.5 font-medium transition-colors ${
                      active
                        ? "bg-primary text-primary-foreground shadow-xs"
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
            {m.manageAccounts}
          </Link>
          <ScopedAITrigger
            open={scorecardAi.open}
            panelId={scorecardAi.panelId}
            onToggle={scorecardAi.toggle}
          />
        </div>
      </div>

      <ScopedAIPanel
        id={scorecardAi.panelId}
        open={scorecardAi.open}
        onClose={scorecardAi.close}
        module="dashboard"
        view="scorecard"
        control="financial-health-scorecard"
        title={m.scorecardTitle}
        currency={currency}
        surfaceContext={{
          currency,
          net_worth: netWorth,
          total_assets: totalAssets,
          total_liabilities: totalLiabilities,
          liquid_cash_total: liquidCashTotal,
          baseline_monthly_burn: baselineBurn,
          liquid_runway_months: runway,
          target_liquidity_months: targetMonths,
          monthly_debt_service: monthlyDebtService,
          monthly_interest_drag: monthlyInterestDrag,
          debt_to_asset_ratio_pct: scorecard.debt_to_asset_ratio_pct,
          margin_ltv_pct: scorecard.margin_ltv_pct,
        }}
        suggestedPrompts={
          locale === "es-CO"
            ? [
                "¿Qué debo priorizar en mi balance y reserva líquida?",
                "¿Cómo impacta el servicio de deuda a mi liquidez actual?",
                "Resume mis activos vs. pasivos en términos prácticos.",
              ]
            : [
                "What should I prioritize first across net worth and runway?",
                "How healthy is my debt service relative to liquid reserves?",
                "Summarize my asset vs. liability position concisely.",
              ]
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div
          className={`rounded-xl border bg-card p-5 text-card-foreground ${netWorth >= 0 ? "border-border" : "border-destructive/30"}`}
        >
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {m.netWorth}
            </p>
            <span
              className={`flex size-8 shrink-0 items-center justify-center rounded-lg ${
                netWorth >= 0
                  ? "bg-success-soft text-success"
                  : "bg-destructive/12 text-destructive"
              }`}
            >
              <Wallet aria-hidden="true" className="size-4" />
            </span>
          </div>
          <p className={`mt-2 text-2xl font-semibold tracking-tight tabular-nums ${netWorthTone}`}>
            {formatMoney(netWorth, currency)}
          </p>
          <p className="mt-1.5 text-xs text-muted-foreground tabular-nums">
            {m.assets} {formatMoney(totalAssets, currency)} · {m.liabilities}{" "}
            {formatMoney(totalLiabilities, currency)}
          </p>
        </div>

        <div
          className={`rounded-xl border bg-card p-5 text-card-foreground ${
            runway !== null && runway !== undefined && runway >= targetMonths
              ? "border-border"
              : "border-warning/30"
          }`}
        >
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {m.runway}
            </p>
            <span
              className={`flex size-8 shrink-0 items-center justify-center rounded-lg ${
                runway !== null && runway !== undefined && runway >= targetMonths
                  ? "bg-info-soft text-info"
                  : "bg-warning-soft text-warning"
              }`}
            >
              <ShieldCheck aria-hidden="true" className="size-4" />
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between gap-2">
            <p className={`text-2xl font-semibold tracking-tight tabular-nums ${runwayTone}`}>
              {runway !== null && runway !== undefined ? `${runway.toFixed(1)} mos` : "N/A"}
            </p>
            {runway !== null && runway !== undefined ? (
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  runway >= targetMonths
                    ? "bg-success-soft text-success"
                    : "bg-warning-soft text-warning"
                }`}
              >
                {runway >= targetMonths ? m.onTarget : `${m.target} ${String(targetMonths)}m`}
              </span>
            ) : null}
          </div>
          {runwayPct !== null ? (
            <div
              aria-hidden="true"
              className="mt-2.5 h-1.5 w-full overflow-hidden rounded-full bg-muted"
            >
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  runway !== null && runway !== undefined && runway >= targetMonths
                    ? "bg-success"
                    : "bg-warning"
                }`}
                style={{ width: `${String(runwayPct)}%` }}
              />
            </div>
          ) : null}
          <p className="mt-1.5 text-xs text-muted-foreground tabular-nums">
            {m.liquid} {formatMoney(liquidCashTotal, currency)} · {m.burn}{" "}
            {formatMoney(baselineBurn, currency)}/mo
          </p>
        </div>

        <div
          className={`rounded-xl border bg-card p-5 text-card-foreground ${monthlyDebtService > 0 ? "border-warning/25" : "border-border"}`}
        >
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {m.debtService}
            </p>
            <span
              className={`flex size-8 shrink-0 items-center justify-center rounded-lg ${
                monthlyDebtService > 0
                  ? "bg-warning-soft text-warning"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              <CreditCard aria-hidden="true" className="size-4" />
            </span>
          </div>
          <p className="mt-2 text-2xl font-semibold tracking-tight tabular-nums">
            {formatMoney(monthlyDebtService, currency)}
          </p>
          <p className="mt-1.5 text-xs text-muted-foreground tabular-nums">
            {m.interestDrag} {formatMoney(monthlyInterestDrag, currency)}/mo
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5 text-card-foreground">
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              {m.dtaLtv}
            </p>
            <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Scale aria-hidden="true" className="size-4" />
            </span>
          </div>
          <p className="mt-2 text-2xl font-semibold tracking-tight tabular-nums">{dtaLabel}</p>
          <p className="mt-1.5 text-xs text-muted-foreground tabular-nums">{marginLtvLabel}</p>
        </div>
      </div>
    </section>
  );
}
