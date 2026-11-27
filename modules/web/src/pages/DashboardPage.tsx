import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeftRight,
  ArrowUpRight,
  BarChart3,
  CalendarClock,
  Clock,
  Landmark,
  Send,
  Tags,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { invalidateAfterTemplateWrite } from "@/api/invalidateLedger";
import {
  accountsListQueryOptions,
  financialHealthReportQueryOptions,
  latestIngestionRunQueryOptions,
  operatingCashflowReportQueryOptions,
  transactionsListQueryOptions,
  upcomingDuesQueryOptions,
} from "@/api/queries";
import { markTemplatePaid } from "@/api/transactionTemplates";
import { bffSessionQueryOptions } from "@/auth/sessionQueries";
import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import { FinancialHealthScorecard } from "@/components/home/FinancialHealthScorecard";
import { LivePulseSection } from "@/components/home/LivePulseSection";
import { APP_NAV_ITEMS } from "@/components/layout/navItems";
import { Button } from "@/components/ui/button";
import { useLocale, useMessages } from "@/i18n/LocaleProvider";
import { formatApiError } from "@/lib/formatApiError";
import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import { formatRemainingDuration, secondsUntil } from "@/lib/formatRemainingDuration";
import type { AccountResponse, TransactionResponse, UpcomingDueResponse } from "@/types/domain";

const QUICK_LINKS = APP_NAV_ITEMS.filter((item) => item.to !== "/dashboard");
const SNAPSHOT_PARAMS = { limit: 5, skip: 0 } as const;
const PENDING_PARAMS = {
  ...SNAPSHOT_PARAMS,
  transaction_type: "transfer",
  status: "pending",
} as const;
const IN_TRANSIT_PARAMS = {
  ...SNAPSHOT_PARAMS,
  exclude_transfer: false,
  settlement_status: "in_transit",
} as const;
const DUE_SOON_PARAMS = { window_days: 14, include_paid: false } as const;
const DUE_SOON_LIMIT = 5;

function currentMonthWindow(locale: string): {
  start_date: string;
  end_date: string;
  label: string;
} {
  const now = new Date();
  const year = now.getUTCFullYear();
  const month = now.getUTCMonth();
  const start = new Date(Date.UTC(year, month, 1));
  const end = new Date(Date.UTC(year, month + 1, 0));
  const pad = (n: number) => String(n).padStart(2, "0");
  const start_date = `${String(start.getUTCFullYear())}-${pad(start.getUTCMonth() + 1)}-${pad(start.getUTCDate())}`;
  const end_date = `${String(end.getUTCFullYear())}-${pad(end.getUTCMonth() + 1)}-${pad(end.getUTCDate())}`;
  const label = start.toLocaleDateString(locale, {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
  return { start_date, end_date, label };
}

/** Automation-first authenticated Home dashboard (PPT-088 / #181). */
export function DashboardPage() {
  const { locale } = useLocale();
  const messages = useMessages();
  const m = messages.dashboard;
  const queryClient = useQueryClient();
  const [selectedCurrency, setSelectedCurrency] = useState<string | null>(null);
  const heroAi = useScopedAIToggle();
  const monthWindow = useMemo(() => currentMonthWindow(locale), [locale]);
  const sessionQuery = useQuery(bffSessionQueryOptions());
  const financialHealthQuery = useQuery(
    financialHealthReportQueryOptions({
      currency: selectedCurrency,
    }),
  );
  const activeCurrency = selectedCurrency ?? financialHealthQuery.data?.currency ?? null;
  const operatingCashflowQuery = useQuery(
    operatingCashflowReportQueryOptions({
      start_date: monthWindow.start_date,
      end_date: monthWindow.end_date,
      currency: activeCurrency,
      include_monthly_series: false,
    }),
  );
  const ingestionRunQuery = useQuery(latestIngestionRunQueryOptions());
  const accountsQuery = useQuery(accountsListQueryOptions(SNAPSHOT_PARAMS));
  const pendingQuery = useQuery(transactionsListQueryOptions(PENDING_PARAMS));
  const inTransitQuery = useQuery(transactionsListQueryOptions(IN_TRANSIT_PARAMS));
  const duesQuery = useQuery(upcomingDuesQueryOptions(DUE_SOON_PARAMS));

  const markPaidMutation = useMutation({
    mutationFn: (templateId: string) => markTemplatePaid(templateId),
    onSuccess: async (txn, templateId) => {
      await invalidateAfterTemplateWrite(queryClient, {
        templateId,
        markPaid: true,
        transactionId: txn.id,
      });
      toast.success("Marked paid");
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err));
    },
  });

  const user = sessionQuery.data?.user;
  const greetingName =
    user?.display_name?.trim() || user?.username?.trim() || user?.email?.split("@")[0] || null;
  const accounts = accountsQuery.data?.items ?? [];
  const pendingMovements = pendingQuery.data?.items ?? [];
  const inTransitMovements = inTransitQuery.data?.items ?? [];
  const dueSoonAll = duesQuery.data?.items ?? [];
  const dueSoon = dueSoonAll.slice(0, DUE_SOON_LIMIT);
  const accountsTotal = accountsQuery.data?.total ?? accounts.length;
  const pendingTotal = pendingQuery.data?.total ?? pendingMovements.length;
  const inTransitTotal = inTransitQuery.data?.total ?? inTransitMovements.length;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-7">
      <header className="animate-papita-card-enter relative overflow-hidden rounded-2xl border border-white/10 bg-[#04090c] p-6 text-white">
        <div className="relative z-10 flex flex-wrap items-center justify-between gap-5">
          <div className="space-y-1.5">
            <h1 className="text-[clamp(1.5rem,2vw,1.75rem)] leading-[1.2] font-semibold tracking-[-0.02em] text-balance text-white">
              {greetingName ? `${m.welcomePrefix} ${greetingName}` : m.title}
            </h1>
            <p className="max-w-[54ch] text-sm leading-relaxed text-white/75">{m.subtitle}</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <ScopedAITrigger
              open={heroAi.open}
              panelId={heroAi.panelId}
              onToggle={heroAi.toggle}
              compact={false}
              tone="dark"
            />
            <Button
              asChild
              size="sm"
              title="Log a new income, expense, or transfer"
              className="bg-emerald-500 text-[#04090c] hover:bg-emerald-400"
            >
              <Link to="/transactions">{m.newActivity}</Link>
            </Button>
            <Button
              asChild
              variant="outline"
              size="sm"
              title="Inspect monthly cashflow waterfall and top spending categories"
              className="border-white/20 bg-white/[0.06] text-white hover:bg-white/[0.12] hover:text-white"
            >
              <Link to="/reports">{m.viewSpendingReport}</Link>
            </Button>
            <section
              aria-label="Session status"
              title="HttpOnly BFF session cookie lifetime"
              className="rounded-xl border border-white/12 bg-white/[0.06] px-3.5 py-2 text-right text-white"
            >
              <p className="text-xs font-medium uppercase tracking-wide text-emerald-300/90">
                {m.accessToken}
              </p>
              <SessionTtlCountdown expiresAt={sessionQuery.data?.access_expires_at ?? null} />
            </section>
          </div>
        </div>
      </header>

      <ScopedAIPanel
        id={heroAi.panelId}
        open={heroAi.open}
        onClose={heroAi.close}
        module="dashboard"
        view="overview"
        control="dashboard-hero"
        title={m.title}
        currency={activeCurrency ?? undefined}
        surfaceContext={{
          currency: activeCurrency,
          month_label: monthWindow.label,
          due_soon_count: dueSoon.length,
          accounts_count: accounts.length,
          pending_transfers: pendingTotal,
          in_transit_transfers: inTransitTotal,
        }}
        suggestedPrompts={
          locale === "es-CO"
            ? [
                "Resume mi panorama general hoy: patrimonio, liquidez, flujo y próximos pagos.",
                "¿Hay alguna alerta urgente entre mis vencimientos y transferencias?",
                "¿Qué acción financiera me recomiendas revisar primero?",
              ]
            : [
                "Summarize my overall snapshot today across net worth, runway, cashflow, and dues.",
                "Are there any urgent alerts across due bills and in-transit transfers?",
                "Which module should I review next based on today's numbers?",
              ]
        }
      />

      <FinancialHealthScorecard
        report={financialHealthQuery.data}
        isPending={financialHealthQuery.isPending}
        isError={financialHealthQuery.isError}
        onSelectCurrency={(code) => {
          setSelectedCurrency(code);
        }}
      />

      <LivePulseSection
        ingestionRun={ingestionRunQuery.data}
        ingestionPending={ingestionRunQuery.isPending}
        ingestionError={ingestionRunQuery.isError}
        cashflow={operatingCashflowQuery.data}
        cashflowPending={operatingCashflowQuery.isPending}
        cashflowError={operatingCashflowQuery.isError}
        monthLabel={monthWindow.label}
      />

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <div className="space-y-6">
          <SnapshotPanel
            title={m.dueSoon}
            aiSpec={{
              module: "dashboard",
              view: "due-soon",
              control: "due-soon-card",
              title: m.dueSoon,
              currency: activeCurrency ?? undefined,
              surfaceContext: {
                window_days: DUE_SOON_PARAMS.window_days,
                due_count: dueSoonAll.length,
                items: dueSoon.map((d) => ({
                  name: d.template.name,
                  due_date: d.due_date,
                  amount: d.template.planned_amount,
                })),
              },
              suggestedPrompts:
                locale === "es-CO"
                  ? [
                      "Prioriza mis próximos pagos programados y su impacto en caja.",
                      "¿Alguno de estos cobros requiere cobertura líquida inmediata?",
                    ]
                  : [
                      "Prioritize these upcoming due bills by date and cash impact.",
                      "Do any upcoming bills strain my current liquid balance?",
                    ],
            }}
            icon={CalendarClock}
            iconTone="bg-warning-soft text-warning"
            viewAllTo="/payment-dues"
            viewAllLabel={m.viewAll}
            isPending={duesQuery.isPending}
            isError={duesQuery.isError}
            itemCount={dueSoon.length}
            emptyLabel={m.nothingDue}
            emptyActionTo="/payment-dues"
            emptyActionLabel={m.addPaymentDue}
            footer={
              dueSoonAll.length > dueSoon.length
                ? `${String(dueSoon.length)} / ${String(dueSoonAll.length)}`
                : dueSoonAll.length > 0
                  ? `${String(dueSoonAll.length)} (${String(DUE_SOON_PARAMS.window_days)}d)`
                  : null
            }
          >
            <ul className="divide-y divide-border">
              {dueSoon.map((due) => (
                <DueSoonRow
                  key={`${due.template.id}-${due.due_date}`}
                  due={due}
                  markPaidPending={markPaidMutation.isPending}
                  onMarkPaid={() => {
                    markPaidMutation.mutate(due.template.id);
                  }}
                />
              ))}
            </ul>
          </SnapshotPanel>

          <SnapshotPanel
            title={m.accounts}
            aiSpec={{
              module: "dashboard",
              view: "accounts-snapshot",
              control: "accounts-card",
              title: m.accounts,
              currency: activeCurrency ?? undefined,
              surfaceContext: {
                total_accounts: accountsTotal,
                shown: accounts.map((a) => ({
                  name: a.name,
                  kind: a.account_kind,
                  currency: a.currency,
                  balance: a.balance,
                })),
              },
              suggestedPrompts:
                locale === "es-CO"
                  ? [
                      "Resume la distribución entre activos y pasivos en estas cuentas.",
                      "¿Cómo se distribuyen mis saldos por moneda y tipo de cuenta?",
                    ]
                  : [
                      "Summarize the asset vs. liability distribution across these accounts.",
                      "How are my balances distributed by currency and account kind?",
                    ],
            }}
            icon={Landmark}
            iconTone="bg-success-soft text-success"
            viewAllTo="/accounts"
            viewAllLabel={m.viewAll}
            isPending={accountsQuery.isPending}
            isError={accountsQuery.isError}
            itemCount={accounts.length}
            emptyLabel={m.noAccounts}
            emptyActionTo="/accounts"
            emptyActionLabel={m.addAccount}
            footer={
              accountsTotal > accounts.length
                ? `${String(accounts.length)} / ${String(accountsTotal)}`
                : null
            }
          >
            <ul className="divide-y divide-border">
              {accounts.map((account) => (
                <AccountRow key={account.id} account={account} />
              ))}
            </ul>
          </SnapshotPanel>
        </div>

        <div className="space-y-6">
          <SnapshotPanel
            title={m.inTransitTransfers}
            icon={Send}
            iconTone="bg-warning-soft text-warning"
            viewAllTo="/transactions"
            viewAllLabel={m.viewAll}
            isPending={inTransitQuery.isPending}
            isError={inTransitQuery.isError}
            itemCount={inTransitMovements.length}
            emptyLabel={m.noInTransit}
            emptyActionTo="/transactions"
            emptyActionLabel={m.viewTransactions}
            footer={inTransitTotal > 0 ? String(inTransitTotal) : null}
          >
            <ul className="divide-y divide-border">
              {inTransitMovements.map((movement) => (
                <PendingMovementRow key={movement.id} movement={movement} />
              ))}
            </ul>
          </SnapshotPanel>

          <SnapshotPanel
            title={m.pendingTransfers}
            icon={Clock}
            iconTone="bg-info-soft text-info"
            viewAllTo="/transactions"
            viewAllLabel={m.viewAll}
            isPending={pendingQuery.isPending}
            isError={pendingQuery.isError}
            itemCount={pendingMovements.length}
            emptyLabel={m.noPending}
            emptyActionTo="/transactions"
            emptyActionLabel={m.scheduleTransfer}
            footer={pendingTotal > 0 ? String(pendingTotal) : null}
          >
            <ul className="divide-y divide-border">
              {pendingMovements.map((movement) => (
                <PendingMovementRow key={movement.id} movement={movement} />
              ))}
            </ul>
          </SnapshotPanel>

          <section aria-label={m.workspace} className="space-y-2.5">
            <h2 className="text-sm leading-[1.3] font-semibold tracking-[-0.01em] text-balance">
              {m.workspace}
            </h2>
            <div className="divide-y divide-border rounded-xl border border-border bg-card">
              {QUICK_LINKS.map((item) => {
                const meta = quickLinkMeta(item.to);
                const Icon = meta.icon;
                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className="group flex items-center justify-between gap-3 px-4 py-2.5 text-card-foreground transition-colors first:rounded-t-xl last:rounded-b-xl hover:bg-accent/25"
                  >
                    <div className="flex min-w-0 items-center gap-2.5">
                      <span
                        className={`flex size-7 shrink-0 items-center justify-center rounded-md ${meta.tone}`}
                      >
                        <Icon aria-hidden="true" className="size-3.5" />
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">
                          {messages.nav[item.to] ?? item.label}
                        </p>
                        <p className="truncate text-xs text-muted-foreground">{meta.hint}</p>
                      </div>
                    </div>
                    <ArrowUpRight
                      aria-hidden="true"
                      className="size-4 shrink-0 text-muted-foreground transition-transform duration-150 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-primary"
                    />
                  </Link>
                );
              })}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function SessionTtlCountdown({ expiresAt }: { expiresAt: number | null }) {
  const [nowMs, setNowMs] = useState(() => Date.now());

  useEffect(() => {
    if (expiresAt === null) {
      return;
    }
    const id = window.setInterval(() => {
      setNowMs(Date.now());
    }, 1000);
    return () => {
      window.clearInterval(id);
    };
  }, [expiresAt]);

  if (expiresAt === null) {
    return <p className="mt-0.5 text-sm text-white/70">Session lifetime unavailable</p>;
  }

  const remaining = secondsUntil(expiresAt, nowMs);
  const label = formatRemainingDuration(remaining);
  const isExpired = remaining <= 0;

  return (
    <p className="mt-0.5 text-sm" data-testid="session-ttl">
      <span className="text-white/65">Time left to live: </span>
      <span
        className={
          isExpired ? "font-medium text-rose-300" : "font-semibold tabular-nums text-emerald-300"
        }
      >
        {label}
      </span>
    </p>
  );
}

function SnapshotPanel({
  title,
  aiSpec,
  icon: Icon,
  iconTone,
  viewAllTo,
  viewAllLabel = "View all",
  isPending,
  isError,
  itemCount,
  emptyLabel,
  emptyActionTo,
  emptyActionLabel,
  footer,
  children,
}: {
  title: string;
  aiSpec?: {
    module: string;
    view: string;
    control: string;
    title: string;
    currency?: string;
    surfaceContext: Record<string, unknown>;
    suggestedPrompts: readonly string[];
  };
  icon: LucideIcon;
  iconTone: string;
  delayMs?: number;
  viewAllTo: string;
  viewAllLabel?: string;
  isPending: boolean;
  isError: boolean;
  itemCount: number;
  emptyLabel: string;
  emptyActionTo: string;
  emptyActionLabel: string;
  footer: string | null;
  children: ReactNode;
}) {
  const isEmpty = !isPending && !isError && itemCount === 0;
  const cardAi = useScopedAIToggle();

  return (
    <section aria-label={title} className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span
            className={`flex size-7 shrink-0 items-center justify-center rounded-lg ${iconTone}`}
          >
            <Icon aria-hidden="true" className="size-3.5" />
          </span>
          <h2 className="truncate text-sm font-semibold tracking-tight">{title}</h2>
          {!isPending && !isError && itemCount > 0 ? (
            <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs font-medium tabular-nums text-muted-foreground">
              {String(itemCount)}
            </span>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {aiSpec ? (
            <ScopedAITrigger open={cardAi.open} panelId={cardAi.panelId} onToggle={cardAi.toggle} />
          ) : null}
          <Link
            to={viewAllTo}
            className="shrink-0 text-xs font-medium text-primary underline-offset-4 hover:underline"
          >
            {viewAllLabel}
          </Link>
        </div>
      </div>
      {aiSpec ? (
        <ScopedAIPanel
          id={cardAi.panelId}
          open={cardAi.open}
          onClose={cardAi.close}
          module={aiSpec.module}
          view={aiSpec.view}
          control={aiSpec.control}
          title={aiSpec.title}
          currency={aiSpec.currency}
          surfaceContext={aiSpec.surfaceContext}
          suggestedPrompts={aiSpec.suggestedPrompts}
        />
      ) : null}
      <div className="rounded-xl border border-border bg-card p-5 text-card-foreground">
        {isPending ? (
          <div className="space-y-3" aria-label={`Loading ${title.toLowerCase()}`}>
            {[0, 1, 2].map((idx) => (
              <div key={idx} className="flex items-center justify-between gap-3">
                <div className="h-4 w-36 animate-pulse rounded bg-muted" />
                <div className="h-4 w-16 animate-pulse rounded bg-muted/70" />
              </div>
            ))}
          </div>
        ) : null}
        {isError ? (
          <p className="text-sm text-destructive" role="alert">
            Could not load {title.toLowerCase()}.
          </p>
        ) : null}
        {isEmpty ? (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-muted-foreground">{emptyLabel}</p>
            <Button asChild variant="outline" size="sm">
              <Link to={emptyActionTo}>{emptyActionLabel}</Link>
            </Button>
          </div>
        ) : null}
        {!isPending && !isError && itemCount > 0 ? children : null}
        {footer && !isEmpty ? (
          <p className="mt-3 border-t border-border pt-2.5 text-xs text-muted-foreground">
            {footer}
          </p>
        ) : null}
      </div>
    </section>
  );
}

function AccountRow({ account }: { account: AccountResponse }) {
  return (
    <li className="flex items-baseline justify-between gap-3 py-2 text-sm">
      <Link
        to={`/accounts/${account.id}`}
        className="truncate font-medium text-primary underline-offset-4 hover:underline"
      >
        {account.name}
      </Link>
      <span className="shrink-0 tabular-nums text-muted-foreground">
        {formatMoney(account.balance, account.currency)}
      </span>
    </li>
  );
}

function PendingMovementRow({ movement }: { movement: TransactionResponse }) {
  const label = movement.description.trim() || "Scheduled transfer";
  const routeLabel =
    movement.source_account_name && movement.destination_account_name
      ? `${movement.source_account_name} → ${movement.destination_account_name}`
      : null;

  return (
    <li className="space-y-0.5 py-2 text-sm">
      <div className="flex items-baseline justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className="truncate font-medium">{label}</span>
          {movement.settlement_status === "in_transit" ? (
            <span className="shrink-0 rounded-full bg-warning-soft px-2 py-0.5 text-xs font-medium text-warning">
              In transit
            </span>
          ) : null}
        </div>
        <span className="shrink-0 tabular-nums text-muted-foreground">
          {formatMoney(movement.amount, movement.currency)}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">
        {formatDate(movement.movement_date ?? movement.transaction_date)}
        {routeLabel ? ` · ${routeLabel}` : ""}
      </p>
    </li>
  );
}

function DueSoonRow({
  due,
  markPaidPending,
  onMarkPaid,
}: {
  due: UpcomingDueResponse;
  markPaidPending: boolean;
  onMarkPaid: () => void;
}) {
  return (
    <li className="space-y-1 py-2 text-sm">
      <div className="flex items-baseline justify-between gap-3">
        <Link
          to="/payment-dues"
          className="truncate font-medium text-primary underline-offset-4 hover:underline"
        >
          {due.template.name}
        </Link>
        <span className="shrink-0 tabular-nums text-muted-foreground">
          {formatMoney(due.template.planned_amount, "USD")}
        </span>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">Due {formatDate(due.due_date)}</p>
        <Button
          type="button"
          size="sm"
          variant="outline"
          disabled={markPaidPending || due.is_paid}
          onClick={onMarkPaid}
        >
          {due.is_paid ? "Paid" : "Mark paid"}
        </Button>
      </div>
    </li>
  );
}

function quickLinkMeta(path: string): { hint: string; icon: LucideIcon; tone: string } {
  switch (path) {
    case "/accounts":
      return {
        hint: "Balances and account details",
        icon: Landmark,
        tone: "bg-success-soft text-success",
      };
    case "/categories":
      return {
        hint: "Income and expense labels",
        icon: Tags,
        tone: "bg-primary/12 text-primary",
      };
    case "/transactions":
      return {
        hint: "Income, expenses, and transfers",
        icon: ArrowLeftRight,
        tone: "bg-info-soft text-info",
      };
    case "/payment-dues":
      return {
        hint: "Bills and payment deadlines",
        icon: CalendarClock,
        tone: "bg-warning-soft text-warning",
      };
    case "/reports":
      return {
        hint: "Spending breakdowns",
        icon: BarChart3,
        tone: "bg-accent text-accent-foreground",
      };
    default:
      return {
        hint: "Open this section",
        icon: ArrowUpRight,
        tone: "bg-muted text-muted-foreground",
      };
  }
}
