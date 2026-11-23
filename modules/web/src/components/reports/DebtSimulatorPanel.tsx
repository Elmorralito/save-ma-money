import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import type {
  DebtLiquidityContext,
  DebtPaydownSimulationRequest,
  DebtPaydownSimulationResponse,
  PeriodicLumpSumInput,
} from "@/types/domain";

type DebtSimulatorPanelProps = {
  currency: string;
  liquidityContext: DebtLiquidityContext;
  simulation?: DebtPaydownSimulationResponse;
  isSimulating: boolean;
  errorMessage: string | null;
  onSimulate: (request: DebtPaydownSimulationRequest) => void;
};

const GUARDRAIL_CLASSES: Record<"safe" | "caution" | "warning", string> = {
  safe: "border-emerald-500/40 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300",
  caution: "border-amber-500/40 bg-amber-500/10 text-amber-800 dark:text-amber-300",
  warning: "border-destructive/50 bg-destructive/10 text-destructive",
};

const MONTH_OPTIONS = [
  { value: 1, label: "Jan" },
  { value: 2, label: "Feb" },
  { value: 3, label: "Mar" },
  { value: 4, label: "Apr" },
  { value: 5, label: "May" },
  { value: 6, label: "Jun" },
  { value: 7, label: "Jul" },
  { value: 8, label: "Aug" },
  { value: 9, label: "Sep" },
  { value: 10, label: "Oct" },
  { value: 11, label: "Nov" },
  { value: 12, label: "Dec" },
];

/** Sticky sidebar controls & API guardrail display for What-If debt prepayment simulation. */
export function DebtSimulatorPanel({
  currency,
  liquidityContext,
  simulation,
  isSimulating,
  errorMessage,
  onSimulate,
}: DebtSimulatorPanelProps) {
  const [strategy, setStrategy] = useState<"avalanche" | "snowball">("avalanche");
  const [extraMonthly, setExtraMonthly] = useState("0");
  const [lumpSum, setLumpSum] = useState("0");
  const [lumpOffset, setLumpOffset] = useState("1");
  const [targetRunway, setTargetRunway] = useState(
    String(liquidityContext.target_liquidity_months ?? 4),
  );
  const [horizonMonths, setHorizonMonths] = useState("60");
  const [periodicLumps, setPeriodicLumps] = useState<PeriodicLumpSumInput[]>([]);

  function parseNonNegative(raw: string): number {
    const num = Number(raw);
    return Number.isFinite(num) && num >= 0 ? num : 0;
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    const offset = Math.min(120, Math.max(1, Math.trunc(Number(lumpOffset) || 1)));
    const runway = Math.min(24, Math.max(0, parseNonNegative(targetRunway)));
    const horizon = Math.min(360, Math.max(1, Math.trunc(Number(horizonMonths) || 60)));
    onSimulate({
      currency,
      strategy,
      extra_monthly_prepayment: parseNonNegative(extraMonthly),
      lump_sum_prepayment: parseNonNegative(lumpSum),
      lump_sum_month_offset: offset,
      periodic_lump_sums: periodicLumps.filter((item) => item.amount > 0),
      target_liquidity_months: runway,
      horizon_months: horizon,
    });
  }

  return (
    <aside className="space-y-4 rounded-lg border border-border bg-card p-4 lg:sticky lg:top-6 lg:self-start">
      <div>
        <h3 className="text-sm font-semibold">Prepayment Simulator</h3>
        <p className="text-xs text-muted-foreground">
          All amortization math & runway guardrails are calculated by the backend.
        </p>
      </div>

      <div className="rounded-md bg-muted/50 p-3 text-xs">
        <div className="flex justify-between">
          <span className="text-muted-foreground">Liquid cash</span>
          <span className="font-medium tabular-nums">
            {formatMoney(liquidityContext.liquid_cash_total, currency)}
          </span>
        </div>
        <div className="mt-1 flex justify-between">
          <span className="text-muted-foreground">Safe lump-sum headroom</span>
          <span className="font-medium tabular-nums">
            {formatMoney(liquidityContext.safe_lump_sum_headroom, currency)}
          </span>
        </div>
      </div>

      <form className="space-y-3" onSubmit={handleSubmit}>
        <div className="space-y-1">
          <Label htmlFor="sim-strategy">Paydown strategy</Label>
          <NativeSelect
            id="sim-strategy"
            value={strategy}
            onChange={(event) => {
              setStrategy(event.target.value === "snowball" ? "snowball" : "avalanche");
            }}
          >
            <option value="avalanche">Avalanche (highest EA rate first)</option>
            <option value="snowball">Snowball (lowest balance first)</option>
          </NativeSelect>
        </div>

        <div className="space-y-1">
          <Label htmlFor="sim-extra-monthly">Extra monthly prepayment ({currency})</Label>
          <Input
            id="sim-extra-monthly"
            type="number"
            min={0}
            step="any"
            value={extraMonthly}
            onChange={(event) => {
              setExtraMonthly(event.target.value);
            }}
          />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label htmlFor="sim-lump-sum">One-off lump sum</Label>
            <Input
              id="sim-lump-sum"
              type="number"
              min={0}
              step="any"
              value={lumpSum}
              onChange={(event) => {
                setLumpSum(event.target.value);
              }}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="sim-lump-offset">Apply in month #</Label>
            <Input
              id="sim-lump-offset"
              type="number"
              min={1}
              max={120}
              value={lumpOffset}
              onChange={(event) => {
                setLumpOffset(event.target.value);
              }}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label htmlFor="sim-runway">Target runway (mos)</Label>
            <Input
              id="sim-runway"
              type="number"
              min={0}
              max={24}
              step="0.5"
              value={targetRunway}
              onChange={(event) => {
                setTargetRunway(event.target.value);
              }}
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="sim-horizon">Horizon (mos)</Label>
            <Input
              id="sim-horizon"
              type="number"
              min={1}
              max={360}
              value={horizonMonths}
              onChange={(event) => {
                setHorizonMonths(event.target.value);
              }}
            />
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium">Periodic annual lump sums</span>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => {
                if (periodicLumps.length < 12) {
                  setPeriodicLumps([...periodicLumps, { month_of_year: 6, amount: 0 }]);
                }
              }}
            >
              + Add month
            </Button>
          </div>
          {periodicLumps.map((entry, idx) => (
            <div key={String(idx)} className="flex items-center gap-2">
              <NativeSelect
                aria-label={`Periodic bonus month ${String(idx + 1)}`}
                value={String(entry.month_of_year)}
                onChange={(event) => {
                  const next = [...periodicLumps];
                  next[idx] = { ...entry, month_of_year: Number(event.target.value) };
                  setPeriodicLumps(next);
                }}
              >
                {MONTH_OPTIONS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label}
                  </option>
                ))}
              </NativeSelect>
              <Input
                aria-label={`Periodic bonus amount ${String(idx + 1)}`}
                type="number"
                min={0}
                step="any"
                value={String(entry.amount)}
                onChange={(event) => {
                  const next = [...periodicLumps];
                  next[idx] = { ...entry, amount: parseNonNegative(event.target.value) };
                  setPeriodicLumps(next);
                }}
              />
              <Button
                type="button"
                size="sm"
                variant="ghost"
                aria-label={`Remove periodic bonus ${String(idx + 1)}`}
                onClick={() => {
                  setPeriodicLumps(periodicLumps.filter((_, i) => i !== idx));
                }}
              >
                ×
              </Button>
            </div>
          ))}
        </div>

        <Button type="submit" className="w-full" disabled={isSimulating}>
          {isSimulating ? "Simulating…" : "Simulate paydown"}
        </Button>
      </form>

      {errorMessage ? (
        <p className="text-xs text-destructive" role="alert">
          {errorMessage}
        </p>
      ) : null}

      {simulation ? (
        <div className="space-y-3 border-t border-border pt-3">
          <div
            role="status"
            className={`rounded-md border p-2.5 text-xs ${GUARDRAIL_CLASSES[simulation.liquidity_guardrail.status]}`}
          >
            {simulation.liquidity_guardrail.message}
          </div>
          <dl className="space-y-1 text-xs">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Interest saved</dt>
              <dd className="font-semibold text-emerald-700 dark:text-emerald-400 tabular-nums">
                {formatMoney(simulation.total_interest_saved, simulation.currency)}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Months saved</dt>
              <dd className="font-semibold tabular-nums">
                {simulation.months_saved !== null && simulation.months_saved !== undefined
                  ? `${String(simulation.months_saved)} mo(s)`
                  : "—"}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Accelerated payoff</dt>
              <dd className="font-medium">
                {simulation.accelerated_payoff_date
                  ? formatDate(simulation.accelerated_payoff_date)
                  : "Beyond horizon"}
              </dd>
            </div>
          </dl>
        </div>
      ) : null}
    </aside>
  );
}
