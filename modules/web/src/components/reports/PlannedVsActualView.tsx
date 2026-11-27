import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import {
  SortableTableHead,
  sortItems,
  toggleSort,
  type SortState,
} from "@/components/table/SortableTableHead";
import { DEFAULT_PAGE_SIZE, TablePagination } from "@/components/table/TablePagination";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHeader, TableRow } from "@/components/ui/table";
import { useLocale } from "@/i18n/LocaleProvider";
import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import { formatSlugLabel } from "@/lib/formatSlugLabel";
import type { PlannedVsActualReportResponse } from "@/types/domain";

type PlannedVsActualViewProps = {
  report: PlannedVsActualReportResponse;
};

type VarianceFilter = "all" | "attention" | "unplanned";
type VarianceSortKey = "item" | "bucket" | "due" | "planned" | "actual" | "variance" | "status";
type RollupFilter = "all" | "favorable" | "unfavorable";
type RollupSortKey = "bucket" | "planned" | "actual" | "variance";

type CombinedVarianceRow = {
  id: string;
  title: string;
  subtitle: string;
  bucket: string;
  due: string;
  planned: number;
  actual: number;
  variance: number;
  isFavorable: boolean;
  status: string;
  isUnplanned: boolean;
};

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
  const { locale } = useLocale();
  const rollupsAi = useScopedAIToggle();
  const itemsAi = useScopedAIToggle();
  const [filterMode, setFilterMode] = useState<VarianceFilter>("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<SortState<VarianceSortKey>>({ key: "due", direction: "asc" });
  const [rollupFilter, setRollupFilter] = useState<RollupFilter>("all");
  const [rollupSearch, setRollupSearch] = useState("");
  const [rollupSort, setRollupSort] = useState<SortState<RollupSortKey>>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(DEFAULT_PAGE_SIZE);
  const { summary, currency } = report;
  const bucket_rollups = useMemo(() => report.bucket_rollups ?? [], [report.bucket_rollups]);
  const template_items = report.template_items ?? [];
  const unplanned_items = report.unplanned_items ?? [];
  const reconciliation_flags = report.reconciliation_flags ?? [];

  const combinedRows = useMemo<CombinedVarianceRow[]>(() => {
    const rows: CombinedVarianceRow[] = [];
    if (filterMode !== "unplanned") {
      for (const item of template_items) {
        if (
          filterMode === "attention" &&
          item.status !== "overdue" &&
          item.status !== "over_budget" &&
          item.status !== "partial"
        ) {
          continue;
        }
        rows.push({
          id: `${item.template_id}-${item.due_date}`,
          title: item.template_name,
          subtitle: item.category_name,
          bucket: item.bucket,
          due: item.due_date,
          planned: item.planned_amount,
          actual: item.actual_amount,
          variance: item.variance_amount,
          isFavorable: item.is_favorable,
          status: item.status,
          isUnplanned: false,
        });
      }
    }
    if (filterMode === "all" || filterMode === "unplanned") {
      unplanned_items.forEach((item, idx) => {
        rows.push({
          id: `${item.category_id ?? item.category_name}-${item.bucket}-${String(idx)}`,
          title: item.category_name,
          subtitle: `${String(item.transaction_count)} unlinked posting(s)`,
          bucket: item.bucket,
          due: "",
          planned: 0,
          actual: item.actual_amount,
          variance: item.actual_amount,
          isFavorable: false,
          status: "unplanned",
          isUnplanned: true,
        });
      });
    }
    const q = search.trim().toLowerCase();
    const searched = q
      ? rows.filter(
          (r) =>
            r.title.toLowerCase().includes(q) ||
            r.subtitle.toLowerCase().includes(q) ||
            formatSlugLabel(r.bucket).toLowerCase().includes(q),
        )
      : rows;
    return sortItems(searched, sort, {
      item: (r) => r.title,
      bucket: (r) => r.bucket,
      due: (r) => r.due,
      planned: (r) => r.planned,
      actual: (r) => r.actual,
      variance: (r) => r.variance,
      status: (r) => r.status,
    });
  }, [filterMode, search, sort, template_items, unplanned_items]);

  const visibleRollups = useMemo(() => {
    const q = rollupSearch.trim().toLowerCase();
    const filtered = bucket_rollups.filter((row) => {
      if (rollupFilter === "favorable" && !row.is_favorable) return false;
      if (rollupFilter === "unfavorable" && row.is_favorable) return false;
      if (q && !row.label.toLowerCase().includes(q) && !row.bucket.toLowerCase().includes(q)) {
        return false;
      }
      return true;
    });
    return sortItems(filtered, rollupSort, {
      bucket: (r) => r.label,
      planned: (r) => r.planned_amount,
      actual: (r) => r.actual_amount,
      variance: (r) => r.variance_amount,
    });
  }, [bucket_rollups, rollupFilter, rollupSearch, rollupSort]);

  const pagedRows = useMemo(() => {
    const start = (page - 1) * pageSize;
    return combinedRows.slice(start, start + pageSize);
  }, [combinedRows, page, pageSize]);

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
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
            <h3 className="text-sm font-semibold">Bucket Rollups</h3>
            <div className="flex flex-wrap items-center gap-2">
              <Input
                aria-label="Filter bucket rollups"
                placeholder="Filter buckets…"
                className="h-8 w-40 text-xs"
                value={rollupSearch}
                onChange={(event) => {
                  setRollupSearch(event.target.value);
                }}
              />
              <div className="flex gap-1.5" role="group" aria-label="Bucket rollup status filter">
                {(
                  [
                    ["all", "All"],
                    ["favorable", "On track"],
                    ["unfavorable", "Over / off plan"],
                  ] as const
                ).map(([key, label]) => (
                  <Button
                    key={key}
                    type="button"
                    size="sm"
                    variant={rollupFilter === key ? "default" : "outline"}
                    aria-pressed={rollupFilter === key}
                    onClick={() => {
                      setRollupFilter(key);
                    }}
                  >
                    {label}
                  </Button>
                ))}
              </div>
              <ScopedAITrigger
                open={rollupsAi.open}
                panelId={rollupsAi.panelId}
                onToggle={rollupsAi.toggle}
              />
            </div>
          </div>
          <ScopedAIPanel
            id={rollupsAi.panelId}
            open={rollupsAi.open}
            onClose={rollupsAi.close}
            module="reports"
            view="variance"
            control="bucket-rollups-table"
            title="Bucket Rollups"
            currency={currency}
            className="m-3"
            surfaceContext={{
              currency,
              adherence_pct: summary.adherence_pct,
              filter: rollupFilter,
              search: rollupSearch || null,
              rows: visibleRollups,
            }}
            suggestedPrompts={
              locale === "es-CO"
                ? [
                    "¿Qué bloque se desvió más del presupuesto planeado?",
                    "Resume dónde cumplí y dónde excedí lo presupuestado.",
                  ]
                : [
                    "Which bucket deviated most sharply from planned targets?",
                    "Summarize where I stayed on track vs. overran plan.",
                  ]
            }
          />
          {visibleRollups.length === 0 ? (
            <div className="px-4 py-6 text-center text-xs text-muted-foreground">
              No bucket rollups match this filter.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <SortableTableHead
                    label="Bucket"
                    sortKey="bucket"
                    sort={rollupSort}
                    onSort={(key) => {
                      setRollupSort((prev) => toggleSort(prev, key, "asc"));
                    }}
                  />
                  <SortableTableHead
                    label="Planned"
                    sortKey="planned"
                    sort={rollupSort}
                    onSort={(key) => {
                      setRollupSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                    align="right"
                  />
                  <SortableTableHead
                    label="Actual"
                    sortKey="actual"
                    sort={rollupSort}
                    onSort={(key) => {
                      setRollupSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                    align="right"
                  />
                  <SortableTableHead
                    label="Variance"
                    sortKey="variance"
                    sort={rollupSort}
                    onSort={(key) => {
                      setRollupSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                    align="right"
                  />
                </TableRow>
              </TableHeader>
              <TableBody>
                {visibleRollups.map((row) => (
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
          )}
        </div>
      ) : null}

      <div className="overflow-hidden rounded-xl border border-border bg-card shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
          <h3 className="text-sm font-semibold">Template & Unplanned Variance</h3>
          <div className="flex flex-wrap items-center gap-2">
            <Input
              aria-label="Filter variance rows"
              placeholder="Filter items…"
              className="h-8 w-44 text-xs"
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
            />
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
                    setPage(1);
                  }}
                >
                  {label}
                </Button>
              ))}
            </div>
            <ScopedAITrigger
              open={itemsAi.open}
              panelId={itemsAi.panelId}
              onToggle={itemsAi.toggle}
            />
          </div>
        </div>

        <ScopedAIPanel
          id={itemsAi.panelId}
          open={itemsAi.open}
          onClose={itemsAi.close}
          module="reports"
          view="variance"
          control="variance-items-table"
          title="Template & Unplanned Variance"
          currency={currency}
          className="m-3"
          surfaceContext={{
            currency,
            filter_mode: filterMode,
            search: search || null,
            sort,
            total_rows: combinedRows.length,
            reconciliation_flags: reconciliation_flags.slice(0, 8),
            visible_rows: pagedRows.slice(0, 10).map((r) => ({
              title: r.title,
              bucket: r.bucket,
              planned: r.planned,
              actual: r.actual,
              variance: r.variance,
              status: r.status,
            })),
          }}
          suggestedPrompts={
            locale === "es-CO"
              ? [
                  "¿Qué movimientos no planeados o vencidos requieren atención?",
                  "Explica las alertas de conciliación y cómo resolverlas.",
                ]
              : [
                  "Which overdue, over-budget, or unplanned items need action?",
                  "Explain the active reconciliation flags and how to clean them up.",
                ]
          }
        />

        {combinedRows.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">
            No planned templates or unplanned postings match this filter.
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <SortableTableHead
                    label="Item"
                    sortKey="item"
                    sort={sort}
                    onSort={(key) => {
                      setSort((prev) => toggleSort(prev, key));
                    }}
                  />
                  <SortableTableHead
                    label="Bucket"
                    sortKey="bucket"
                    sort={sort}
                    onSort={(key) => {
                      setSort((prev) => toggleSort(prev, key));
                    }}
                  />
                  <SortableTableHead
                    label="Due"
                    sortKey="due"
                    sort={sort}
                    onSort={(key) => {
                      setSort((prev) => toggleSort(prev, key));
                    }}
                  />
                  <SortableTableHead
                    label="Planned"
                    sortKey="planned"
                    sort={sort}
                    align="right"
                    onSort={(key) => {
                      setSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                  />
                  <SortableTableHead
                    label="Actual"
                    sortKey="actual"
                    sort={sort}
                    align="right"
                    onSort={(key) => {
                      setSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                  />
                  <SortableTableHead
                    label="Variance"
                    sortKey="variance"
                    sort={sort}
                    align="right"
                    onSort={(key) => {
                      setSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                  />
                  <SortableTableHead
                    label="Status"
                    sortKey="status"
                    sort={sort}
                    onSort={(key) => {
                      setSort((prev) => toggleSort(prev, key));
                    }}
                  />
                </TableRow>
              </TableHeader>
              <TableBody>
                {pagedRows.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell className="font-medium">
                      <div>{row.title}</div>
                      <div className="text-xs text-muted-foreground">{row.subtitle}</div>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatSlugLabel(row.bucket)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {row.due ? formatDate(row.due) : "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">
                      {formatMoney(row.planned, currency)}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums">
                      {formatMoney(row.actual, currency)}
                    </TableCell>
                    <TableCell
                      className={`text-right tabular-nums ${
                        row.isUnplanned
                          ? "text-warning"
                          : row.isFavorable
                            ? "text-success"
                            : "text-destructive"
                      }`}
                    >
                      {row.isUnplanned ? "+" : ""}
                      {formatMoney(row.variance, currency)}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                          STATUS_BADGES[row.status] ?? "bg-muted text-muted-foreground"
                        }`}
                      >
                        {row.isUnplanned ? "Unplanned" : formatSlugLabel(row.status)}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <TablePagination
              page={page}
              pageSize={pageSize}
              total={combinedRows.length}
              visibleCount={pagedRows.length}
              onPageChange={setPage}
              onPageSizeChange={(nextSize) => {
                setPageSize(nextSize);
                setPage(1);
              }}
            />
          </>
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
