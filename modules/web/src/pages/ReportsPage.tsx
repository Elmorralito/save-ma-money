import { useMutation, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  Calculator,
  CheckCircle2,
  ChevronDown,
  Flame,
  PieChart,
  RefreshCw,
  Scale,
  SlidersHorizontal,
  type LucideIcon,
} from "lucide-react";
import { useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  accountsListQueryOptions,
  clientContractQueryOptions,
  debtPaydownReportQueryOptions,
  operatingCashflowReportQueryOptions,
  plannedVsActualReportQueryOptions,
  reportWindowMaxDays,
  simulateDebtPaydown,
  spendingReportQueryOptions,
} from "@/api";
import { getAIConfig } from "@/api/ai";
import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import { QueryState } from "@/components/QueryState";
import { CashflowWaterfallView } from "@/components/reports/CashflowWaterfallView";
import { DebtPaydownView } from "@/components/reports/DebtPaydownView";
import { KpiSummaryStrip, type ReportTabId } from "@/components/reports/KpiSummaryStrip";
import { PlannedVsActualView } from "@/components/reports/PlannedVsActualView";
import { ReportFilters, type ReportFilterValues } from "@/components/reports/ReportFilters";
import { SpendingReportView } from "@/components/reports/SpendingReportView";
import { Button } from "@/components/ui/button";
import { useLocale } from "@/i18n/LocaleProvider";
import { formatApiError } from "@/lib/formatApiError";
import { formatMoney } from "@/lib/formatMoney";
import { defaultReportWindowDates, validateReportWindow } from "@/lib/reportWindow";
import { cn } from "@/lib/utils";
import type { DebtPaydownSimulationRequest } from "@/types/domain";

const ACCOUNT_LIST_PARAMS = { limit: 100, skip: 0, is_active: true } as const;

type ReportTab = ReportTabId;

const TABS: ReadonlyArray<{ id: ReportTab; label: string; icon: LucideIcon }> = [
  { id: "waterfall", label: "Operating Cashflow", icon: BarChart3 },
  { id: "variance", label: "Planned vs. Actual", icon: Scale },
  { id: "debt", label: "Debt Paydown", icon: Flame },
  { id: "spending", label: "Spending", icon: PieChart },
];

type InsightChip = {
  id: string;
  tone: "positive" | "warning" | "negative" | "neutral";
  text: string;
  targetTab?: ReportTab;
  to?: string;
};

function resolveTab(raw: string | null): ReportTab {
  if (raw === "variance" || raw === "debt" || raw === "spending") {
    return raw;
  }
  return "waterfall";
}

function initialFilters(): ReportFilterValues {
  const window = defaultReportWindowDates();
  return {
    startDate: window.startDate,
    endDate: window.endDate,
    accountId: "",
    currency: "",
    groupBy: "category",
  };
}

/** Executive Reports workspace (PPT-054 + PPT-091 / #184). Zero TS domain math. */
export function ReportsPage() {
  const { locale, messages } = useLocale();
  const rt = messages.reports;
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = resolveTab(searchParams.get("tab"));

  const [draft, setDraft] = useState<ReportFilterValues>(initialFilters);
  const [applied, setApplied] = useState<ReportFilterValues>(initialFilters);
  const reportsAi = useScopedAIToggle();
  const aiConfigQuery = useQuery({
    queryKey: ["ai-config"],
    queryFn: ({ signal }) => getAIConfig(signal),
    staleTime: 60_000,
  });
  const reportsAiEnabled = aiConfigQuery.data?.reports_ai_enabled ?? true;
  const tabRefs = useRef<Partial<Record<ReportTab, HTMLButtonElement | null>>>({});

  const contractQuery = useQuery(clientContractQueryOptions());
  const accountsQuery = useQuery(accountsListQueryOptions(ACCOUNT_LIST_PARAMS));
  const maxDays = reportWindowMaxDays(contractQuery.data);

  const draftWindow = useMemo(
    () => validateReportWindow(draft.startDate, draft.endDate, maxDays),
    [draft.startDate, draft.endDate, maxDays],
  );
  const appliedWindow = useMemo(
    () => validateReportWindow(applied.startDate, applied.endDate, maxDays),
    [applied.startDate, applied.endDate, maxDays],
  );

  const currencyParam = applied.currency === "" ? null : applied.currency;
  const accountParam = applied.accountId === "" ? null : applied.accountId;

  const waterfallQuery = useQuery({
    ...operatingCashflowReportQueryOptions({
      start_date: applied.startDate,
      end_date: applied.endDate,
      currency: currencyParam,
      account_id: accountParam,
      include_monthly_series: true,
    }),
    enabled: appliedWindow.ok,
  });

  const varianceQuery = useQuery({
    ...plannedVsActualReportQueryOptions({
      start_date: applied.startDate,
      end_date: applied.endDate,
      currency: currencyParam,
      account_id: accountParam,
    }),
    enabled: appliedWindow.ok,
  });

  const debtQuery = useQuery(
    debtPaydownReportQueryOptions({
      currency: currencyParam,
      include_excluded: true,
    }),
  );

  const spendingQuery = useQuery({
    ...spendingReportQueryOptions({
      start_date: applied.startDate,
      end_date: applied.endDate,
      group_by: applied.groupBy,
      account_id: accountParam,
    }),
    enabled: appliedWindow.ok && activeTab === "spending",
  });

  const simulationMutation = useMutation({
    mutationFn: (request: DebtPaydownSimulationRequest) => simulateDebtPaydown(request),
  });

  const accounts = (accountsQuery.data?.items ?? []).map((account) => ({
    id: account.id,
    name: account.name,
  }));

  const availableCurrencies = useMemo(() => {
    const merged = new Set<string>();
    for (const c of waterfallQuery.data?.available_currencies ?? []) merged.add(c);
    for (const c of varianceQuery.data?.available_currencies ?? []) merged.add(c);
    for (const c of debtQuery.data?.available_currencies ?? []) merged.add(c);
    for (const acct of accountsQuery.data?.items ?? []) {
      if (acct.currency) merged.add(acct.currency);
    }
    return Array.from(merged).sort();
  }, [
    accountsQuery.data?.items,
    debtQuery.data?.available_currencies,
    varianceQuery.data?.available_currencies,
    waterfallQuery.data?.available_currencies,
  ]);

  const displayCurrency =
    waterfallQuery.data?.currency ??
    debtQuery.data?.currency ??
    varianceQuery.data?.currency ??
    (applied.currency || accountsQuery.data?.items?.[0]?.currency) ??
    "USD";

  const multiCurrencyWarning = Boolean(
    waterfallQuery.data?.multi_currency_warning ||
    varianceQuery.data?.multi_currency_warning ||
    debtQuery.data?.multi_currency_warning,
  );

  const isAnyFetching =
    waterfallQuery.isFetching ||
    varianceQuery.isFetching ||
    debtQuery.isFetching ||
    spendingQuery.isFetching;

  // Presentation-only synthesis of API-computed diagnostics into clickable insight pills
  const insights = useMemo<InsightChip[]>(() => {
    const chips: InsightChip[] = [];
    const wf = waterfallQuery.data?.waterfall;
    if (wf) {
      if (wf.organic_fcf_margin_pct >= 20) {
        chips.push({
          id: "fcf-strong",
          tone: "positive",
          text: `${rt.strongMarginPrefix} ${wf.organic_fcf_margin_pct.toFixed(1)}${rt.strongMarginSuffix}`,
          targetTab: "waterfall",
        });
      } else if (wf.organic_fcf_margin_pct < 0) {
        chips.push({
          id: "fcf-neg",
          tone: "negative",
          text: `${rt.negCashflowPrefix}${wf.organic_fcf_margin_pct.toFixed(1)}${rt.negCashflowSuffix}`,
          targetTab: "waterfall",
        });
      }
      if (wf.debt_service_to_income_pct > 30) {
        chips.push({
          id: "debt-ratio",
          tone: "warning",
          text: `${rt.debtServicePrefix} ${wf.debt_service_to_income_pct.toFixed(1)}${rt.debtServiceSuffix}`,
          targetTab: "debt",
        });
      }
    }
    const debt = debtQuery.data;
    if (debt && debt.summary.active_liability_count > 0) {
      chips.push({
        id: "debt-drag",
        tone: debt.summary.weighted_average_ea_pct >= 18 ? "negative" : "warning",
        text: `${debt.summary.highest_rate_account_name ?? rt.topLiabilityFallback} ${rt.debtDragInfix} ${formatMoney(debt.summary.total_monthly_interest_drag, debt.currency)}${rt.debtDragSuffix}`,
        to: "/projections",
      });
    }
    const vr = varianceQuery.data?.summary;
    if (vr && vr.reconciliation_flag_count > 0) {
      chips.push({
        id: "variance-flags",
        tone: "warning",
        text: `${String(vr.reconciliation_flag_count)} ${rt.varianceAlertsSuffix}`,
        targetTab: "variance",
      });
    }
    return chips;
  }, [debtQuery.data, rt, varianceQuery.data?.summary, waterfallQuery.data?.waterfall]);

  function selectTab(tab: ReportTab): void {
    const next = new URLSearchParams(searchParams);
    next.set("tab", tab);
    setSearchParams(next, { replace: true });
  }

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number): void {
    let targetIndex: number | null = null;
    if (event.key === "ArrowRight") {
      targetIndex = (index + 1) % TABS.length;
    } else if (event.key === "ArrowLeft") {
      targetIndex = (index - 1 + TABS.length) % TABS.length;
    } else if (event.key === "Home") {
      targetIndex = 0;
    } else if (event.key === "End") {
      targetIndex = TABS.length - 1;
    }
    if (targetIndex === null) {
      return;
    }
    event.preventDefault();
    const nextTab = TABS[targetIndex];
    if (!nextTab) {
      return;
    }
    selectTab(nextTab.id);
    tabRefs.current[nextTab.id]?.focus();
  }

  function applyFilterValues(next: ReportFilterValues): void {
    if (next.currency !== applied.currency) {
      simulationMutation.reset();
    }
    setApplied({ ...next });
  }

  function refreshAll(): void {
    void waterfallQuery.refetch();
    void varianceQuery.refetch();
    void debtQuery.refetch();
    if (activeTab === "spending") void spendingQuery.refetch();
  }

  const kpiNode = (
    <KpiSummaryStrip
      currency={displayCurrency}
      waterfall={waterfallQuery.data}
      variance={varianceQuery.data}
      debt={debtQuery.data}
      activeTab={activeTab}
      onSelectTab={selectTab}
    />
  );

  const insightsNode =
    insights.length > 0 ? (
      <div aria-label={rt.insightsLabel} className="flex flex-wrap items-center gap-2">
        {insights.map((chip) => {
          const toneClass =
            chip.tone === "positive"
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-800 hover:bg-emerald-500/15 dark:text-emerald-200"
              : chip.tone === "negative"
                ? "border-rose-500/30 bg-rose-500/10 text-rose-800 hover:bg-rose-500/15 dark:text-rose-200"
                : "border-amber-500/30 bg-amber-500/10 text-amber-800 hover:bg-amber-500/15 dark:text-amber-200";
          const Icon = chip.tone === "positive" ? CheckCircle2 : AlertTriangle;
          if (chip.to) {
            return (
              <Link
                key={chip.id}
                to={chip.to}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                  toneClass,
                )}
              >
                <Icon className="size-3.5 shrink-0" />
                <span>{chip.text}</span>
                <ArrowUpRight className="size-3 shrink-0 opacity-75" />
              </Link>
            );
          }
          return (
            <button
              key={chip.id}
              type="button"
              onClick={() => chip.targetTab && selectTab(chip.targetTab)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors",
                toneClass,
              )}
            >
              <Icon className="size-3.5 shrink-0" />
              <span>{chip.text}</span>
            </button>
          );
        })}
      </div>
    ) : null;

  const filtersNode = (
    <ReportFilters
      value={draft}
      onChange={setDraft}
      onSubmit={() => {
        if (!draftWindow.ok) {
          return;
        }
        applyFilterValues(draft);
      }}
      onApplyPreset={(next) => {
        const check = validateReportWindow(next.startDate, next.endDate, maxDays);
        if (check.ok) {
          applyFilterValues(next);
        }
      }}
      accounts={accounts}
      availableCurrencies={availableCurrencies}
      showGroupBy={activeTab === "spending"}
      maxDays={maxDays}
      windowError={draftWindow.ok ? null : draftWindow.message}
      isSubmitting={isAnyFetching}
    />
  );

  const currencyWarningNode = multiCurrencyWarning ? (
    <div
      role="status"
      className="rounded-xl border border-amber-500/35 bg-amber-500/10 px-4 py-3 text-xs text-amber-800 dark:text-amber-200"
    >
      {rt.multiCurrencyPrefix} ({availableCurrencies.join(", ")}). {rt.multiCurrencyMiddle}{" "}
      <strong>{displayCurrency}</strong>; {rt.multiCurrencySuffix}
    </div>
  ) : null;

  const tabsNode = (
    <div
      role="tablist"
      aria-label="Report views"
      className="flex flex-wrap gap-1.5 rounded-xl border border-border bg-card p-1.5"
    >
      {TABS.map((tab, index) => {
        const selected = activeTab === tab.id;
        const TabIcon = tab.icon;
        const badgeCount =
          tab.id === "variance"
            ? (varianceQuery.data?.summary.reconciliation_flag_count ?? 0)
            : tab.id === "debt"
              ? (debtQuery.data?.summary.active_liability_count ?? 0)
              : 0;
        return (
          <button
            key={tab.id}
            ref={(el) => {
              tabRefs.current[tab.id] = el;
            }}
            type="button"
            role="tab"
            id={`tab-${tab.id}`}
            tabIndex={selected ? 0 : -1}
            aria-selected={selected}
            aria-controls={`panel-${tab.id}`}
            onClick={() => {
              selectTab(tab.id);
            }}
            onKeyDown={(event) => {
              handleTabKeyDown(event, index);
            }}
            className={cn(
              "inline-flex items-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition-all duration-150",
              selected
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            <TabIcon aria-hidden="true" className="size-4" />
            <span>{rt.tabs[tab.id] ?? tab.label}</span>
            {badgeCount > 0 ? (
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 text-[10px] font-semibold tabular-nums",
                  selected
                    ? "bg-primary-foreground/20 text-primary-foreground"
                    : "bg-muted-foreground/15 text-foreground",
                )}
              >
                {String(badgeCount)}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );

  const panelsNode = (
    <>
      {activeTab === "waterfall" ? (
        <section
          role="tabpanel"
          id="panel-waterfall"
          aria-labelledby="tab-waterfall"
          aria-label="Operating cashflow waterfall"
          className="space-y-3 animate-in fade-in-0 duration-200"
        >
          {!appliedWindow.ok ? (
            <p className="text-sm text-muted-foreground" role="status">
              {rt.fixDateWindow}
            </p>
          ) : (
            <QueryState
              isPending={waterfallQuery.isPending}
              isError={waterfallQuery.isError}
              error={waterfallQuery.error}
              isEmpty={false}
              emptyTitle={rt.noReport}
              onRetry={() => {
                void waterfallQuery.refetch();
              }}
            >
              {waterfallQuery.data ? <CashflowWaterfallView report={waterfallQuery.data} /> : null}
            </QueryState>
          )}
        </section>
      ) : null}

      {activeTab === "variance" ? (
        <section
          role="tabpanel"
          id="panel-variance"
          aria-labelledby="tab-variance"
          aria-label="Planned vs actual variance"
          className="space-y-3 animate-in fade-in-0 duration-200"
        >
          {!appliedWindow.ok ? (
            <p className="text-sm text-muted-foreground" role="status">
              {rt.fixDateWindow}
            </p>
          ) : (
            <QueryState
              isPending={varianceQuery.isPending}
              isError={varianceQuery.isError}
              error={varianceQuery.error}
              isEmpty={false}
              emptyTitle={rt.noReport}
              onRetry={() => {
                void varianceQuery.refetch();
              }}
            >
              {varianceQuery.data ? <PlannedVsActualView report={varianceQuery.data} /> : null}
            </QueryState>
          )}
        </section>
      ) : null}

      {activeTab === "debt" ? (
        <section
          role="tabpanel"
          id="panel-debt"
          aria-labelledby="tab-debt"
          aria-label="Debt paydown and simulator"
          className="space-y-3 animate-in fade-in-0 duration-200"
        >
          <QueryState
            isPending={debtQuery.isPending}
            isError={debtQuery.isError}
            error={debtQuery.error}
            isEmpty={false}
            emptyTitle={rt.noDebtReport}
            onRetry={() => {
              void debtQuery.refetch();
            }}
          >
            {debtQuery.data ? (
              <DebtPaydownView
                report={debtQuery.data}
                simulation={simulationMutation.data}
                isSimulating={simulationMutation.isPending}
                simulationError={
                  simulationMutation.isError
                    ? formatApiError(simulationMutation.error, rt.simulationError)
                    : null
                }
                onSimulate={(request) => {
                  simulationMutation.mutate(request);
                }}
              />
            ) : null}
          </QueryState>
        </section>
      ) : null}

      {activeTab === "spending" ? (
        <section
          role="tabpanel"
          id="panel-spending"
          aria-labelledby="tab-spending"
          aria-label="Spending breakdown"
          className="space-y-3 animate-in fade-in-0 duration-200"
        >
          {!appliedWindow.ok ? (
            <p className="text-sm text-muted-foreground" role="status">
              {rt.fixDateWindow}
            </p>
          ) : (
            <QueryState
              isPending={spendingQuery.isPending}
              isError={spendingQuery.isError}
              error={spendingQuery.error}
              isEmpty={false}
              emptyTitle={rt.noSpendingReport}
              onRetry={() => {
                void spendingQuery.refetch();
              }}
            >
              {spendingQuery.data ? (
                <SpendingReportView report={spendingQuery.data} currency={displayCurrency} />
              ) : null}
            </QueryState>
          )}
        </section>
      ) : null}
    </>
  );

  const collapsibleFilters = (
    <details className="group rounded-2xl border border-border bg-card shadow-xs">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-medium transition-colors hover:bg-muted/40 [&::-webkit-details-marker]:hidden">
        <span className="inline-flex items-center gap-2.5">
          <SlidersHorizontal aria-hidden="true" className="size-4 text-primary" />
          <span>{rt.filters.title}</span>
          <span className="rounded-full bg-muted px-2.5 py-0.5 text-xs font-normal tabular-nums text-muted-foreground">
            {applied.startDate} → {applied.endDate} · {displayCurrency}
          </span>
        </span>
        <ChevronDown
          aria-hidden="true"
          className="size-4 text-muted-foreground transition-transform duration-200 group-open:rotate-180"
        />
      </summary>
      <div className="border-t border-border p-1 [&>form]:border-0 [&>form]:shadow-none">
        {filtersNode}
      </div>
    </details>
  );

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-5">
      <header className="relative overflow-hidden rounded-2xl bg-[#04090c] p-5 text-white">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-20 -right-16 size-60 rounded-full bg-emerald-500/18 blur-3xl"
        />
        <div className="relative flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-semibold tracking-tight text-white text-balance">
                {rt.title}
              </h1>
              <span className="rounded-full bg-white/10 px-2.5 py-0.5 text-xs font-medium tabular-nums text-slate-200">
                {applied.startDate} → {applied.endDate} · {displayCurrency}
              </span>
            </div>
            <p className="max-w-2xl text-sm text-slate-300 text-pretty">{rt.subtitle}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {reportsAiEnabled ? (
              <ScopedAITrigger
                open={reportsAi.open}
                panelId={reportsAi.panelId}
                onToggle={reportsAi.toggle}
                compact={false}
                tone="dark"
              />
            ) : null}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={refreshAll}
              disabled={isAnyFetching}
              className="border-white/20 bg-white/[0.06] text-white hover:bg-white/15 hover:text-white"
            >
              <RefreshCw className={cn("mr-1.5 size-3.5", isAnyFetching && "animate-spin")} />
              {rt.refresh}
            </Button>
            <Button
              asChild
              size="sm"
              className="bg-emerald-500 text-slate-950 hover:bg-emerald-400"
            >
              <Link to="/projections">
                <Calculator className="mr-1.5 size-3.5" />
                {rt.projectionsCta}
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <ScopedAIPanel
        id={reportsAi.panelId}
        open={reportsAiEnabled && reportsAi.open}
        onClose={reportsAi.close}
        module="reports"
        view={activeTab}
        control="reports-overview"
        title={`${rt.title} · ${rt.tabs[activeTab] ?? activeTab}`}
        currency={displayCurrency}
        surfaceContext={{
          active_tab: activeTab,
          start_date: applied.startDate,
          end_date: applied.endDate,
          currency: displayCurrency,
          account_id: accountParam,
          group_by: applied.groupBy,
          insights: insights.map((i) => i.text),
          waterfall_summary: waterfallQuery.data?.waterfall ?? null,
          variance_summary: varianceQuery.data?.summary ?? null,
          debt_summary: debtQuery.data?.summary ?? null,
          spending_totals: spendingQuery.data
            ? {
                total_spending: spendingQuery.data.total_spending,
                total_income: spendingQuery.data.total_income,
                net_savings: spendingQuery.data.net_savings,
              }
            : null,
        }}
        suggestedPrompts={
          locale === "es-CO"
            ? [
                "Resume los hallazgos clave de mis reportes para este período.",
                "¿Qué anomalía o riesgo financiero merece acción inmediata?",
                "Conecta mi flujo operativo, variación presupuestal y costo de deuda.",
              ]
            : [
                "Summarize the key takeaways across my reports for this window.",
                "What anomaly or financial risk deserves immediate action?",
                "Connect my operating cashflow, budget variance, and debt drag.",
              ]
        }
      />

      {kpiNode}
      {insightsNode}
      {currencyWarningNode}
      {collapsibleFilters}
      {tabsNode}
      {panelsNode}
    </div>
  );
}
