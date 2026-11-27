import { useMemo, useState } from "react";

import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import { DebtSimulatorPanel } from "@/components/reports/DebtSimulatorPanel";
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

type LiabilitySortKey = "rank" | "name" | "balance" | "ea" | "drag" | "payment" | "payoff";
type ScheduleSortKey = "month" | "baseline" | "accelerated" | "interest" | "extra";

/** 2-column presentation-only Debt Interest-Drag & Backend Prepayment Simulator workspace. */
export function DebtPaydownView({
  report,
  simulation,
  isSimulating,
  simulationError,
  onSimulate,
}: DebtPaydownViewProps) {
  const { locale } = useLocale();
  const liabilitiesAi = useScopedAIToggle();
  const scheduleAi = useScopedAIToggle();
  const [showAllMonths, setShowAllMonths] = useState(false);
  const [liabilitySearch, setLiabilitySearch] = useState("");
  const [liabilitySort, setLiabilitySort] = useState<SortState<LiabilitySortKey>>({
    key: "rank",
    direction: "asc",
  });
  const [scheduleSearch, setScheduleSearch] = useState("");
  const [eventsOnly, setEventsOnly] = useState(false);
  const [scheduleSort, setScheduleSort] = useState<SortState<ScheduleSortKey>>({
    key: "month",
    direction: "asc",
  });
  const { summary, liquidity_context, excluded_liabilities, currency } = report;
  const liabilities = useMemo(() => report.liabilities ?? [], [report.liabilities]);
  const excludedNames = excluded_liabilities?.account_names ?? [];
  const simulationTrajectory = useMemo(
    () => simulation?.monthly_trajectory ?? [],
    [simulation?.monthly_trajectory],
  );

  const visibleLiabilities = useMemo(() => {
    const q = liabilitySearch.trim().toLowerCase();
    const filtered = q
      ? liabilities.filter(
          (item) =>
            item.account_name.toLowerCase().includes(q) ||
            formatSlugLabel(item.account_kind).toLowerCase().includes(q) ||
            (item.linked_asset?.asset_name.toLowerCase().includes(q) ?? false),
        )
      : liabilities;
    return sortItems(filtered, liabilitySort, {
      rank: (r) => r.priority_rank,
      name: (r) => r.account_name,
      balance: (r) => r.balance,
      ea: (r) => r.effective_annual_rate_pct,
      drag: (r) => r.monthly_interest_drag,
      payment: (r) => r.monthly_contractual_payment,
      payoff: (r) => r.estimated_payoff_date ?? "",
    });
  }, [liabilities, liabilitySearch, liabilitySort]);

  const filteredTrajectory = useMemo(() => {
    const q = scheduleSearch.trim().toLowerCase();
    const filtered = simulationTrajectory.filter((point) => {
      if (eventsOnly && (point.events?.length ?? 0) === 0) return false;
      if (!q) return true;
      const evtMatch = (point.events ?? []).some((evt) => evt.toLowerCase().includes(q));
      return String(point.month).toLowerCase().includes(q) || evtMatch;
    });
    return sortItems(filtered, scheduleSort, {
      month: (r) => r.month,
      baseline: (r) => r.baseline_total_debt,
      accelerated: (r) => r.accelerated_total_debt,
      interest: (r) => r.interest_paid,
      extra: (r) => r.extra_applied,
    });
  }, [eventsOnly, scheduleSearch, scheduleSort, simulationTrajectory]);

  const visibleTrajectory = showAllMonths ? filteredTrajectory : filteredTrajectory.slice(0, 24);

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
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3">
            <h3 className="text-sm font-semibold">Priority Liability Ranking (Highest EA First)</h3>
            <div className="flex flex-wrap items-center gap-2">
              {liabilities.length > 0 ? (
                <Input
                  aria-label="Filter liabilities"
                  placeholder="Filter liabilities…"
                  className="h-8 w-44 text-xs"
                  value={liabilitySearch}
                  onChange={(event) => {
                    setLiabilitySearch(event.target.value);
                  }}
                />
              ) : null}
              <ScopedAITrigger
                open={liabilitiesAi.open}
                panelId={liabilitiesAi.panelId}
                onToggle={liabilitiesAi.toggle}
              />
            </div>
          </div>
          <ScopedAIPanel
            id={liabilitiesAi.panelId}
            open={liabilitiesAi.open}
            onClose={liabilitiesAi.close}
            module="reports"
            view="debt"
            control="liability-ranking-table"
            title="Priority Liability Ranking"
            currency={currency}
            className="m-3"
            surfaceContext={{
              currency,
              total_debt: summary.total_debt,
              total_monthly_interest_drag: summary.total_monthly_interest_drag,
              weighted_average_ea_pct: summary.weighted_average_ea_pct,
              search: liabilitySearch || null,
              sort: liabilitySort,
              liabilities: visibleLiabilities.map((l) => ({
                rank: l.priority_rank,
                name: l.account_name,
                kind: l.account_kind,
                balance: l.balance,
                ea_pct: l.effective_annual_rate_pct,
                monthly_drag: l.monthly_interest_drag,
                monthly_payment: l.monthly_contractual_payment,
                payoff_date: l.estimated_payoff_date,
                negative_amortization: l.negative_amortization,
              })),
            }}
            suggestedPrompts={
              locale === "es-CO"
                ? [
                    "¿Qué obligación genera mayor costo en intereses y debo atacar primero?",
                    "¿Alguna deuda presenta amortización negativa o tasa crítica?",
                  ]
                : [
                    "Which liability causes the highest interest drag to attack first?",
                    "Are any accounts in negative amortization or carrying risky EA rates?",
                  ]
            }
          />
          {liabilities.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
              No active liabilities in {currency}.
            </div>
          ) : visibleLiabilities.length === 0 ? (
            <div className="px-4 py-6 text-center text-xs text-muted-foreground">
              No liabilities match this filter.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <SortableTableHead
                    label="#"
                    sortKey="rank"
                    sort={liabilitySort}
                    onSort={(key) => {
                      setLiabilitySort((prev) => toggleSort(prev, key, "asc"));
                    }}
                  />
                  <SortableTableHead
                    label="Liability"
                    sortKey="name"
                    sort={liabilitySort}
                    onSort={(key) => {
                      setLiabilitySort((prev) => toggleSort(prev, key, "asc"));
                    }}
                  />
                  <SortableTableHead
                    label="Balance"
                    sortKey="balance"
                    sort={liabilitySort}
                    onSort={(key) => {
                      setLiabilitySort((prev) => toggleSort(prev, key, "desc"));
                    }}
                    align="right"
                  />
                  <SortableTableHead
                    label="EA / Monthly"
                    sortKey="ea"
                    sort={liabilitySort}
                    onSort={(key) => {
                      setLiabilitySort((prev) => toggleSort(prev, key, "desc"));
                    }}
                    align="right"
                  />
                  <SortableTableHead
                    label="Interest Drag"
                    sortKey="drag"
                    sort={liabilitySort}
                    onSort={(key) => {
                      setLiabilitySort((prev) => toggleSort(prev, key, "desc"));
                    }}
                    align="right"
                  />
                  <SortableTableHead
                    label="Payment / Extras"
                    sortKey="payment"
                    sort={liabilitySort}
                    onSort={(key) => {
                      setLiabilitySort((prev) => toggleSort(prev, key, "desc"));
                    }}
                    align="right"
                  />
                  <SortableTableHead
                    label="Est. Payoff"
                    sortKey="payoff"
                    sort={liabilitySort}
                    onSort={(key) => {
                      setLiabilitySort((prev) => toggleSort(prev, key, "asc"));
                    }}
                    align="right"
                  />
                </TableRow>
              </TableHeader>
              <TableBody>
                {visibleLiabilities.map((item) => (
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
                <div className="flex flex-wrap items-center gap-2">
                  <Input
                    aria-label="Filter payoff schedule"
                    placeholder="Filter month or event…"
                    className="h-8 w-44 text-xs"
                    value={scheduleSearch}
                    onChange={(event) => {
                      setScheduleSearch(event.target.value);
                    }}
                  />
                  <Button
                    type="button"
                    size="sm"
                    variant={eventsOnly ? "default" : "outline"}
                    aria-pressed={eventsOnly}
                    onClick={() => {
                      setEventsOnly((prev) => !prev);
                    }}
                  >
                    Events only
                  </Button>
                  {filteredTrajectory.length > 24 ? (
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
                        : `Show all ${String(filteredTrajectory.length)} months`}
                    </Button>
                  ) : null}
                  <ScopedAITrigger
                    open={scheduleAi.open}
                    panelId={scheduleAi.panelId}
                    onToggle={scheduleAi.toggle}
                  />
                </div>
              </div>
              <ScopedAIPanel
                id={scheduleAi.panelId}
                open={scheduleAi.open}
                onClose={scheduleAi.close}
                module="reports"
                view="debt"
                control="payoff-schedule-table"
                title="Simulated Monthly Payoff Schedule"
                currency={simulation.currency}
                className="m-3"
                surfaceContext={{
                  currency: simulation.currency,
                  months_saved: simulation.months_saved,
                  total_interest_saved: simulation.total_interest_saved,
                  accelerated_payoff_date: simulation.accelerated_payoff_date ?? null,
                  search: scheduleSearch || null,
                  events_only: eventsOnly,
                  sort: scheduleSort,
                  sample_months: visibleTrajectory.slice(0, 10),
                }}
                suggestedPrompts={
                  locale === "es-CO"
                    ? [
                        "Resume cuándo quedan saldadas las deudas y cuánto interés se ahorra.",
                        "¿Qué hitos clave aparecen en este calendario simulado?",
                      ]
                    : [
                        "Summarize payoff milestones and total interest saved under this schedule.",
                        "Highlight the biggest inflection months in this accelerated plan.",
                      ]
                }
              />
              {visibleTrajectory.length === 0 ? (
                <div className="px-4 py-6 text-center text-xs text-muted-foreground">
                  No payoff months match this filter.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <SortableTableHead
                        label="Month"
                        sortKey="month"
                        sort={scheduleSort}
                        onSort={(key) => {
                          setScheduleSort((prev) => toggleSort(prev, key, "asc"));
                        }}
                      />
                      <SortableTableHead
                        label="Baseline Debt"
                        sortKey="baseline"
                        sort={scheduleSort}
                        onSort={(key) => {
                          setScheduleSort((prev) => toggleSort(prev, key, "desc"));
                        }}
                        align="right"
                      />
                      <SortableTableHead
                        label="Accelerated Debt"
                        sortKey="accelerated"
                        sort={scheduleSort}
                        onSort={(key) => {
                          setScheduleSort((prev) => toggleSort(prev, key, "desc"));
                        }}
                        align="right"
                      />
                      <SortableTableHead
                        label="Interest Paid"
                        sortKey="interest"
                        sort={scheduleSort}
                        onSort={(key) => {
                          setScheduleSort((prev) => toggleSort(prev, key, "desc"));
                        }}
                        align="right"
                      />
                      <SortableTableHead
                        label="Extra Applied"
                        sortKey="extra"
                        sort={scheduleSort}
                        onSort={(key) => {
                          setScheduleSort((prev) => toggleSort(prev, key, "desc"));
                        }}
                        align="right"
                      />
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
              )}
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
