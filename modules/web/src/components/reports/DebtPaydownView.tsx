import { useState } from "react";

import { DebtSimulatorPanel } from "@/components/reports/DebtSimulatorPanel";
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
import type {
  DebtPaydownReportResponse,
  DebtPaydownSimulationRequest,
  DebtPaydownSimulationResponse,
  DebtTrajectoryPoint,
} from "@/types/domain";

type DebtPaydownViewProps = {
  report: DebtPaydownReportResponse;
  simulation?: DebtPaydownSimulationResponse;
  isSimulating: boolean;
  simulationError: string | null;
  onSimulate: (request: DebtPaydownSimulationRequest) => void;
};

/** 2-column presentation-only Debt Interest-Drag & Backend Prepayment Simulator workspace. */
export function DebtPaydownView({
  report,
  simulation,
  isSimulating,
  simulationError,
  onSimulate,
}: DebtPaydownViewProps) {
  const [showAllMonths, setShowAllMonths] = useState(false);
  const { summary, liquidity_context, excluded_liabilities, currency } = report;
  const liabilities = report.liabilities ?? [];
  const excludedNames = excluded_liabilities?.account_names ?? [];
  const simulationTrajectory = simulation?.monthly_trajectory ?? [];
  const visibleTrajectory = showAllMonths
    ? simulationTrajectory
    : simulationTrajectory.slice(0, 24);

  return (
    <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
      <DebtSimulatorPanel
        currency={currency}
        liquidityContext={liquidity_context}
        simulation={simulation}
        isSimulating={isSimulating}
        errorMessage={simulationError}
        onSimulate={onSimulate}
      />

      <div className="space-y-6">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border border-border bg-card p-3.5">
            <p className="text-xs text-muted-foreground">Active Debt Total</p>
            <p className="mt-1 text-lg font-semibold tabular-nums">
              {formatMoney(summary.total_debt, currency)}
            </p>
            <p className="text-xs text-muted-foreground">
              {String(summary.active_liability_count)} active liability account(s)
            </p>
          </div>
          <div className="rounded-lg border border-border bg-card p-3.5">
            <p className="text-xs text-muted-foreground">Monthly / Annual Drag</p>
            <p className="mt-1 text-lg font-semibold tabular-nums">
              {formatMoney(summary.total_monthly_interest_drag, currency)}
            </p>
            <p className="text-xs text-muted-foreground">
              {formatMoney(summary.total_annual_interest_drag, currency)}/yr ·{" "}
              {summary.weighted_average_ea_pct.toFixed(2)}% avg EA
            </p>
          </div>
          <div className="rounded-lg border border-border bg-card p-3.5">
            <p className="text-xs text-muted-foreground">Contractual Debt Service</p>
            <p className="mt-1 text-lg font-semibold tabular-nums">
              {formatMoney(summary.total_monthly_contractual_payment, currency)}/mo
            </p>
            <p className="text-xs text-muted-foreground">
              Burn est. {formatMoney(liquidity_context.baseline_monthly_burn, currency)}/mo
            </p>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card">
          <div className="border-b border-border px-4 py-3">
            <h3 className="text-sm font-semibold">Priority Liability Ranking (Highest EA First)</h3>
          </div>
          {liabilities.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
              No active liabilities in {currency}.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Liability</TableHead>
                  <TableHead className="text-right">Balance</TableHead>
                  <TableHead className="text-right">EA / Monthly</TableHead>
                  <TableHead className="text-right">Interest Drag</TableHead>
                  <TableHead className="text-right">Payment / Extras</TableHead>
                  <TableHead className="text-right">Est. Payoff</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {liabilities.map((item) => (
                  <TableRow key={item.account_id}>
                    <TableCell className="font-semibold tabular-nums">
                      {String(item.priority_rank)}
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{item.account_name}</div>
                      <div className="text-xs text-muted-foreground">
                        {formatSlugLabel(item.account_kind)}
                        {item.remaining_periods !== null && item.remaining_periods !== undefined
                          ? ` · ${String(item.remaining_periods)} periods left`
                          : ""}
                      </div>
                      {item.negative_amortization ? (
                        <span className="mt-1 inline-block rounded bg-destructive/15 px-1.5 py-0.5 text-xs font-medium text-destructive">
                          Negative amortization
                        </span>
                      ) : null}
                      {item.linked_asset ? (
                        <div className="mt-1 text-xs text-muted-foreground">
                          Finances {item.linked_asset.asset_name} (net carry{" "}
                          <span className="tabular-nums">
                            {formatMoney(item.linked_asset.net_monthly_carry, currency)}
                          </span>
                          /mo)
                        </div>
                      ) : null}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums">
                      {formatMoney(item.balance, currency)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      <div>{item.effective_annual_rate_pct.toFixed(2)}% EA</div>
                      <div className="text-xs text-muted-foreground">
                        {item.effective_monthly_rate_pct.toFixed(2)}% MV
                      </div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      <div>{formatMoney(item.monthly_interest_drag, currency)}/mo</div>
                      <div className="text-xs text-muted-foreground">
                        {formatMoney(item.annual_interest_drag, currency)}/yr
                      </div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      <div>{formatMoney(item.monthly_contractual_payment, currency)}</div>
                      {item.monthly_extras_payment > 0 ? (
                        <div className="text-xs text-muted-foreground">
                          incl. {formatMoney(item.monthly_extras_payment, currency)} extras
                        </div>
                      ) : null}
                    </TableCell>
                    <TableCell className="text-right text-xs">
                      {item.estimated_payoff_date ? formatDate(item.estimated_payoff_date) : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>

        {excluded_liabilities && excluded_liabilities.count > 0 ? (
          <p className="text-xs text-muted-foreground">
            Excluded paid-off / non-balance liabilities ({String(excluded_liabilities.count)}):{" "}
            {excludedNames.join(", ")} ({formatMoney(excluded_liabilities.total_balance, currency)})
          </p>
        ) : null}

        {simulation && simulationTrajectory.length > 0 ? (
          <div className="space-y-4">
            <TrajectorySvgChart trajectory={simulationTrajectory} currency={simulation.currency} />
            <div className="rounded-lg border border-border bg-card">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
                <h3 className="text-sm font-semibold">Simulated Monthly Payoff Schedule</h3>
                {simulationTrajectory.length > 24 ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setShowAllMonths((prev) => !prev);
                    }}
                  >
                    {showAllMonths
                      ? "Show first 24 months"
                      : `Show all ${String(simulationTrajectory.length)} months`}
                  </Button>
                ) : null}
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Month</TableHead>
                    <TableHead className="text-right">Baseline Debt</TableHead>
                    <TableHead className="text-right">Accelerated Debt</TableHead>
                    <TableHead className="text-right">Interest Paid</TableHead>
                    <TableHead className="text-right">Extra Applied</TableHead>
                    <TableHead>Events</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibleTrajectory.map((point) => (
                    <TableRow key={point.month}>
                      <TableCell className="font-medium">{point.month}</TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {formatMoney(point.baseline_total_debt, simulation.currency)}
                      </TableCell>
                      <TableCell className="text-right font-medium tabular-nums">
                        {formatMoney(point.accelerated_total_debt, simulation.currency)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatMoney(point.interest_paid, simulation.currency)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {formatMoney(point.extra_applied, simulation.currency)}
                      </TableCell>
                      <TableCell>
                        <div className="flex flex-wrap gap-1">
                          {(point.events ?? []).map((evt, idx) => (
                            <span
                              key={`${evt}-${String(idx)}`}
                              className="rounded bg-primary/10 px-1.5 py-0.5 text-xs font-medium text-primary"
                            >
                              {evt}
                            </span>
                          ))}
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function TrajectorySvgChart({
  trajectory,
  currency,
}: {
  trajectory: DebtTrajectoryPoint[];
  currency: string;
}) {
  const maxDebt = Math.max(
    1,
    ...trajectory.map((point) => Math.max(point.baseline_total_debt, point.accelerated_total_debt)),
  );
  const width = 620;
  const height = 180;
  const padX = 16;
  const padY = 16;
  const plotW = width - padX * 2;
  const plotH = height - padY * 2;

  const toCoords = (selector: (point: DebtTrajectoryPoint) => number): string => {
    const first = trajectory[0];
    if (!first) {
      return "";
    }
    if (trajectory.length === 1) {
      const y = padY + plotH - (selector(first) / maxDebt) * plotH;
      return `${String(padX)},${y.toFixed(1)} ${String(padX + plotW)},${y.toFixed(1)}`;
    }
    return trajectory
      .map((point, index) => {
        const x = padX + (index / (trajectory.length - 1)) * plotW;
        const y = padY + plotH - (selector(point) / maxDebt) * plotH;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(" ");
  };

  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Baseline vs. Accelerated Debt Trajectory</h3>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span>
            <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-muted-foreground" />
            Baseline
          </span>
          <span>
            <span className="mr-1.5 inline-block h-2 w-2 rounded-full bg-emerald-500" />
            Accelerated ({currency})
          </span>
        </div>
      </div>
      <svg
        role="img"
        aria-label="Baseline vs accelerated debt payoff trajectory chart"
        viewBox={`0 0 ${String(width)} ${String(height)}`}
        className="h-auto w-full"
      >
        <title>Baseline vs. Accelerated Debt Trajectory ({currency})</title>
        <polyline
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeDasharray="4 3"
          className="text-muted-foreground"
          points={toCoords((point) => point.baseline_total_debt)}
        />
        <polyline
          fill="none"
          stroke="#10b981"
          strokeWidth="2.5"
          points={toCoords((point) => point.accelerated_total_debt)}
        />
      </svg>
    </div>
  );
}
