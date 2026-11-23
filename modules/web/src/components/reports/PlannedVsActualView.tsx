import { useState } from "react";
import { Link } from "react-router-dom";

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
import type { PlannedVsActualReportResponse } from "@/types/domain";

type PlannedVsActualViewProps = {
  report: PlannedVsActualReportResponse;
};

type VarianceFilter = "all" | "attention" | "unplanned";

const STATUS_BADGES: Record<string, string> = {
  paid: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  exceeded: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-400",
  partial: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
  upcoming: "bg-muted text-muted-foreground",
  over_budget: "bg-destructive/15 text-destructive",
  overdue: "bg-destructive/15 text-destructive",
  unplanned: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
};

/** Presentation-only Planned vs. Actual variance & reconciliation alerts view. */
export function PlannedVsActualView({ report }: PlannedVsActualViewProps) {
  const [filterMode, setFilterMode] = useState<VarianceFilter>("all");
  const { summary, currency } = report;
  const bucket_rollups = report.bucket_rollups ?? [];
  const template_items = report.template_items ?? [];
  const unplanned_items = report.unplanned_items ?? [];
  const reconciliation_flags = report.reconciliation_flags ?? [];

  const filteredTemplates = template_items.filter((item) => {
    if (filterMode === "unplanned") {
      return false;
    }
    if (filterMode === "attention") {
      return (
        item.status === "overdue" || item.status === "over_budget" || item.status === "partial"
      );
    }
    return true;
  });

  const showUnplanned = filterMode === "all" || filterMode === "unplanned";

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <MetricBox
          label="Planned vs. Actual Income"
          primary={formatMoney(summary.actual_income, currency)}
          secondary={`Planned ${formatMoney(summary.planned_income, currency)}`}
        />
        <MetricBox
          label="Planned vs. Actual Outflows"
          primary={formatMoney(summary.actual_outflows, currency)}
          secondary={`Planned ${formatMoney(summary.planned_outflows, currency)}`}
        />
        <MetricBox
          label="Operating FCF Delta"
          primary={formatMoney(summary.net_fcf_variance, currency)}
          secondary={`Planned ${formatMoney(summary.planned_operating_fcf, currency)} → Actual ${formatMoney(summary.actual_operating_fcf, currency)}`}
        />
        <MetricBox
          label="Plan Adherence"
          primary={`${summary.adherence_pct.toFixed(1)}%`}
          secondary={`${String(reconciliation_flags.length)} reconciliation alert(s)`}
        />
      </div>

      {bucket_rollups.length > 0 ? (
        <div className="rounded-lg border border-border bg-card">
          <div className="border-b border-border px-4 py-3">
            <h3 className="text-sm font-semibold">Bucket Rollups</h3>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Bucket</TableHead>
                <TableHead className="text-right">Planned</TableHead>
                <TableHead className="text-right">Actual</TableHead>
                <TableHead className="text-right">Variance</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {bucket_rollups.map((row) => (
                <TableRow key={row.bucket}>
                  <TableCell className="font-medium">{row.label}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(row.planned_amount, currency)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(row.actual_amount, currency)}
                  </TableCell>
                  <TableCell
                    className={`text-right font-medium tabular-nums ${
                      row.is_favorable
                        ? "text-emerald-700 dark:text-emerald-400"
                        : "text-destructive"
                    }`}
                  >
                    {formatMoney(row.variance_amount, currency)} ({row.variance_pct.toFixed(1)}%)
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      ) : null}

      <div className="rounded-lg border border-border bg-card">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
          <h3 className="text-sm font-semibold">Template & Unplanned Variance</h3>
          <div className="flex gap-1.5" role="group" aria-label="Variance row filter">
            {(
              [
                ["all", "All"],
                ["attention", "Needs attention"],
                ["unplanned", "Unplanned only"],
              ] as const
            ).map(([key, label]) => (
              <Button
                key={key}
                type="button"
                size="sm"
                variant={filterMode === key ? "default" : "outline"}
                aria-pressed={filterMode === key}
                onClick={() => {
                  setFilterMode(key);
                }}
              >
                {label}
              </Button>
            ))}
          </div>
        </div>

        {filteredTemplates.length === 0 && (!showUnplanned || unplanned_items.length === 0) ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">
            No planned templates or unplanned postings match this filter.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Item</TableHead>
                <TableHead>Bucket</TableHead>
                <TableHead>Due</TableHead>
                <TableHead className="text-right">Planned</TableHead>
                <TableHead className="text-right">Actual</TableHead>
                <TableHead className="text-right">Variance</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredTemplates.map((item) => (
                <TableRow key={`${item.template_id}-${item.due_date}`}>
                  <TableCell className="font-medium">
                    <div>{item.template_name}</div>
                    <div className="text-xs text-muted-foreground">{item.category_name}</div>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatSlugLabel(item.bucket)}
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {formatDate(item.due_date)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(item.planned_amount, currency)}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatMoney(item.actual_amount, currency)}
                  </TableCell>
                  <TableCell
                    className={`text-right tabular-nums ${
                      item.is_favorable
                        ? "text-emerald-700 dark:text-emerald-400"
                        : "text-destructive"
                    }`}
                  >
                    {formatMoney(item.variance_amount, currency)}
                  </TableCell>
                  <TableCell>
                    <span
                      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                        STATUS_BADGES[item.status] ?? "bg-muted text-muted-foreground"
                      }`}
                    >
                      {formatSlugLabel(item.status)}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
              {showUnplanned
                ? unplanned_items.map((item, idx) => (
                    <TableRow
                      key={`${item.category_id ?? item.category_name}-${item.bucket}-${String(idx)}`}
                    >
                      <TableCell className="font-medium">
                        <div>{item.category_name}</div>
                        <div className="text-xs text-muted-foreground">
                          {String(item.transaction_count)} unlinked posting(s)
                        </div>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {formatSlugLabel(item.bucket)}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">—</TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {formatMoney(0, currency)}
                      </TableCell>
                      <TableCell className="text-right font-medium tabular-nums">
                        {formatMoney(item.actual_amount, currency)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-amber-700 dark:text-amber-400">
                        +{formatMoney(item.actual_amount, currency)}
                      </TableCell>
                      <TableCell>
                        <span
                          className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGES.unplanned}`}
                        >
                          Unplanned
                        </span>
                      </TableCell>
                    </TableRow>
                  ))
                : null}
            </TableBody>
          </Table>
        )}
      </div>

      {reconciliation_flags.length > 0 ? (
        <section
          aria-label="Reconciliation alerts"
          className="rounded-lg border border-amber-500/40 bg-amber-500/5 p-4"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-semibold">Reconciliation Alerts</h3>
              <p className="text-xs text-muted-foreground">
                Potential unlinked template matches, duplicate entries, or unbucketed categories.
              </p>
            </div>
            <Link
              to="/transactions"
              className="text-xs font-medium text-primary underline-offset-4 hover:underline"
            >
              Review in Transactions →
            </Link>
          </div>
          <ul className="mt-3 space-y-2 text-xs">
            {reconciliation_flags.map((flag, idx) => (
              <li
                key={`${flag.code}-${String(idx)}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded border border-border bg-background px-3 py-2"
              >
                <span>{flag.message}</span>
                <span className="rounded bg-muted px-2 py-0.5 font-medium text-muted-foreground">
                  {formatSlugLabel(flag.code)}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function MetricBox({
  label,
  primary,
  secondary,
}: {
  label: string;
  primary: string;
  secondary: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-3.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold tabular-nums">{primary}</p>
      <p className="mt-0.5 text-xs text-muted-foreground">{secondary}</p>
    </div>
  );
}
