import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatMoney } from "@/lib/formatMoney";
import type { SpendingReportResponse } from "@/types/domain";

type SpendingReportViewProps = {
  report: SpendingReportResponse;
  /** Display currency for amounts (API does not return currency on report). */
  currency?: string;
};

/** Renders ``SpendingReportResponse`` fields — no client-side aggregation. */
export function SpendingReportView({ report, currency = "USD" }: SpendingReportViewProps) {
  const breakdown = report.breakdown ?? [];

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <SummaryStat label="Total spending" value={formatMoney(report.total_spending, currency)} />
        <SummaryStat label="Total income" value={formatMoney(report.total_income, currency)} />
        <SummaryStat label="Net savings" value={formatMoney(report.net_savings, currency)} />
      </div>

      <p className="text-xs text-muted-foreground">
        Period {report.period.start_date} → {report.period.end_date} · grouped by {report.group_by}
      </p>

      {breakdown.length === 0 ? (
        <div className="rounded-md border border-dashed border-border px-4 py-8 text-center">
          <p className="text-sm font-medium">No spending in this window</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Try a wider date range or another account filter.
          </p>
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>{report.group_by === "account" ? "Account" : "Category"}</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead className="text-right">Share</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {breakdown.map((row) => (
              <TableRow key={`${row.category}-${String(row.amount)}`}>
                <TableCell className="font-medium">{row.category}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatMoney(row.amount, currency)}
                </TableCell>
                <TableCell className="text-right tabular-nums text-muted-foreground">
                  {row.percentage.toFixed(1)}%
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}

function SummaryStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border px-3 py-2">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-lg font-semibold tabular-nums tracking-tight">{value}</p>
    </div>
  );
}
