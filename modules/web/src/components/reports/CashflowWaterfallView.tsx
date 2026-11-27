import { ArrowUpRight, ChevronDown, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import {
  SortableTableHead,
  sortItems,
  toggleSort,
  type SortState,
} from "@/components/table/SortableTableHead";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useLocale } from "@/i18n/LocaleProvider";
import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import { formatSlugLabel } from "@/lib/formatSlugLabel";
import { cn } from "@/lib/utils";
import type { OperatingCashflowReportResponse, WaterfallBucketItem } from "@/types/domain";

type CashflowWaterfallViewProps = {
  report: OperatingCashflowReportResponse;
};

type StepRow = {
  key: string;
  label: string;
  amount: number;
  tone: "income" | "outflow" | "result" | "allocation";
  bucketMatch?: string;
};

type TrendSortKey = "month" | "income" | "outflows" | "fcf" | "margin" | "nonOp";
type FcfFilter = "all" | "positive" | "negative";
type BucketSortKey = "bucket" | "group" | "transactions" | "share" | "amount";

const GROUP_BADGE: Record<string, string> = {
  income: "bg-emerald-500/12 text-emerald-700 dark:text-emerald-300",
  operating_outflow: "bg-rose-500/12 text-rose-700 dark:text-rose-300",
  outflow: "bg-rose-500/12 text-rose-700 dark:text-rose-300",
  allocation: "bg-indigo-500/12 text-indigo-700 dark:text-indigo-300",
  non_operating: "bg-amber-500/12 text-amber-800 dark:text-amber-300",
};

/** Interactive Operating Free Cashflow waterfall & monthly trend view (zero TS domain math). */
export function CashflowWaterfallView({ report }: CashflowWaterfallViewProps) {
  const { locale, messages } = useLocale();
  const wt = messages.reports.waterfall;
  const chartAi = useScopedAIToggle();
  const trendAi = useScopedAIToggle();
  const bucketsAi = useScopedAIToggle();
  const reconciliationAi = useScopedAIToggle();
  const diagnosticsAi = useScopedAIToggle();
  const [expandedBucket, setExpandedBucket] = useState<string | null>(null);
  const [activeStepKey, setActiveStepKey] = useState<string | null>(null);
  const [hoveredMonth, setHoveredMonth] = useState<string | null>(null);
  const [monthSearch, setMonthSearch] = useState("");
  const [fcfFilter, setFcfFilter] = useState<FcfFilter>("all");
  const [trendSort, setTrendSort] = useState<SortState<TrendSortKey>>({
    key: "month",
    direction: "asc",
  });
  const [bucketSearch, setBucketSearch] = useState("");
  const [groupFilter, setGroupFilter] = useState("all");
  const [bucketSort, setBucketSort] = useState<SortState<BucketSortKey>>(null);

  const { waterfall, currency } = report;
  const buckets = useMemo(() => report.buckets ?? [], [report.buckets]);
  const in_transit = report.in_transit ?? { count: 0, inflows: 0, outflows: 0, total_volume: 0 };
  const monthly_series = useMemo(() => report.monthly_series ?? [], [report.monthly_series]);
  const diagnostics = report.diagnostics ?? {
    unbucketed_category_count: 0,
    unbucketed_amount: 0,
    cashflow_only_cc_excluded_count: 0,
    cashflow_only_cc_excluded_amount: 0,
    cashflow_only_cc_account_names: [],
  };
  const ccFlaggedNames = diagnostics.cashflow_only_cc_account_names ?? [];

  const steps: StepRow[] = [
    {
      key: "income",
      label: wt.steps.income,
      amount: waterfall.total_external_income,
      tone: "income",
      bucketMatch: "income",
    },
    {
      key: "loans",
      label: wt.steps.loans,
      amount: waterfall.loans,
      tone: "outflow",
      bucketMatch: "loan",
    },
    {
      key: "fixed",
      label: wt.steps.fixed,
      amount: waterfall.fixed_expenses,
      tone: "outflow",
      bucketMatch: "fixed",
    },
    {
      key: "variable",
      label: wt.steps.variable,
      amount: waterfall.variable_expenses,
      tone: "outflow",
      bucketMatch: "variable",
    },
    {
      key: "unexpected",
      label: wt.steps.unexpected,
      amount: waterfall.unexpected_expenses,
      tone: "outflow",
      bucketMatch: "unexpected",
    },
    {
      key: "fcf",
      label: wt.steps.fcf,
      amount: waterfall.operating_free_cashflow,
      tone: "result",
    },
    {
      key: "savings",
      label: wt.steps.savings,
      amount: waterfall.savings,
      tone: "allocation",
      bucketMatch: "saving",
    },
    {
      key: "capital",
      label: wt.steps.capital,
      amount: waterfall.capital_deployments,
      tone: "allocation",
      bucketMatch: "capital",
    },
  ];

  const maxStepMag = Math.max(1, ...steps.map((step) => Math.abs(step.amount)));
  const selectedStep = steps.find((s) => s.key === activeStepKey) ?? null;
  const maxMonthVal = Math.max(
    1,
    ...monthly_series.map((m) =>
      Math.max(Math.abs(m.total_external_income), Math.abs(m.total_operating_outflows)),
    ),
  );
  const activeMonthRow =
    monthly_series.find((m) => m.month === hoveredMonth) ??
    monthly_series[monthly_series.length - 1] ??
    null;

  const visibleMonthlyRows = useMemo(() => {
    const q = monthSearch.trim().toLowerCase();
    const filtered = monthly_series.filter((row) => {
      if (fcfFilter === "positive" && row.operating_free_cashflow < 0) return false;
      if (fcfFilter === "negative" && row.operating_free_cashflow >= 0) return false;
      if (q && !row.month.toLowerCase().includes(q)) return false;
      return true;
    });
    return sortItems(filtered, trendSort, {
      month: (r) => r.month,
      income: (r) => r.total_external_income,
      outflows: (r) => r.total_operating_outflows,
      fcf: (r) => r.operating_free_cashflow,
      margin: (r) => r.organic_fcf_margin_pct,
      nonOp: (r) => r.non_operating_inflows,
    });
  }, [fcfFilter, monthSearch, monthly_series, trendSort]);

  const bucketGroupKeys = useMemo(() => {
    const seen = new Set<string>();
    for (const item of buckets) {
      seen.add(item.group.toLowerCase());
    }
    return Array.from(seen);
  }, [buckets]);

  const visibleBuckets = useMemo(() => {
    const q = bucketSearch.trim().toLowerCase();
    const filtered = buckets.filter((item) => {
      const gKey = item.group.toLowerCase();
      if (groupFilter !== "all" && gKey !== groupFilter) return false;
      if (!q) return true;
      const bLabel = (wt.bucketLabels[item.bucket.toUpperCase()] ?? item.label).toLowerCase();
      const gLabel = (wt.bucketGroups[gKey] ?? formatSlugLabel(item.group)).toLowerCase();
      const catMatch = (item.top_categories ?? []).some((c) =>
        c.category_name.toLowerCase().includes(q),
      );
      return (
        bLabel.includes(q) || item.label.toLowerCase().includes(q) || gLabel.includes(q) || catMatch
      );
    });
    return sortItems(filtered, bucketSort, {
      bucket: (r) => wt.bucketLabels[r.bucket.toUpperCase()] ?? r.label,
      group: (r) => wt.bucketGroups[r.group.toLowerCase()] ?? formatSlugLabel(r.group),
      transactions: (r) => r.transaction_count,
      share: (r) => r.share_of_income_pct,
      amount: (r) => r.amount,
    });
  }, [bucketSearch, bucketSort, buckets, groupFilter, wt.bucketGroups, wt.bucketLabels]);

  function handleStepSelect(step: StepRow) {
    setActiveStepKey((prev) => (prev === step.key ? null : step.key));
    if (step.bucketMatch) {
      const match = buckets.find((b) => b.bucket.toLowerCase().includes(step.bucketMatch!));
      if (match) setExpandedBucket(match.bucket);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span>
          {wt.period} {formatDate(report.period.start_date)} → {formatDate(report.period.end_date)}{" "}
          · {wt.currency} <strong className="text-foreground">{currency}</strong>
        </span>
        <div className="flex flex-wrap items-center gap-3">
          <span>
            {wt.organicMargin}:{" "}
            <strong
              className={cn(
                "tabular-nums",
                waterfall.organic_fcf_margin_pct >= 20
                  ? "text-emerald-700 dark:text-emerald-300"
                  : waterfall.organic_fcf_margin_pct >= 0
                    ? "text-amber-700 dark:text-amber-300"
                    : "text-rose-700 dark:text-rose-300",
              )}
            >
              {waterfall.organic_fcf_margin_pct.toFixed(1)}%
            </strong>
          </span>
          <span>
            {wt.debtRatio}:{" "}
            <strong
              className={cn(
                "tabular-nums",
                waterfall.debt_service_to_income_pct <= 25
                  ? "text-emerald-700 dark:text-emerald-300"
                  : waterfall.debt_service_to_income_pct <= 40
                    ? "text-amber-700 dark:text-amber-300"
                    : "text-rose-700 dark:text-rose-300",
              )}
            >
              {waterfall.debt_service_to_income_pct.toFixed(1)}%
            </strong>
          </span>
        </div>
      </div>

      {/* Interactive SVG Horizontal Waterfall Chart */}
      <div className="rounded-2xl border border-border bg-card p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold">{wt.chartTitle}</h3>
            <p className="mt-0.5 text-xs text-muted-foreground text-pretty">{wt.chartHint}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
            <span className="inline-flex items-center gap-1.5">
              <span className="size-2.5 rounded-full bg-emerald-500" /> {wt.legendIncome}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="size-2.5 rounded-full bg-rose-500" /> {wt.legendOutflow}
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="size-2.5 rounded-full bg-indigo-500" /> {wt.legendAllocation}
            </span>
            <ScopedAITrigger
              open={chartAi.open}
              panelId={chartAi.panelId}
              onToggle={chartAi.toggle}
            />
          </div>
        </div>

        <ScopedAIPanel
          id={chartAi.panelId}
          open={chartAi.open}
          onClose={chartAi.close}
          module="reports"
          view="waterfall"
          control="waterfall-chart"
          title={wt.chartTitle}
          currency={currency}
          className="mt-3"
          surfaceContext={{
            currency,
            period: report.period,
            organic_fcf_margin_pct: waterfall.organic_fcf_margin_pct,
            debt_service_to_income_pct: waterfall.debt_service_to_income_pct,
            selected_step: selectedStep
              ? { key: selectedStep.key, amount: selectedStep.amount }
              : null,
            steps: steps.map((s) => ({ key: s.key, label: s.label, amount: s.amount })),
          }}
          suggestedPrompts={
            locale === "es-CO"
              ? [
                  "¿Qué peldaño explica mejor mi flujo operativo libre actual?",
                  "¿Qué categoría debo ajustar primero para pasar a FCF positivo?",
                ]
              : [
                  "Which step explains my current Operating FCF most directly?",
                  "Where is the clearest lever to strengthen positive free cashflow?",
                ]
          }
        />

        <div className="mt-4 space-y-2">
          {steps.map((step) => {
            const pct = Math.max(1.5, Math.min(100, (Math.abs(step.amount) / maxStepMag) * 100));
            const shareOfIncome =
              waterfall.total_external_income > 0
                ? (Math.abs(step.amount) / waterfall.total_external_income) * 100
                : null;
            const isSelected = activeStepKey === step.key;
            const barColor =
              step.tone === "income"
                ? "bg-emerald-500"
                : step.tone === "outflow"
                  ? "bg-rose-500"
                  : step.tone === "result"
                    ? waterfall.operating_free_cashflow >= 0
                      ? "bg-emerald-600"
                      : "bg-rose-600"
                    : "bg-indigo-500";
            return (
              <button
                key={step.key}
                type="button"
                onClick={() => handleStepSelect(step)}
                className={cn(
                  "group grid w-full grid-cols-[9.5rem_1fr_auto] items-center gap-3 rounded-lg px-2.5 py-1.5 text-left transition-colors duration-150",
                  isSelected ? "bg-primary/10 ring-1 ring-primary/30" : "hover:bg-muted/60",
                )}
              >
                <span
                  className={cn(
                    "truncate text-xs",
                    step.tone === "result"
                      ? "font-semibold text-foreground"
                      : "text-muted-foreground group-hover:text-foreground",
                  )}
                >
                  {step.label}
                </span>
                <div className="h-5 w-full overflow-hidden rounded-md bg-muted/60">
                  <div
                    className={cn(
                      "h-full rounded-md transition-all duration-500 ease-out group-hover:brightness-110",
                      barColor,
                    )}
                    style={{ width: `${pct.toFixed(1)}%` }}
                  />
                </div>
                <span className="flex items-center gap-2 text-right">
                  <span className="min-w-[6.5rem] font-mono text-xs font-medium tabular-nums text-foreground">
                    {formatMoney(step.amount, currency)}
                  </span>
                  {shareOfIncome !== null ? (
                    <span className="hidden w-12 text-right text-[11px] tabular-nums text-muted-foreground sm:inline-block">
                      {shareOfIncome.toFixed(0)}%
                    </span>
                  ) : null}
                </span>
              </button>
            );
          })}
        </div>

        {selectedStep ? (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-border bg-muted/35 px-3.5 py-2 text-xs">
            <span>
              {wt.selectedPrefix} <strong>{selectedStep.label}</strong> —{" "}
              <strong className="tabular-nums">{formatMoney(selectedStep.amount, currency)}</strong>
              {waterfall.total_external_income > 0
                ? ` (${((Math.abs(selectedStep.amount) / waterfall.total_external_income) * 100).toFixed(1)}% ${wt.ofExternalIncome})`
                : ""}
            </span>
            <button
              type="button"
              onClick={() => setActiveStepKey(null)}
              className="text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
            >
              {wt.clearSelection}
            </button>
          </div>
        ) : null}
      </div>

      {/* Interactive Monthly Cashflow Trend Bar Chart + Table */}
      {monthly_series.length > 0 ? (
        <div className="rounded-2xl border border-border bg-card">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
            <div>
              <h3 className="text-sm font-semibold">{wt.trendTitle}</h3>
              <p className="text-xs text-muted-foreground">{wt.trendHint}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {activeMonthRow ? (
                <div className="flex flex-wrap items-center gap-3 rounded-lg bg-muted/50 px-3 py-1.5 text-xs">
                  <span className="font-semibold text-foreground">{activeMonthRow.month}</span>
                  <span className="text-emerald-700 tabular-nums dark:text-emerald-300">
                    {wt.inShort} {formatMoney(activeMonthRow.total_external_income, currency)}
                  </span>
                  <span className="text-rose-700 tabular-nums dark:text-rose-300">
                    {wt.outShort} {formatMoney(activeMonthRow.total_operating_outflows, currency)}
                  </span>
                  <span className="font-medium tabular-nums text-foreground">
                    {wt.fcfShort} {formatMoney(activeMonthRow.operating_free_cashflow, currency)} (
                    {activeMonthRow.organic_fcf_margin_pct.toFixed(1)}%)
                  </span>
                </div>
              ) : null}
              <ScopedAITrigger
                open={trendAi.open}
                panelId={trendAi.panelId}
                onToggle={trendAi.toggle}
              />
            </div>
          </div>

          <ScopedAIPanel
            id={trendAi.panelId}
            open={trendAi.open}
            onClose={trendAi.close}
            module="reports"
            view="waterfall"
            control="monthly-trend-table"
            title={wt.trendTitle}
            currency={currency}
            className="mx-4 mt-3"
            surfaceContext={{
              currency,
              fcf_filter: fcfFilter,
              month_search: monthSearch || null,
              sort: trendSort,
              focused_month: activeMonthRow?.month ?? null,
              rows: visibleMonthlyRows.slice(0, 12),
            }}
            suggestedPrompts={
              locale === "es-CO"
                ? [
                    "Explica la tendencia mensual y el mes con menor margen FCF.",
                    "¿Qué meses muestran picos atípicos de ingreso o gasto operativo?",
                  ]
                : [
                    "Explain the monthly cashflow trend and the weakest FCF month.",
                    "Which months show abnormal spikes in income or operating outflows?",
                  ]
            }
          />

          <div className="flex items-end gap-2 overflow-x-auto px-4 pt-5 pb-3">
            {monthly_series.map((m) => {
              const inH = Math.max(
                4,
                Math.round((Math.abs(m.total_external_income) / maxMonthVal) * 96),
              );
              const outH = Math.max(
                4,
                Math.round((Math.abs(m.total_operating_outflows) / maxMonthVal) * 96),
              );
              const isFocused = activeMonthRow?.month === m.month;
              return (
                <button
                  key={m.month}
                  type="button"
                  onMouseEnter={() => setHoveredMonth(m.month)}
                  onFocus={() => setHoveredMonth(m.month)}
                  onClick={() => setHoveredMonth(m.month)}
                  className={cn(
                    "flex min-w-[3.5rem] flex-1 flex-col items-center gap-1.5 rounded-lg px-1.5 py-2 transition-colors",
                    isFocused ? "bg-primary/10" : "hover:bg-muted/50",
                  )}
                >
                  <div className="flex h-24 items-end gap-1">
                    <div
                      className="w-3 rounded-t bg-emerald-500/85 transition-all duration-300 ease-out"
                      style={{ height: `${inH}px` }}
                    />
                    <div
                      className="w-3 rounded-t bg-rose-500/80 transition-all duration-300 ease-out"
                      style={{ height: `${outH}px` }}
                    />
                  </div>
                  <span className="text-[11px] font-medium text-muted-foreground">{m.month}</span>
                </button>
              );
            })}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 border-y border-border px-4 py-2.5">
            <Input
              aria-label={wt.filterMonthsPlaceholder}
              placeholder={wt.filterMonthsPlaceholder}
              className="h-8 w-44 text-xs"
              value={monthSearch}
              onChange={(event) => {
                setMonthSearch(event.target.value);
              }}
            />
            <div className="flex flex-wrap gap-1.5" role="group" aria-label={wt.trendTitle}>
              {(
                [
                  ["all", wt.filterFcfAll],
                  ["positive", wt.filterFcfPositive],
                  ["negative", wt.filterFcfNegative],
                ] as const
              ).map(([key, label]) => (
                <Button
                  key={key}
                  type="button"
                  size="sm"
                  variant={fcfFilter === key ? "default" : "outline"}
                  aria-pressed={fcfFilter === key}
                  onClick={() => {
                    setFcfFilter(key);
                  }}
                >
                  {label}
                </Button>
              ))}
            </div>
          </div>

          {visibleMonthlyRows.length === 0 ? (
            <div className="px-4 py-6 text-center text-xs text-muted-foreground">
              {wt.noMatchingMonths}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <SortableTableHead
                    label={wt.colMonth}
                    sortKey="month"
                    sort={trendSort}
                    onSort={(key) => {
                      setTrendSort((prev) => toggleSort(prev, key, "asc"));
                    }}
                  />
                  <SortableTableHead
                    label={wt.colExternalIncome}
                    sortKey="income"
                    sort={trendSort}
                    onSort={(key) => {
                      setTrendSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                    align="right"
                  />
                  <SortableTableHead
                    label={wt.colOperatingOutflows}
                    sortKey="outflows"
                    sort={trendSort}
                    onSort={(key) => {
                      setTrendSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                    align="right"
                  />
                  <SortableTableHead
                    label={wt.colOperatingFcf}
                    sortKey="fcf"
                    sort={trendSort}
                    onSort={(key) => {
                      setTrendSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                    align="right"
                  />
                  <SortableTableHead
                    label={wt.colMargin}
                    sortKey="margin"
                    sort={trendSort}
                    onSort={(key) => {
                      setTrendSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                    align="right"
                  />
                  <SortableTableHead
                    label={wt.colNonOpInflows}
                    sortKey="nonOp"
                    sort={trendSort}
                    onSort={(key) => {
                      setTrendSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                    align="right"
                  />
                </TableRow>
              </TableHeader>
              <TableBody>
                {visibleMonthlyRows.map((row) => (
                  <TableRow
                    key={row.month}
                    onMouseEnter={() => setHoveredMonth(row.month)}
                    className={cn(activeMonthRow?.month === row.month && "bg-muted/40")}
                  >
                    <TableCell className="font-medium">{row.month}</TableCell>
                    <TableCell className="text-right tabular-nums text-emerald-700 dark:text-emerald-300">
                      {formatMoney(row.total_external_income, currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-rose-700 dark:text-rose-300">
                      {formatMoney(row.total_operating_outflows, currency)}
                    </TableCell>
                    <TableCell className="text-right font-semibold tabular-nums">
                      {formatMoney(row.operating_free_cashflow, currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">
                      {row.organic_fcf_margin_pct.toFixed(1)}%
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">
                      {formatMoney(row.non_operating_inflows, currency)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      ) : null}

      {/* Detailed Bucket Breakdown */}
      <div className="rounded-2xl border border-border bg-card">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
          <div>
            <h3 className="text-sm font-semibold">{wt.bucketTitle}</h3>
            <p className="mt-0.5 text-xs text-muted-foreground">{wt.bucketSubtitle}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Input
              aria-label={wt.filterBucketsPlaceholder}
              placeholder={wt.filterBucketsPlaceholder}
              className="h-8 w-48 text-xs"
              value={bucketSearch}
              onChange={(event) => {
                setBucketSearch(event.target.value);
              }}
            />
            {bucketGroupKeys.length > 1 ? (
              <div className="flex flex-wrap gap-1.5" role="group" aria-label={wt.colGroup}>
                <Button
                  type="button"
                  size="sm"
                  variant={groupFilter === "all" ? "default" : "outline"}
                  aria-pressed={groupFilter === "all"}
                  onClick={() => {
                    setGroupFilter("all");
                  }}
                >
                  {wt.filterAllGroups}
                </Button>
                {bucketGroupKeys.map((gKey) => (
                  <Button
                    key={gKey}
                    type="button"
                    size="sm"
                    variant={groupFilter === gKey ? "default" : "outline"}
                    aria-pressed={groupFilter === gKey}
                    onClick={() => {
                      setGroupFilter(gKey);
                    }}
                  >
                    {wt.bucketGroups[gKey] ?? formatSlugLabel(gKey)}
                  </Button>
                ))}
              </div>
            ) : null}
            <ScopedAITrigger
              open={bucketsAi.open}
              panelId={bucketsAi.panelId}
              onToggle={bucketsAi.toggle}
            />
          </div>
        </div>
        <ScopedAIPanel
          id={bucketsAi.panelId}
          open={bucketsAi.open}
          onClose={bucketsAi.close}
          module="reports"
          view="waterfall"
          control="bucket-breakdown-table"
          title={wt.bucketTitle}
          currency={currency}
          className="m-4"
          surfaceContext={{
            currency,
            group_filter: groupFilter,
            search: bucketSearch || null,
            sort: bucketSort,
            expanded_bucket: expandedBucket,
            rows: visibleBuckets.map((b) => ({
              bucket: b.bucket,
              label: wt.bucketLabels[b.bucket.toUpperCase()] ?? b.label,
              group: b.group,
              amount: b.amount,
              share_of_income_pct: b.share_of_income_pct,
              transaction_count: b.transaction_count,
              top_categories: (b.top_categories ?? []).slice(0, 4),
            })),
          }}
          suggestedPrompts={
            locale === "es-CO"
              ? [
                  "¿Qué bloque representa mayor salida de efectivo?",
                  "¿Qué subcategorías explican el bloque más alto?",
                ]
              : [
                  "Which bucket drives the largest share of cash outflow?",
                  "Summarize the top categories inside my filtered buckets.",
                ]
          }
        />
        {visibleBuckets.length === 0 ? (
          <div className="px-4 py-6 text-center text-xs text-muted-foreground">
            {wt.noMatchingBuckets}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <SortableTableHead
                  label={wt.colBucket}
                  sortKey="bucket"
                  sort={bucketSort}
                  onSort={(key) => {
                    setBucketSort((prev) => toggleSort(prev, key, "asc"));
                  }}
                />
                <SortableTableHead
                  label={wt.colGroup}
                  sortKey="group"
                  sort={bucketSort}
                  onSort={(key) => {
                    setBucketSort((prev) => toggleSort(prev, key, "asc"));
                  }}
                />
                <SortableTableHead
                  label={wt.colTransactions}
                  sortKey="transactions"
                  sort={bucketSort}
                  onSort={(key) => {
                    setBucketSort((prev) => toggleSort(prev, key, "desc"));
                  }}
                  align="right"
                />
                <SortableTableHead
                  label={wt.colShareOfIncome}
                  sortKey="share"
                  sort={bucketSort}
                  onSort={(key) => {
                    setBucketSort((prev) => toggleSort(prev, key, "desc"));
                  }}
                  align="right"
                />
                <SortableTableHead
                  label={wt.colAmount}
                  sortKey="amount"
                  sort={bucketSort}
                  onSort={(key) => {
                    setBucketSort((prev) => toggleSort(prev, key, "desc"));
                  }}
                  align="right"
                />
                <TableHead className="text-right">{wt.colCategories}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {visibleBuckets.map((item) => (
                <BucketTableRow
                  key={item.bucket}
                  item={item}
                  currency={currency}
                  expanded={expandedBucket === item.bucket}
                  hideLabel={wt.hide}
                  topLabel={wt.top}
                  bucketLabels={wt.bucketLabels}
                  bucketGroups={wt.bucketGroups}
                  onToggle={() => {
                    setExpandedBucket((prev) => (prev === item.bucket ? null : item.bucket));
                  }}
                />
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Visually Separated Non-Operating & Hygiene Cards */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-dashed border-border bg-muted/25 p-4 text-sm">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h3 className="font-semibold">{wt.reconciliationTitle}</h3>
              <p className="mt-0.5 text-xs text-muted-foreground">{wt.reconciliationHint}</p>
            </div>
            <ScopedAITrigger
              open={reconciliationAi.open}
              panelId={reconciliationAi.panelId}
              onToggle={reconciliationAi.toggle}
            />
          </div>
          <ScopedAIPanel
            id={reconciliationAi.panelId}
            open={reconciliationAi.open}
            onClose={reconciliationAi.close}
            module="reports"
            view="waterfall"
            control="reconciliation-card"
            title={wt.reconciliationTitle}
            currency={currency}
            className="mt-3"
            surfaceContext={{
              currency,
              non_operating_inflows: waterfall.non_operating_inflows,
              internal_sweeps_volume: waterfall.internal_sweeps_volume,
              net_allocated_surplus: waterfall.net_allocated_surplus,
              net_ledger_cashflow: waterfall.net_ledger_cashflow,
            }}
            suggestedPrompts={
              locale === "es-CO"
                ? [
                    "Explica cómo difiere el flujo neto contable del FCF operativo.",
                    "¿Qué representan las entradas no operativas y traslados internos aquí?",
                  ]
                : [
                    "Explain how net ledger cashflow reconciles against Operating FCF.",
                    "What are the non-operating inflows and internal sweeps showing?",
                  ]
            }
          />
          <dl className="mt-3 space-y-1.5 text-xs">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">{wt.nonOpInflowsLabel}</dt>
              <dd className="font-medium tabular-nums">
                {formatMoney(waterfall.non_operating_inflows, currency)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">{wt.sweepsVolumeLabel}</dt>
              <dd className="font-medium tabular-nums">
                {formatMoney(waterfall.internal_sweeps_volume, currency)}
              </dd>
            </div>
            <div className="flex justify-between border-t border-border pt-1.5">
              <dt className="text-muted-foreground">{wt.netAllocatedSurplusLabel}</dt>
              <dd className="font-medium tabular-nums">
                {formatMoney(waterfall.net_allocated_surplus, currency)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="font-medium">{wt.netLedgerCashflowLabel}</dt>
              <dd className="font-semibold tabular-nums">
                {formatMoney(waterfall.net_ledger_cashflow, currency)}
              </dd>
            </div>
          </dl>
        </div>

        <div className="rounded-2xl border border-border bg-card p-4 text-sm">
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-semibold">{wt.diagnosticsTitle}</h3>
            <ScopedAITrigger
              open={diagnosticsAi.open}
              panelId={diagnosticsAi.panelId}
              onToggle={diagnosticsAi.toggle}
            />
          </div>
          <ScopedAIPanel
            id={diagnosticsAi.panelId}
            open={diagnosticsAi.open}
            onClose={diagnosticsAi.close}
            module="reports"
            view="waterfall"
            control="diagnostics-card"
            title={wt.diagnosticsTitle}
            currency={currency}
            className="mt-3"
            surfaceContext={{
              currency,
              in_transit: in_transit,
              diagnostics,
            }}
            suggestedPrompts={
              locale === "es-CO"
                ? [
                    "¿Tengo categorías sin bloque o movimientos por reclasificar?",
                    "Explica por qué se excluyeron estas transferencias y cargos de tarjeta.",
                  ]
                : [
                    "Do I have unbucketed categories or classification gaps to fix?",
                    "Explain why these in-transit or credit-card items were excluded.",
                  ]
            }
          />
          <dl className="mt-3 space-y-1.5 text-xs">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">{wt.inTransitExcludedLabel}</dt>
              <dd className="font-medium tabular-nums">
                {String(in_transit.count)} ({formatMoney(in_transit.total_volume, currency)})
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">{wt.unbucketedFallbackLabel}</dt>
              <dd className="font-medium tabular-nums">
                {String(diagnostics.unbucketed_category_count)} (
                {formatMoney(diagnostics.unbucketed_amount, currency)})
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">{wt.ccExcludedLabel}</dt>
              <dd className="font-medium tabular-nums">
                {String(diagnostics.cashflow_only_cc_excluded_count)} (
                {formatMoney(diagnostics.cashflow_only_cc_excluded_amount, currency)})
              </dd>
            </div>
          </dl>
          {ccFlaggedNames.length > 0 ? (
            <p className="mt-2 text-xs text-muted-foreground">
              {wt.cardsFlaggedPrefix} {ccFlaggedNames.join(", ")}
            </p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function BucketTableRow({
  item,
  currency,
  expanded,
  hideLabel,
  topLabel,
  bucketLabels,
  bucketGroups,
  onToggle,
}: {
  item: WaterfallBucketItem;
  currency: string;
  expanded: boolean;
  hideLabel: string;
  topLabel: string;
  bucketLabels?: Record<string, string>;
  bucketGroups?: Record<string, string>;
  onToggle: () => void;
}) {
  const hasCategories = (item.top_categories?.length ?? 0) > 0;
  const groupKey = item.group.toLowerCase();
  const groupBadge = GROUP_BADGE[groupKey] ?? "bg-muted text-muted-foreground";
  const bucketLabel = bucketLabels?.[item.bucket.toUpperCase()] ?? item.label;
  const groupLabel = bucketGroups?.[groupKey] ?? formatSlugLabel(item.group);
  return (
    <>
      <TableRow className={cn(expanded && "bg-muted/35")}>
        <TableCell className="font-medium">{bucketLabel}</TableCell>
        <TableCell>
          <span
            className={cn("inline-flex rounded-md px-2 py-0.5 text-[11px] font-medium", groupBadge)}
          >
            {groupLabel}
          </span>
        </TableCell>
        <TableCell className="text-right tabular-nums text-muted-foreground">
          {String(item.transaction_count)}
        </TableCell>
        <TableCell className="text-right tabular-nums text-muted-foreground">
          {item.share_of_income_pct.toFixed(1)}%
        </TableCell>
        <TableCell className="text-right font-medium tabular-nums">
          {formatMoney(item.amount, currency)}
        </TableCell>
        <TableCell className="text-right">
          {hasCategories ? (
            <Button
              type="button"
              size="sm"
              variant="ghost"
              aria-expanded={expanded}
              aria-label={`${expanded ? hideLabel : topLabel} ${bucketLabel}`}
              onClick={onToggle}
              className="gap-1"
            >
              {expanded ? (
                <ChevronDown className="size-3.5" />
              ) : (
                <ChevronRight className="size-3.5" />
              )}
              {expanded ? hideLabel : topLabel}
            </Button>
          ) : (
            <span className="text-xs text-muted-foreground">—</span>
          )}
        </TableCell>
      </TableRow>
      {expanded && hasCategories ? (
        <TableRow className="bg-muted/25">
          <TableCell colSpan={6} className="py-2.5">
            <div className="flex flex-wrap gap-2 text-xs">
              {(item.top_categories ?? []).map((cat, idx) => (
                <Link
                  key={`${cat.category_id ?? cat.category_name}-${String(idx)}`}
                  to={`/transactions?search=${encodeURIComponent(cat.category_name)}`}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 py-1 transition-colors hover:border-primary/40 hover:bg-primary/5"
                >
                  <span>{cat.category_name}</span>
                  <strong className="tabular-nums">{formatMoney(cat.amount, currency)}</strong>
                  <span className="text-muted-foreground">({String(cat.transaction_count)})</span>
                  <ArrowUpRight className="size-3 text-muted-foreground" />
                </Link>
              ))}
            </div>
          </TableCell>
        </TableRow>
      ) : null}
    </>
  );
}
