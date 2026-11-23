import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import type {
  DebtPaydownReportResponse,
  OperatingCashflowReportResponse,
  PlannedVsActualReportResponse,
} from "@/types/domain";

type KpiSummaryStripProps = {
  currency: string;
  waterfall?: OperatingCashflowReportResponse;
  variance?: PlannedVsActualReportResponse;
  debt?: DebtPaydownReportResponse;
};

type Tone = "positive" | "warning" | "negative" | "neutral";

const TONE_CLASSES: Record<Tone, string> = {
  positive: "border-emerald-500/40 bg-emerald-500/5",
  warning: "border-amber-500/40 bg-amber-500/5",
  negative: "border-destructive/50 bg-destructive/5",
  neutral: "border-border bg-card",
};

const VALUE_TONE_CLASSES: Record<Tone, string> = {
  positive: "text-emerald-700 dark:text-emerald-400",
  warning: "text-amber-700 dark:text-amber-400",
  negative: "text-destructive",
  neutral: "text-foreground",
};

/** Top 4-KPI executive summary strip driven entirely by API metrics & tones. */
export function KpiSummaryStrip({ currency, waterfall, variance, debt }: KpiSummaryStripProps) {
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
    <section
      aria-label="Executive financial KPIs"
      className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4"
    >
      <KpiCard
        label="Operating Free Cashflow"
        value={
          waterfall
            ? formatMoney(waterfall.waterfall.operating_free_cashflow, waterfallCurrency)
            : "—"
        }
        sublabel={
          waterfall
            ? `Organic margin ${waterfall.waterfall.organic_fcf_margin_pct.toFixed(1)}% · Debt load ${waterfall.waterfall.debt_service_to_income_pct.toFixed(1)}%`
            : "Loading waterfall…"
        }
        tone={wfTone}
      />
      <KpiCard
        label="Planned vs. Actual FCF"
        value={variance ? formatMoney(variance.summary.net_fcf_variance, varianceCurrency) : "—"}
        sublabel={
          variance
            ? `Adherence ${variance.summary.adherence_pct.toFixed(1)}% · ${String(variance.summary.reconciliation_flag_count)} alert(s)`
            : "Loading variance…"
        }
        tone={varTone}
      />
      <KpiCard
        label="Monthly Interest Drag"
        value={debt ? formatMoney(debt.summary.total_monthly_interest_drag, debtCurrency) : "—"}
        sublabel={
          debt
            ? `${formatMoney(debt.summary.total_annual_interest_drag, debtCurrency)}/yr · ${debt.summary.weighted_average_ea_pct.toFixed(2)}% avg EA`
            : "Loading debt drag…"
        }
        tone={debt ? dragTone : "neutral"}
      />
      <KpiCard
        label="Priority Payoff & Runway"
        value={
          debt
            ? debt.summary.highest_rate_payoff_date
              ? formatDate(debt.summary.highest_rate_payoff_date)
              : debt.summary.active_liability_count === 0
                ? "Debt-free"
                : "Amort. alert"
            : "—"
        }
        sublabel={
          debt
            ? `${debt.summary.highest_rate_account_name ?? "No active debt"} · Runway ${runwayMonths !== null && runwayMonths !== undefined ? `${runwayMonths.toFixed(1)} mos` : "N/A"}`
            : "Loading horizon…"
        }
        tone={debt ? horizonTone : "neutral"}
      />
    </section>
  );
}

function KpiCard({
  label,
  value,
  sublabel,
  tone,
}: {
  label: string;
  value: string;
  sublabel: string;
  tone: Tone;
}) {
  return (
    <div className={`rounded-lg border p-3.5 transition-colors ${TONE_CLASSES[tone]}`}>
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <p
        className={`mt-1 text-xl font-semibold tabular-nums tracking-tight ${VALUE_TONE_CLASSES[tone]}`}
      >
        {value}
      </p>
      <p className="mt-1 text-xs text-muted-foreground">{sublabel}</p>
    </div>
  );
}
