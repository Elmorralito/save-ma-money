import { Flame, ShieldCheck, Target, TrendingUp, type LucideIcon } from "lucide-react";

import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import { useLocale } from "@/i18n/LocaleProvider";
import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import { cn } from "@/lib/utils";
import type {
  DebtPaydownReportResponse,
  OperatingCashflowReportResponse,
  PlannedVsActualReportResponse,
} from "@/types/domain";

export type ReportTabId = "waterfall" | "variance" | "debt" | "spending";

type KpiSummaryStripProps = {
  currency: string;
  waterfall?: OperatingCashflowReportResponse;
  variance?: PlannedVsActualReportResponse;
  debt?: DebtPaydownReportResponse;
  activeTab?: ReportTabId;
  onSelectTab?: (tab: ReportTabId) => void;
};

type Tone = "positive" | "warning" | "negative" | "neutral";

const TONE_CARD: Record<Tone, string> = {
  positive: "border-emerald-500/30 bg-emerald-500/[0.06] hover:border-emerald-500/50",
  warning: "border-amber-500/35 bg-amber-500/[0.06] hover:border-amber-500/55",
  negative: "border-rose-500/35 bg-rose-500/[0.06] hover:border-rose-500/55",
  neutral: "border-border bg-card hover:border-primary/40",
};

const TONE_ICON_BG: Record<Tone, string> = {
  positive: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300",
  warning: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  negative: "bg-rose-500/15 text-rose-700 dark:text-rose-300",
  neutral: "bg-muted text-muted-foreground",
};

const TONE_VALUE: Record<Tone, string> = {
  positive: "text-emerald-700 dark:text-emerald-300",
  warning: "text-amber-700 dark:text-amber-300",
  negative: "text-rose-700 dark:text-rose-300",
  neutral: "text-foreground",
};

/** Interactive 4-KPI executive summary strip driven entirely by API metrics & tones. */
export function KpiSummaryStrip({
  currency,
  waterfall,
  variance,
  debt,
  activeTab,
  onSelectTab,
}: KpiSummaryStripProps) {
  const { locale, messages } = useLocale();
  const kt = messages.reports.kpi;
  const kpiAi = useScopedAIToggle();
  const waterfallCurrency = waterfall?.currency ?? currency;
  const varianceCurrency = variance?.currency ?? currency;
  const debtCurrency = debt?.currency ?? currency;
  const wfTone: Tone = waterfall?.waterfall.status_tone ?? "neutral";
  const varTone: Tone = variance?.summary.status_tone ?? "neutral";
  const dragTone: Tone =
    debt && debt.summary.active_liability_count > 0
      ? debt.summary.weighted_average_ea_pct >= 18
        ? "negative"
        : "warning"
      : "positive";
  const runwayMonths = debt?.liquidity_context.liquid_runway_months;
  const targetMonths = debt?.liquidity_context.target_liquidity_months ?? 4;
  const horizonTone: Tone =
    runwayMonths === null || runwayMonths === undefined
      ? "neutral"
      : runwayMonths >= targetMonths
        ? "positive"
        : "warning";

  return (
    <section aria-label={kt.stripLabel} className="space-y-2.5">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          {kt.stripLabel}
        </p>
        <ScopedAITrigger open={kpiAi.open} panelId={kpiAi.panelId} onToggle={kpiAi.toggle} />
      </div>

      <ScopedAIPanel
        id={kpiAi.panelId}
        open={kpiAi.open}
        onClose={kpiAi.close}
        module="reports"
        view="summary"
        control="kpi-summary-strip"
        title={kt.stripLabel}
        currency={currency}
        surfaceContext={{
          currency,
          operating_free_cashflow: waterfall?.waterfall.operating_free_cashflow ?? null,
          organic_fcf_margin_pct: waterfall?.waterfall.organic_fcf_margin_pct ?? null,
          debt_service_to_income_pct: waterfall?.waterfall.debt_service_to_income_pct ?? null,
          net_fcf_variance: variance?.summary.net_fcf_variance ?? null,
          adherence_pct: variance?.summary.adherence_pct ?? null,
          reconciliation_flag_count: variance?.summary.reconciliation_flag_count ?? null,
          monthly_interest_drag: debt?.summary.total_monthly_interest_drag ?? null,
          weighted_average_ea_pct: debt?.summary.weighted_average_ea_pct ?? null,
          highest_rate_account: debt?.summary.highest_rate_account_name ?? null,
          liquid_runway_months: runwayMonths ?? null,
        }}
        suggestedPrompts={
          locale === "es-CO"
            ? [
                "Compara estos 4 indicadores e identifica cuál requiere atención prioritaria.",
                "¿Mi reserva líquida cubre bien mi flujo y deuda actuales?",
              ]
            : [
                "Compare these 4 KPIs and highlight which metric needs priority attention.",
                "Does my liquid runway comfortably cover current cashflow and debt drag?",
              ]
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          icon={TrendingUp}
          label={kt.operatingCashflow}
          value={
            waterfall
              ? formatMoney(waterfall.waterfall.operating_free_cashflow, waterfallCurrency)
              : "—"
          }
          sublabel={
            waterfall
              ? `${kt.organicMargin} ${waterfall.waterfall.organic_fcf_margin_pct.toFixed(1)}% · ${kt.debtLoad} ${waterfall.waterfall.debt_service_to_income_pct.toFixed(1)}%`
              : kt.loadingWaterfall
          }
          tone={wfTone}
          isActive={activeTab === "waterfall"}
          onClick={onSelectTab ? () => onSelectTab("waterfall") : undefined}
        />
        <KpiCard
          icon={Target}
          label={kt.plannedVsActual}
          value={variance ? formatMoney(variance.summary.net_fcf_variance, varianceCurrency) : "—"}
          sublabel={
            variance
              ? `${kt.adherence} ${variance.summary.adherence_pct.toFixed(1)}% · ${String(variance.summary.reconciliation_flag_count)} ${kt.alertsSuffix}`
              : kt.loadingVariance
          }
          tone={varTone}
          isActive={activeTab === "variance"}
          onClick={onSelectTab ? () => onSelectTab("variance") : undefined}
        />
        <KpiCard
          icon={Flame}
          label={kt.interestDrag}
          value={debt ? formatMoney(debt.summary.total_monthly_interest_drag, debtCurrency) : "—"}
          sublabel={
            debt
              ? `${formatMoney(debt.summary.total_annual_interest_drag, debtCurrency)}${kt.perYear} · ${debt.summary.weighted_average_ea_pct.toFixed(2)}% ${kt.avgEa}`
              : kt.loadingDebtDrag
          }
          tone={debt ? dragTone : "neutral"}
          isActive={activeTab === "debt"}
          onClick={onSelectTab ? () => onSelectTab("debt") : undefined}
        />
        <KpiCard
          icon={ShieldCheck}
          label={kt.priorityPayoff}
          value={
            debt
              ? debt.summary.highest_rate_payoff_date
                ? formatDate(debt.summary.highest_rate_payoff_date)
                : debt.summary.active_liability_count === 0
                  ? kt.debtFree
                  : kt.amortAlert
              : "—"
          }
          sublabel={
            debt
              ? `${debt.summary.highest_rate_account_name ?? kt.noActiveDebt} · ${kt.runway} ${runwayMonths !== null && runwayMonths !== undefined ? `${runwayMonths.toFixed(1)} ${kt.mos}` : "N/A"}`
              : kt.loadingHorizon
          }
          tone={debt ? horizonTone : "neutral"}
          isActive={activeTab === "debt"}
          onClick={onSelectTab ? () => onSelectTab("debt") : undefined}
        />
      </div>
    </section>
  );
}

function KpiCard({
  icon: Icon,
  label,
  value,
  sublabel,
  tone,
  isActive,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  sublabel: string;
  tone: Tone;
  isActive?: boolean;
  onClick?: () => void;
}) {
  const baseClass = cn(
    "group relative flex w-full flex-col justify-between rounded-xl border p-4 text-left transition-all duration-200 ease-out",
    TONE_CARD[tone],
    onClick &&
      "cursor-pointer hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
    isActive && "ring-2 ring-primary/30",
  );

  const inner = (
    <>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <span
          className={cn(
            "inline-flex size-7 shrink-0 items-center justify-center rounded-lg transition-transform duration-200 ease-out group-hover:scale-105",
            TONE_ICON_BG[tone],
          )}
        >
          <Icon aria-hidden="true" className="size-3.5" />
        </span>
      </div>
      <p className={cn("mt-2 text-xl font-semibold tabular-nums tracking-tight", TONE_VALUE[tone])}>
        {value}
      </p>
      <p className="mt-1.5 text-xs leading-snug text-muted-foreground">{sublabel}</p>
    </>
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={baseClass}>
        {inner}
      </button>
    );
  }
  return <div className={baseClass}>{inner}</div>;
}
