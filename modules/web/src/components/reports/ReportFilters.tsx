import type { FormEvent } from "react";

import type { SpendingGroupBy } from "@/api/reports";
import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { useLocale } from "@/i18n/LocaleProvider";
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
  const { locale, messages } = useLocale();
  const ft = messages.reports.filters;
  const filtersAi = useScopedAIToggle();

  const presetLabels: Record<ReportWindowPreset, string> = {
    this_month: ft.thisMonth,
    last_3_months: ft.last3Months,
    ytd: ft.ytd,
    last_12_months: ft.last12Months,
  };

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
      className="space-y-4 rounded-2xl border border-border bg-card p-5 text-card-foreground shadow-xs"
      onSubmit={handleSubmit}
      noValidate
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">{ft.title}</h2>
          <p className="text-xs text-muted-foreground">
            {ft.hintPrefix}
            {typeof maxDays === "number"
              ? ` (${ft.maxDaysPrefix} ${String(maxDays)} ${ft.maxDaysSuffix})`
              : ""}
            .
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex flex-wrap gap-1" role="group" aria-label={ft.presetsLabel}>
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
                {presetLabels[preset.id] ?? preset.label}
              </Button>
            ))}
          </div>
          <Button type="submit" disabled={isSubmitting || windowError !== null}>
            {ft.runReport}
          </Button>
          <ScopedAITrigger
            open={filtersAi.open}
            panelId={filtersAi.panelId}
            onToggle={filtersAi.toggle}
          />
        </div>
      </div>

      <ScopedAIPanel
        id={filtersAi.panelId}
        open={filtersAi.open}
        onClose={filtersAi.close}
        module="reports"
        view="filters"
        control="report-filters"
        title={ft.title}
        currency={value.currency || undefined}
        surfaceContext={{
          start_date: value.startDate,
          end_date: value.endDate,
          account_id: value.accountId || null,
          currency: value.currency || null,
          group_by: showGroupBy ? value.groupBy : null,
          max_window_days: maxDays,
        }}
        suggestedPrompts={
          locale === "es-CO"
            ? [
                "¿Qué período conviene analizar según mis datos actuales?",
                "¿Cómo cambia el análisis al filtrar por moneda o cuenta específica?",
              ]
            : [
                "Which date window makes the most sense for analyzing my current trends?",
                "How does filtering by account or currency scope these metrics?",
              ]
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <div className="space-y-1.5">
          <Label htmlFor="report-start-date">{ft.startDate}</Label>
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
          <Label htmlFor="report-end-date">{ft.endDate}</Label>
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
          <Label htmlFor="report-currency">{ft.currency}</Label>
          <NativeSelect
            id="report-currency"
            value={value.currency}
            onChange={(event) => {
              onChange({ ...value, currency: event.target.value });
            }}
          >
            <option value="">{ft.autoDominant}</option>
            {availableCurrencies.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="report-account">{ft.account}</Label>
          <NativeSelect
            id="report-account"
            value={value.accountId}
            onChange={(event) => {
              onChange({ ...value, accountId: event.target.value });
            }}
          >
            <option value="">{ft.allAccounts}</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </NativeSelect>
        </div>
        {showGroupBy ? (
          <div className="space-y-1.5">
            <Label htmlFor="report-group-by">{ft.groupBy}</Label>
            <NativeSelect
              id="report-group-by"
              value={value.groupBy}
              onChange={(event) => {
                const next = event.target.value === "account" ? "account" : "category";
                onChange({ ...value, groupBy: next });
              }}
            >
              <option value="category">{ft.groupByCategory}</option>
              <option value="account">{ft.groupByAccount}</option>
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
