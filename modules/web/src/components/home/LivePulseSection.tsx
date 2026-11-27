import { Activity, TrendingDown, TrendingUp } from "lucide-react";
import { Link } from "react-router-dom";

import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import { useLocale, useMessages } from "@/i18n/LocaleProvider";
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
    return "bg-success-soft text-success";
  }
  if (normalized === "partial" || normalized === "running") {
    return "bg-warning-soft text-warning";
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
  const { locale } = useLocale();
  const m = useMessages().dashboard;
  const ingestionAi = useScopedAIToggle();
  const cashflowAi = useScopedAIToggle();
  const fcfPositive = (cashflow?.waterfall.operating_free_cashflow ?? 0) >= 0;
  const totalFlow =
    (cashflow?.waterfall.total_external_income ?? 0) +
    (cashflow?.waterfall.total_operating_outflows ?? 0);
  const inflowSharePct =
    totalFlow > 0
      ? Math.min(
          100,
          Math.max(
            4,
            Math.round(((cashflow?.waterfall.total_external_income ?? 0) / totalFlow) * 100),
          ),
        )
      : null;

  return (
    <div className="grid gap-6 sm:grid-cols-2">
      <section aria-label={m.ingestionStatus} className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="flex size-7 items-center justify-center rounded-lg bg-info-soft text-info">
              <Activity aria-hidden="true" className="size-3.5" />
            </span>
            <h2 className="text-sm font-semibold tracking-tight">{m.ingestionStatus}</h2>
          </div>
          <div className="flex items-center gap-2">
            <ScopedAITrigger
              open={ingestionAi.open}
              panelId={ingestionAi.panelId}
              onToggle={ingestionAi.toggle}
            />
            <Link
              to="/transactions"
              className="text-xs font-medium text-primary underline-offset-4 hover:underline"
            >
              {m.reviewLedger}
            </Link>
          </div>
        </div>

        <ScopedAIPanel
          id={ingestionAi.panelId}
          open={ingestionAi.open}
          onClose={ingestionAi.close}
          module="dashboard"
          view="live-pulse"
          control="ingestion-status-card"
          title={m.ingestionStatus}
          surfaceContext={
            ingestionRun
              ? {
                  status: ingestionRun.status,
                  flow_name: ingestionRun.flow_name,
                  fetched: ingestionRun.fetched,
                  created: ingestionRun.created,
                  updated: ingestionRun.updated,
                  failed: ingestionRun.failed,
                  error_summary: ingestionRun.error_summary,
                }
              : { status: "no_runs" }
          }
          suggestedPrompts={
            locale === "es-CO"
              ? [
                  "Resume el estado de la última sincronización.",
                  "¿Hubo errores o movimientos fallidos que deba revisar?",
                ]
              : [
                  "Summarize the latest ingestion sync run.",
                  "Are there any failed items or sync issues I should inspect?",
                ]
          }
        />

        <div className="rounded-xl border border-border bg-card p-5 text-card-foreground">
          {ingestionPending ? (
            <div className="space-y-3" aria-label="Loading ingestion status">
              <div className="flex items-center justify-between gap-2">
                <div className="h-4 w-40 animate-pulse rounded bg-muted" />
                <div className="h-5 w-16 animate-pulse rounded-full bg-muted" />
              </div>
              <div className="grid grid-cols-4 gap-2 border-t border-border pt-3">
                {[0, 1, 2, 3].map((idx) => (
                  <div key={idx} className="space-y-1.5">
                    <div className="h-3 w-12 animate-pulse rounded bg-muted/70" />
                    <div className="h-4 w-8 animate-pulse rounded bg-muted" />
                  </div>
                ))}
              </div>
            </div>
          ) : ingestionError ? (
            <p role="alert" className="text-sm text-destructive">
              Could not load ingestion status.
            </p>
          ) : !ingestionRun ? (
            <div className="space-y-1.5">
              <p className="text-sm font-medium">{m.noIngestionRuns}</p>
              <p className="text-xs leading-relaxed text-muted-foreground">{m.noIngestionHint}</p>
            </div>
          ) : (
            <div className="space-y-3.5">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">
                    {ingestionRun.flow_name || ingestionRun.deployment_name || m.ingestionStatus}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {m.started} {formatDate(ingestionRun.started_at)}
                    {ingestionRun.finished_at
                      ? ` · ${m.finished} ${formatDate(ingestionRun.finished_at)}`
                      : ""}
                  </p>
                </div>
                <span
                  className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${ingestionStatusBadgeClass(ingestionRun.status)}`}
                >
                  <span aria-hidden="true" className="size-1.5 rounded-full bg-current" />
                  {ingestionRun.status}
                </span>
              </div>

              <div className="grid grid-cols-4 divide-x divide-border border-t border-border pt-3 text-xs">
                <div className="pr-2">
                  <p className="text-xs text-muted-foreground">{m.fetched}</p>
                  <p className="mt-0.5 font-semibold tabular-nums">
                    {String(ingestionRun.fetched)}
                  </p>
                </div>
                <div className="px-2.5">
                  <p className="text-xs text-muted-foreground">{m.created}</p>
                  <p className="mt-0.5 font-semibold tabular-nums text-success">
                    {String(ingestionRun.created)}
                  </p>
                </div>
                <div className="px-2.5">
                  <p className="text-xs text-muted-foreground">{m.updated}</p>
                  <p className="mt-0.5 font-semibold tabular-nums text-info">
                    {String(ingestionRun.updated)}
                  </p>
                </div>
                <div className="pl-2.5">
                  <p className="text-xs text-muted-foreground">{m.failed}</p>
                  <p
                    className={`mt-0.5 font-semibold tabular-nums ${ingestionRun.failed > 0 ? "text-destructive" : ""}`}
                  >
                    {String(ingestionRun.failed)}
                  </p>
                </div>
              </div>

              {ingestionRun.error_summary ? (
                <p className="break-words rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
                  {ingestionRun.error_summary}
                </p>
              ) : null}
            </div>
          )}
        </div>
      </section>

      <section aria-label="Operating Free Cashflow" className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span
              className={`flex size-7 items-center justify-center rounded-lg ${
                fcfPositive ? "bg-success-soft text-success" : "bg-destructive/12 text-destructive"
              }`}
            >
              {fcfPositive ? (
                <TrendingUp aria-hidden="true" className="size-3.5" />
              ) : (
                <TrendingDown aria-hidden="true" className="size-3.5" />
              )}
            </span>
            <h2 className="text-sm font-semibold tracking-tight">
              {m.operatingFcf} ({monthLabel})
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to="/reports"
              className="text-xs font-medium text-primary underline-offset-4 hover:underline"
            >
              {m.fullWaterfall}
            </Link>
            {cashflow ? (
              <ScopedAITrigger
                open={cashflowAi.open}
                panelId={cashflowAi.panelId}
                onToggle={cashflowAi.toggle}
              />
            ) : null}
          </div>
        </div>

        {cashflow ? (
          <ScopedAIPanel
            id={cashflowAi.panelId}
            open={cashflowAi.open}
            onClose={cashflowAi.close}
            module="dashboard"
            view="live-pulse"
            control="operating-fcf-card"
            title={`${m.operatingFcf} (${monthLabel})`}
            currency={cashflow.currency}
            surfaceContext={{
              month_label: monthLabel,
              currency: cashflow.currency,
              operating_free_cashflow: cashflow.waterfall.operating_free_cashflow,
              total_external_income: cashflow.waterfall.total_external_income,
              total_operating_outflows: cashflow.waterfall.total_operating_outflows,
              organic_fcf_margin_pct: cashflow.waterfall.organic_fcf_margin_pct,
              debt_service_to_income_pct: cashflow.waterfall.debt_service_to_income_pct,
              in_transit_volume: cashflow.in_transit?.total_volume ?? 0,
            }}
            suggestedPrompts={
              locale === "es-CO"
                ? [
                    `Explica mi flujo operativo libre de ${monthLabel}.`,
                    "¿Qué está presionando más mi margen orgánico este mes?",
                  ]
                : [
                    `Explain my ${monthLabel} Operating Free Cashflow.`,
                    "What is putting the most pressure on my organic margin this month?",
                  ]
            }
          />
        ) : null}

        <div
          className={`rounded-xl border bg-card p-5 text-card-foreground ${fcfPositive ? "border-border" : "border-destructive/30"}`}
        >
          {cashflowPending ? (
            <div className="space-y-3" aria-label="Loading monthly cashflow">
              <div className="h-3.5 w-36 animate-pulse rounded bg-muted/70" />
              <div className="h-7 w-32 animate-pulse rounded bg-muted" />
              <div className="grid grid-cols-3 gap-2 border-t border-border pt-3">
                {[0, 1, 2].map((idx) => (
                  <div key={idx} className="space-y-1.5">
                    <div className="h-3 w-14 animate-pulse rounded bg-muted/70" />
                    <div className="h-4 w-20 animate-pulse rounded bg-muted" />
                  </div>
                ))}
              </div>
            </div>
          ) : cashflowError || !cashflow ? (
            <p role="alert" className="text-sm text-destructive">
              Could not load Operating Free Cashflow.
            </p>
          ) : (
            <div className="space-y-3.5">
              <div className="flex items-baseline justify-between gap-2">
                <div>
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {m.monthlyOperatingFcf} ({cashflow.currency})
                  </p>
                  <p
                    className={`mt-1 text-2xl font-semibold tracking-tight tabular-nums ${
                      fcfPositive ? "text-success" : "text-destructive"
                    }`}
                  >
                    {formatMoney(cashflow.waterfall.operating_free_cashflow, cashflow.currency)}
                  </p>
                </div>
                <div className="text-right text-xs text-muted-foreground tabular-nums">
                  <p>
                    {m.organicMargin} {cashflow.waterfall.organic_fcf_margin_pct.toFixed(1)}%
                  </p>
                  <p>
                    {m.debtLoad} {cashflow.waterfall.debt_service_to_income_pct.toFixed(1)}%
                  </p>
                </div>
              </div>

              {inflowSharePct !== null ? (
                <div
                  aria-hidden="true"
                  className="flex h-2 w-full overflow-hidden rounded-full bg-warning/30"
                >
                  <div
                    className="h-full bg-success transition-all duration-500"
                    style={{ width: `${String(inflowSharePct)}%` }}
                  />
                </div>
              ) : null}

              <div className="grid grid-cols-3 gap-2 border-t border-border pt-3 text-xs">
                <div>
                  <p className="text-muted-foreground">{m.inflows}</p>
                  <p className="mt-0.5 font-semibold tabular-nums text-success">
                    {formatMoney(cashflow.waterfall.total_external_income, cashflow.currency)}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">{m.outflows}</p>
                  <p className="mt-0.5 font-semibold tabular-nums text-warning">
                    {formatMoney(cashflow.waterfall.total_operating_outflows, cashflow.currency)}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">{m.inTransit}</p>
                  <p className="mt-0.5 font-semibold tabular-nums">
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
