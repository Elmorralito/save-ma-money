import type { FormEvent } from "react";

import type { SpendingGroupBy } from "@/api/reports";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { presetReportWindowDates, type ReportWindowPreset } from "@/lib/reportWindow";

export type ReportFilterValues = {
  startDate: string;
  endDate: string;
  accountId: string;
  currency: string;
  groupBy: SpendingGroupBy;
};

export type AccountOption = {
  id: string;
  name: string;
};

type ReportFiltersProps = {
  value: ReportFilterValues;
  onChange: (next: ReportFilterValues) => void;
  onSubmit: () => void;
  onApplyPreset?: (next: ReportFilterValues) => void;
  accounts: readonly AccountOption[];
  availableCurrencies?: readonly string[];
  showGroupBy?: boolean;
  maxDays: number | null;
  windowError: string | null;
  isSubmitting?: boolean;
};

const PRESETS: ReadonlyArray<{ id: ReportWindowPreset; label: string }> = [
  { id: "this_month", label: "This month" },
  { id: "last_3_months", label: "Last 3 months" },
  { id: "ytd", label: "YTD" },
  { id: "last_12_months", label: "Last 12 months" },
];

/** Shared date / currency / account / group_by filters for report GETs (presentation only). */
export function ReportFilters({
  value,
  onChange,
  onSubmit,
  onApplyPreset,
  accounts,
  availableCurrencies = [],
  showGroupBy = true,
  maxDays,
  windowError,
  isSubmitting = false,
}: ReportFiltersProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    onSubmit();
  }

  function applyPreset(preset: ReportWindowPreset): void {
    const dates = presetReportWindowDates(preset);
    const next: ReportFilterValues = { ...value, ...dates };
    onChange(next);
    onApplyPreset?.(next);
  }

  return (
    <form
      className="space-y-4 rounded-lg border border-border bg-card p-4 text-card-foreground"
      onSubmit={handleSubmit}
      noValidate
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Filters</h2>
          <p className="text-xs text-muted-foreground">
            Windows are validated against the API client-contract
            {typeof maxDays === "number" ? ` (max ${String(maxDays)} days)` : ""}.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap gap-1" role="group" aria-label="Quick date presets">
            {PRESETS.map((preset) => (
              <Button
                key={preset.id}
                type="button"
                size="sm"
                variant="outline"
                onClick={() => {
                  applyPreset(preset.id);
                }}
              >
                {preset.label}
              </Button>
            ))}
          </div>
          <Button type="submit" disabled={isSubmitting || windowError !== null}>
            Run report
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <div className="space-y-1.5">
          <Label htmlFor="report-start-date">Start date</Label>
          <Input
            id="report-start-date"
            type="date"
            required
            value={value.startDate}
            onChange={(event) => {
              onChange({ ...value, startDate: event.target.value });
            }}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="report-end-date">End date</Label>
          <Input
            id="report-end-date"
            type="date"
            required
            value={value.endDate}
            onChange={(event) => {
              onChange({ ...value, endDate: event.target.value });
            }}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="report-currency">Currency</Label>
          <NativeSelect
            id="report-currency"
            value={value.currency}
            onChange={(event) => {
              onChange({ ...value, currency: event.target.value });
            }}
          >
            <option value="">Auto (dominant)</option>
            {availableCurrencies.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="report-account">Account</Label>
          <NativeSelect
            id="report-account"
            value={value.accountId}
            onChange={(event) => {
              onChange({ ...value, accountId: event.target.value });
            }}
          >
            <option value="">All accounts</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </NativeSelect>
        </div>
        {showGroupBy ? (
          <div className="space-y-1.5">
            <Label htmlFor="report-group-by">Group by</Label>
            <NativeSelect
              id="report-group-by"
              value={value.groupBy}
              onChange={(event) => {
                const next = event.target.value === "account" ? "account" : "category";
                onChange({ ...value, groupBy: next });
              }}
            >
              <option value="category">Category</option>
              <option value="account">Account</option>
            </NativeSelect>
          </div>
        ) : null}
      </div>

      {windowError ? (
        <p className="text-sm text-destructive" role="alert">
          {windowError}
        </p>
      ) : null}
    </form>
  );
}
