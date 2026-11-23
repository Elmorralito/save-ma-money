import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import { formatSlugLabel } from "@/lib/formatSlugLabel";
import type { OperatingCashflowReportResponse, WaterfallBucketItem } from "@/types/domain";

type CashflowWaterfallViewProps = {
  report: OperatingCashflowReportResponse;
};

type StepRow = {
  key: string;
  label: string;
  amount: number;
  tone: "income" | "outflow" | "result" | "allocation";
};

/** Presentation-only Operating Free Cashflow waterfall view (zero TS domain math). */
export function CashflowWaterfallView({ report }: CashflowWaterfallViewProps) {
  const [expandedBucket, setExpandedBucket] = useState<string | null>(null);
  const { waterfall, currency } = report;
  const buckets = report.buckets ?? [];
  const in_transit = report.in_transit ?? { count: 0, inflows: 0, outflows: 0, total_volume: 0 };
  const monthly_series = report.monthly_series ?? [];
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
      label: "External Income",
      amount: waterfall.total_external_income,
      tone: "income",
    },
    { key: "loans", label: "− Loans & Debt", amount: waterfall.loans, tone: "outflow" },
    { key: "fixed", label: "− Fixed Expenses", amount: waterfall.fixed_expenses, tone: "outflow" },
    {
      key: "variable",
      label: "− Variable Expenses",
      amount: waterfall.variable_expenses,
      tone: "outflow",
    },
    {
      key: "unexpected",
      label: "− Unexpected",
      amount: waterfall.unexpected_expenses,
      tone: "outflow",
    },
    {
      key: "fcf",
      label: "= Operating FCF",
      amount: waterfall.operating_free_cashflow,
      tone: "result",
    },
    { key: "savings", label: "→ Savings", amount: waterfall.savings, tone: "allocation" },
    {
      key: "capital",
      label: "→ Capital Deployed",
      amount: waterfall.capital_deployments,
      tone: "allocation",
    },
  ];

  const maxStepMag = Math.max(1, ...steps.map((step) => Math.abs(step.amount)));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span>
          Period {formatDate(report.period.start_date)} → {formatDate(report.period.end_date)} ·
          Currency {currency}
        </span>
        <span>
          Organic FCF Margin:{" "}
          <strong className="text-foreground">
            {waterfall.organic_fcf_margin_pct.toFixed(1)}%
          </strong>{" "}
          · Debt Service Ratio:{" "}
          <strong className="text-foreground">
            {waterfall.debt_service_to_income_pct.toFixed(1)}%
          </strong>
        </span>
      </div>

      {/* Accessible SVG Horizontal Waterfall Chart */}
      <div className="rounded-lg border border-border bg-card p-4">
        <h3 className="text-sm font-semibold">Cashflow Waterfall</h3>
        <p className="mb-3 text-xs text-muted-foreground">
          Isolates internal sweeps and debt proceeds from true operating cashflow.
        </p>
        <svg
          role="img"
          aria-label="Operating Free Cashflow waterfall chart"
          viewBox="0 0 640 248"
          className="h-auto w-full"
        >
          <title>Operating Free Cashflow Waterfall ({currency})</title>
          {steps.map((step, index) => {
            const y = 10 + index * 29;
            const barWidth = Math.max(4, Math.round((Math.abs(step.amount) / maxStepMag) * 280));
            const fill =
              step.tone === "income"
                ? "var(--color-primary)"
                : step.tone === "outflow"
                  ? "var(--color-destructive)"
                  : step.tone === "result"
                    ? waterfall.operating_free_cashflow >= 0
                      ? "#10b981"
                      : "var(--color-destructive)"
                    : "#64748b";
            return (
              <g key={step.key}>
                <text
                  x={4}
                  y={y + 15}
                  fontSize="11"
                  fill="currentColor"
                  className="text-muted-foreground"
                >
                  {step.label}
                </text>
                <rect
                  x={155}
                  y={y + 2}
                  width={barWidth}
                  height={18}
                  rx={4}
                  fill={fill}
                  opacity={0.85}
                />
                <text x={445} y={y + 15} fontSize="11" fill="currentColor" className="font-medium">
                  {formatMoney(step.amount, currency)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Detailed Bucket Breakdown */}
      <div className="rounded-lg border border-border bg-card">
        <div className="border-b border-border px-4 py-3">
          <h3 className="text-sm font-semibold">Bucket Breakdown</h3>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Bucket</TableHead>
              <TableHead>Group</TableHead>
              <TableHead className="text-right">Transactions</TableHead>
              <TableHead className="text-right">Share of Income</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead className="text-right">Categories</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {buckets.map((item) => (
              <BucketTableRow
                key={item.bucket}
                item={item}
                currency={currency}
                expanded={expandedBucket === item.bucket}
                onToggle={() => {
                  setExpandedBucket((prev) => (prev === item.bucket ? null : item.bucket));
                }}
              />
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Visually Separated Non-Operating & Hygiene Cards */}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-dashed border-border bg-muted/30 p-4 text-sm">
          <h3 className="font-semibold">Non-Operating & Ledger Reconciliation</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Excluded from Operating FCF so sweeps and loan disbursements never inflate savings.
          </p>
          <dl className="mt-3 space-y-1.5 text-xs">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">
                Non-operating inflows (debt / principal returns)
              </dt>
              <dd className="font-medium tabular-nums">
                {formatMoney(waterfall.non_operating_inflows, currency)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Internal sweeps volume (isolated)</dt>
              <dd className="font-medium tabular-nums">
                {formatMoney(waterfall.internal_sweeps_volume, currency)}
              </dd>
            </div>
            <div className="flex justify-between border-t border-border pt-1.5">
              <dt className="text-muted-foreground">
                Net allocated surplus (post savings & capital)
              </dt>
              <dd className="font-medium tabular-nums">
                {formatMoney(waterfall.net_allocated_surplus, currency)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="font-medium">Net ledger cashflow</dt>
              <dd className="font-semibold tabular-nums">
                {formatMoney(waterfall.net_ledger_cashflow, currency)}
              </dd>
            </div>
          </dl>
        </div>

        <div className="rounded-lg border border-border bg-card p-4 text-sm">
          <h3 className="font-semibold">Settlement & Classification Diagnostics</h3>
          <dl className="mt-3 space-y-1.5 text-xs">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">In-transit transfers excluded</dt>
              <dd className="font-medium tabular-nums">
                {String(in_transit.count)} ({formatMoney(in_transit.total_volume, currency)})
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Unbucketed categories inferred via fallback</dt>
              <dd className="font-medium tabular-nums">
                {String(diagnostics.unbucketed_category_count)} (
                {formatMoney(diagnostics.unbucketed_amount, currency)})
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Cashflow-only CC itemized charges skipped</dt>
              <dd className="font-medium tabular-nums">
                {String(diagnostics.cashflow_only_cc_excluded_count)} (
                {formatMoney(diagnostics.cashflow_only_cc_excluded_amount, currency)})
              </dd>
            </div>
          </dl>
          {ccFlaggedNames.length > 0 ? (
            <p className="mt-2 text-xs text-muted-foreground">
              Cards flagged: {ccFlaggedNames.join(", ")}
            </p>
          ) : null}
        </div>
      </div>

      {monthly_series.length > 0 ? (
        <div className="rounded-lg border border-border bg-card">
          <div className="border-b border-border px-4 py-3">
            <h3 className="text-sm font-semibold">Monthly Operating Cashflow Series</h3>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Month</TableHead>
                <TableHead className="text-right">External Income</TableHead>
                <TableHead className="text-right">Operating Outflows</TableHead>
                <TableHead className="text-right">Operating FCF</TableHead>
                <TableHead className="text-right">Margin</TableHead>
                <TableHead className="text-right">Non-Op Inflows</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {monthly_series.map((row) => (
                <TableRow key={row.month}>
                  <TableCell className="font-medium">{row.month}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(row.total_external_income, currency)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(row.total_operating_outflows, currency)}
                  </TableCell>
                  <TableCell className="text-right font-medium tabular-nums">
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
        </div>
      ) : null}
    </div>
  );
}

function BucketTableRow({
  item,
  currency,
  expanded,
  onToggle,
}: {
  item: WaterfallBucketItem;
  currency: string;
  expanded: boolean;
  onToggle: () => void;
}) {
  const hasCategories = (item.top_categories?.length ?? 0) > 0;
  return (
    <>
      <TableRow>
        <TableCell className="font-medium">{item.label}</TableCell>
        <TableCell className="text-xs text-muted-foreground">
          {formatSlugLabel(item.group)}
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
              aria-label={`${expanded ? "Hide" : "Show"} top categories for ${item.label}`}
              onClick={onToggle}
            >
              {expanded ? "Hide" : "Top"}
            </Button>
          ) : (
            <span className="text-xs text-muted-foreground">—</span>
          )}
        </TableCell>
      </TableRow>
      {expanded && hasCategories ? (
        <TableRow className="bg-muted/30">
          <TableCell colSpan={6} className="py-2">
            <div className="flex flex-wrap gap-3 text-xs">
              {(item.top_categories ?? []).map((cat, idx) => (
                <span
                  key={`${cat.category_id ?? cat.category_name}-${String(idx)}`}
                  className="rounded border border-border bg-background px-2 py-1"
                >
                  {cat.category_name}:{" "}
                  <strong className="tabular-nums">{formatMoney(cat.amount, currency)}</strong>{" "}
                  <span className="text-muted-foreground">({String(cat.transaction_count)})</span>
                </span>
              ))}
            </div>
          </TableCell>
        </TableRow>
      ) : null}
    </>
  );
}
