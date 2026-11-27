import { ArrowDownRight, ArrowUpRight, PiggyBank } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { Table, TableBody, TableCell, TableHeader, TableRow } from "@/components/ui/table";
import { useLocale } from "@/i18n/LocaleProvider";
import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import { formatSlugLabel } from "@/lib/formatSlugLabel";
import { cn } from "@/lib/utils";
import type { SpendingReportResponse } from "@/types/domain";

type SpendingReportViewProps = {
  report: SpendingReportResponse;
  /** Display currency for amounts (API does not return currency on report). */
  currency?: string;
};

type SpendingSortKey = "category" | "amount" | "percentage";

const SLICE_PALETTE = [
  "#0ea5e9", // sky
  "#10b981", // emerald
  "#8b5cf6", // violet
  "#f59e0b", // amber
  "#f43f5e", // rose
  "#14b8a6", // teal
  "#6366f1", // indigo
  "#64748b", // slate
];

/** Interactive Spending breakdown with SVG share ring, inline bars, and ledger drilldown. */
export function SpendingReportView({ report, currency = "USD" }: SpendingReportViewProps) {
  const { locale } = useLocale();
  const ringAi = useScopedAIToggle();
  const tableAi = useScopedAIToggle();
  const breakdown = report.breakdown ?? [];
  const [search, setSearch] = useState("");
  const [hoveredCat, setHoveredCat] = useState<string | null>(null);
  const [sort, setSort] = useState<SortState<SpendingSortKey>>({
    key: "amount",
    direction: "desc",
  });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(DEFAULT_PAGE_SIZE);

  const colorByCategory = useMemo(() => {
    const map = new Map<string, string>();
    breakdown.forEach((row, idx) => {
      map.set(row.category, SLICE_PALETTE[idx % SLICE_PALETTE.length] ?? "#64748b");
    });
    return map;
  }, [breakdown]);

  const topSlices = useMemo(() => {
    const ordered = [...breakdown].sort((a, b) => b.percentage - a.percentage).slice(0, 6);
    const radius = 56;
    const circumference = 2 * Math.PI * radius;
    return ordered.reduce<
      Array<
        (typeof ordered)[number] & {
          color: string;
          dashArray: string;
          dashOffset: number;
          _nextOffset: number;
        }
      >
    >((acc, row) => {
      const prevOffset = acc[acc.length - 1]?._nextOffset ?? 0;
      const length = Math.max(2, (Math.max(0, row.percentage) / 100) * circumference);
      acc.push({
        ...row,
        color: colorByCategory.get(row.category) ?? "#64748b",
        dashArray: `${length.toFixed(2)} ${(circumference - length).toFixed(2)}`,
        dashOffset: -prevOffset,
        _nextOffset: prevOffset + length,
      });
      return acc;
    }, []);
  }, [breakdown, colorByCategory]);

  const activeSlice = useMemo(
    () => topSlices.find((s) => s.category === hoveredCat) ?? null,
    [hoveredCat, topSlices],
  );

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return breakdown;
    return breakdown.filter((row) => row.category.toLowerCase().includes(q));
  }, [breakdown, search]);

  const sorted = useMemo(
    () =>
      sortItems(filtered, sort, {
        category: (r) => r.category,
        amount: (r) => r.amount,
        percentage: (r) => r.percentage,
      }),
    [filtered, sort],
  );

  const paged = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sorted.slice(start, start + pageSize);
  }, [page, pageSize, sorted]);

  const netPositive = report.net_savings >= 0;

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-3">
        <SummaryStat
          label="Total spending"
          value={formatMoney(report.total_spending, currency)}
          tone="negative"
          icon={ArrowDownRight}
        />
        <SummaryStat
          label="Total income"
          value={formatMoney(report.total_income, currency)}
          tone="positive"
          icon={ArrowUpRight}
        />
        <SummaryStat
          label="Net savings"
          value={formatMoney(report.net_savings, currency)}
          tone={netPositive ? "positive" : "negative"}
          icon={PiggyBank}
        />
      </div>

      <p className="text-xs text-muted-foreground">
        Period {formatDate(report.period.start_date)} → {formatDate(report.period.end_date)} ·
        grouped by <strong className="text-foreground">{formatSlugLabel(report.group_by)}</strong>
      </p>

      {breakdown.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border bg-card px-4 py-8 text-center">
          <p className="text-sm font-medium">No spending in this window</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Try a wider date range or another account filter.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[19rem_1fr]">
          {/* Interactive Share Ring */}
          <div className="flex flex-col items-center justify-between rounded-xl border border-border bg-card p-5">
            <div className="flex w-full items-start justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold">Top Share Distribution</h3>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Hover a slice to inspect; click to filter.
                </p>
              </div>
              <ScopedAITrigger
                open={ringAi.open}
                panelId={ringAi.panelId}
                onToggle={ringAi.toggle}
              />
            </div>
            <ScopedAIPanel
              id={ringAi.panelId}
              open={ringAi.open}
              onClose={ringAi.close}
              module="reports"
              view="spending"
              control="spending-share-ring"
              title="Top Share Distribution"
              currency={currency}
              className="mt-3 w-full"
              surfaceContext={{
                currency,
                group_by: report.group_by,
                total_spending: report.total_spending,
                total_income: report.total_income,
                net_savings: report.net_savings,
                hovered_or_filtered: hoveredCat ?? (search || null),
                top_slices: topSlices.map((s) => ({
                  category: s.category,
                  amount: s.amount,
                  pct: s.percentage,
                })),
              }}
              suggestedPrompts={
                locale === "es-CO"
                  ? [
                      "¿Qué concentra la mayor parte de mi gasto?",
                      "Evalúa la relación entre ingreso total, gasto y ahorro neto.",
                    ]
                  : [
                      "Where is my spending most concentrated?",
                      "Evaluate the balance between total spending, income, and net savings.",
                    ]
              }
            />
            <div className="relative my-4 flex items-center justify-center">
              <svg viewBox="0 0 144 144" className="size-40 -rotate-90">
                <circle
                  cx="72"
                  cy="72"
                  r="56"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="16"
                  className="text-muted/40"
                />
                {topSlices.map((slice) => {
                  const isActive = hoveredCat === slice.category;
                  return (
                    <circle
                      key={slice.category}
                      cx="72"
                      cy="72"
                      r="56"
                      fill="none"
                      stroke={slice.color}
                      strokeWidth={isActive ? 20 : 16}
                      strokeDasharray={slice.dashArray}
                      strokeDashoffset={slice.dashOffset}
                      className="cursor-pointer transition-all duration-200 ease-out"
                      opacity={hoveredCat && !isActive ? 0.35 : 0.95}
                      onMouseEnter={() => setHoveredCat(slice.category)}
                      onMouseLeave={() => setHoveredCat(null)}
                      onClick={() => {
                        setSearch((prev) => (prev === slice.category ? "" : slice.category));
                        setPage(1);
                      }}
                    />
                  );
                })}
              </svg>
              <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center px-5 text-center">
                <span className="max-w-[7rem] truncate text-[11px] font-medium text-muted-foreground">
                  {activeSlice ? activeSlice.category : "Total"}
                </span>
                <span className="mt-0.5 text-sm font-semibold tabular-nums text-foreground">
                  {activeSlice
                    ? `${activeSlice.percentage.toFixed(1)}%`
                    : formatMoney(report.total_spending, currency)}
                </span>
              </div>
            </div>
            <ul className="w-full space-y-1.5 text-xs">
              {topSlices.map((slice) => (
                <li key={slice.category}>
                  <button
                    type="button"
                    onMouseEnter={() => setHoveredCat(slice.category)}
                    onMouseLeave={() => setHoveredCat(null)}
                    onClick={() => {
                      setSearch((prev) => (prev === slice.category ? "" : slice.category));
                      setPage(1);
                    }}
                    className={cn(
                      "flex w-full items-center justify-between gap-2 rounded-md px-2 py-1 text-left transition-colors",
                      hoveredCat === slice.category || search === slice.category
                        ? "bg-muted font-medium"
                        : "hover:bg-muted/50",
                    )}
                  >
                    <span className="flex min-w-0 items-center gap-2">
                      <span
                        className="size-2.5 shrink-0 rounded-full"
                        style={{ backgroundColor: slice.color }}
                      />
                      <span className="truncate">{slice.category}</span>
                    </span>
                    <span className="shrink-0 tabular-nums text-muted-foreground">
                      {slice.percentage.toFixed(1)}%
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {/* Colorized Breakdown Table */}
          <div className="overflow-hidden rounded-xl border border-border bg-card">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
              <h3 className="text-sm font-semibold">Breakdown</h3>
              <div className="flex flex-wrap items-center gap-2">
                <Input
                  aria-label="Filter spending breakdown"
                  placeholder={`Filter ${report.group_by === "account" ? "accounts" : "categories"}…`}
                  className="h-8 max-w-xs text-xs"
                  value={search}
                  onChange={(event) => {
                    setSearch(event.target.value);
                    setPage(1);
                  }}
                />
                <ScopedAITrigger
                  open={tableAi.open}
                  panelId={tableAi.panelId}
                  onToggle={tableAi.toggle}
                />
              </div>
            </div>
            <ScopedAIPanel
              id={tableAi.panelId}
              open={tableAi.open}
              onClose={tableAi.close}
              module="reports"
              view="spending"
              control="spending-breakdown-table"
              title="Spending Breakdown"
              currency={currency}
              className="m-3"
              surfaceContext={{
                currency,
                group_by: report.group_by,
                search_filter: search || null,
                sort,
                visible_rows: paged.slice(0, 12).map((r) => ({
                  name: r.category,
                  amount: r.amount,
                  pct: r.percentage,
                })),
                total_filtered_rows: sorted.length,
              }}
              suggestedPrompts={
                locale === "es-CO"
                  ? [
                      "Identifica los principales rubros en esta vista filtrada.",
                      "¿Dónde hay mayor oportunidad de optimizar gasto?",
                    ]
                  : [
                      "Analyze the top items in this filtered spending table.",
                      "Where is the clearest opportunity to optimize spending?",
                    ]
              }
            />
            <Table>
              <TableHeader>
                <TableRow>
                  <SortableTableHead
                    label={report.group_by === "account" ? "Account" : "Category"}
                    sortKey="category"
                    sort={sort}
                    onSort={(key) => {
                      setSort((prev) => toggleSort(prev, key));
                    }}
                  />
                  <SortableTableHead
                    label="Amount"
                    sortKey="amount"
                    sort={sort}
                    align="right"
                    onSort={(key) => {
                      setSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                  />
                  <SortableTableHead
                    label="Share"
                    sortKey="percentage"
                    sort={sort}
                    align="right"
                    onSort={(key) => {
                      setSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                  />
                </TableRow>
              </TableHeader>
              <TableBody>
                {paged.map((row, index) => {
                  const color = colorByCategory.get(row.category) ?? "#64748b";
                  return (
                    <TableRow
                      key={`${row.category}-${String(index)}`}
                      onMouseEnter={() => setHoveredCat(row.category)}
                      onMouseLeave={() => setHoveredCat(null)}
                      className={cn(hoveredCat === row.category && "bg-muted/45")}
                    >
                      <TableCell>
                        <div className="space-y-1.5">
                          <div className="flex items-center justify-between gap-2">
                            <Link
                              to={`/transactions?search=${encodeURIComponent(row.category)}`}
                              className="inline-flex items-center gap-1.5 font-medium hover:text-primary"
                            >
                              <span
                                className="size-2 shrink-0 rounded-full"
                                style={{ backgroundColor: color }}
                              />
                              <span>{row.category}</span>
                              <ArrowUpRight className="size-3 text-muted-foreground" />
                            </Link>
                          </div>
                          <div className="h-1.5 w-full max-w-[14rem] overflow-hidden rounded-full bg-muted">
                            <div
                              className="h-full rounded-full transition-all duration-500 ease-out"
                              style={{
                                width: `${Math.max(2, Math.min(100, row.percentage)).toFixed(1)}%`,
                                backgroundColor: color,
                              }}
                            />
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-medium tabular-nums">
                        {formatMoney(row.amount, currency)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {row.percentage.toFixed(1)}%
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
            <TablePagination
              page={page}
              pageSize={pageSize}
              total={sorted.length}
              visibleCount={paged.length}
              onPageChange={setPage}
              onPageSizeChange={(nextSize) => {
                setPageSize(nextSize);
                setPage(1);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryStat({
  label,
  value,
  tone,
  icon: Icon,
}: {
  label: string;
  value: string;
  tone: "positive" | "negative";
  icon: typeof PiggyBank;
}) {
  return (
    <div
      className={cn(
        "flex items-center justify-between rounded-xl border px-4 py-3.5",
        tone === "positive"
          ? "border-emerald-500/25 bg-emerald-500/[0.05]"
          : "border-rose-500/25 bg-rose-500/[0.05]",
      )}
    >
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p
          className={cn(
            "mt-0.5 text-lg font-semibold tabular-nums tracking-tight",
            tone === "positive"
              ? "text-emerald-700 dark:text-emerald-300"
              : "text-rose-700 dark:text-rose-300",
          )}
        >
          {value}
        </p>
      </div>
      <span
        className={cn(
          "inline-flex size-8 items-center justify-center rounded-lg",
          tone === "positive"
            ? "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300"
            : "bg-rose-500/15 text-rose-700 dark:text-rose-300",
        )}
      >
        <Icon aria-hidden="true" className="size-4" />
      </span>
    </div>
  );
}
