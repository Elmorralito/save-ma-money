import { useQuery } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";

import { accountsListQueryOptions, movementsListQueryOptions } from "@/api/queries";
import { bffSessionQueryOptions } from "@/auth/sessionQueries";
import { APP_NAV_ITEMS } from "@/components/layout/navItems";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import { formatRemainingDuration, secondsUntil } from "@/lib/formatRemainingDuration";
import type { AccountResponse, MovementResponse } from "@/types/domain";

const QUICK_LINKS = APP_NAV_ITEMS.filter((item) => item.to !== "/dashboard");
const SNAPSHOT_PARAMS = { limit: 5, skip: 0 } as const;
const PENDING_PARAMS = { ...SNAPSHOT_PARAMS, status: "pending" } as const;

/** Authenticated landing with session TTL, ledger snapshots, and quick links. */
export function DashboardPage() {
  const sessionQuery = useQuery(bffSessionQueryOptions());
  const accountsQuery = useQuery(accountsListQueryOptions(SNAPSHOT_PARAMS));
  const pendingQuery = useQuery(movementsListQueryOptions(PENDING_PARAMS));

  const user = sessionQuery.data?.user;
  const greetingName =
    user?.display_name?.trim() || user?.username?.trim() || user?.email?.split("@")[0] || null;
  const accounts = accountsQuery.data?.items ?? [];
  const pendingMovements = pendingQuery.data?.items ?? [];
  const accountsTotal = accountsQuery.data?.total ?? accounts.length;
  const pendingTotal = pendingQuery.data?.total ?? pendingMovements.length;

  return (
    <div className="mx-auto w-full max-w-3xl space-y-8">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">
          {greetingName ? `Welcome back, ${greetingName}` : "Dashboard"}
        </h1>
        <p className="text-sm text-muted-foreground">
          Session status, account balances, and pending transfers — then jump into the ledger.
        </p>
      </div>

      <section aria-label="Session status" className="space-y-1 border-b border-border pb-4">
        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Access token
        </p>
        <SessionTtlCountdown expiresAt={sessionQuery.data?.access_expires_at ?? null} />
        {sessionQuery.data?.session_backend ? (
          <p className="text-xs text-muted-foreground">
            Session store: {sessionQuery.data.session_backend}
          </p>
        ) : null}
      </section>

      <div className="grid gap-6 sm:grid-cols-2">
        <SnapshotPanel
          title="Accounts"
          viewAllTo="/accounts"
          isPending={accountsQuery.isPending}
          isError={accountsQuery.isError}
          itemCount={accounts.length}
          emptyLabel="No accounts yet"
          emptyActionTo="/accounts"
          emptyActionLabel="Add an account"
          footer={
            accountsTotal > accounts.length
              ? `Showing ${String(accounts.length)} of ${String(accountsTotal)}`
              : null
          }
        >
          <ul className="divide-y divide-border">
            {accounts.map((account) => (
              <AccountRow key={account.id} account={account} />
            ))}
          </ul>
        </SnapshotPanel>

        <SnapshotPanel
          title="Pending transfers"
          viewAllTo="/movements"
          isPending={pendingQuery.isPending}
          isError={pendingQuery.isError}
          itemCount={pendingMovements.length}
          emptyLabel="No pending transfers"
          emptyActionTo="/movements"
          emptyActionLabel="Schedule a transfer"
          footer={pendingTotal > 0 ? `${String(pendingTotal)} waiting to execute` : null}
        >
          <ul className="divide-y divide-border">
            {pendingMovements.map((movement) => (
              <PendingMovementRow key={movement.id} movement={movement} />
            ))}
          </ul>
        </SnapshotPanel>
      </div>

      <section aria-label="Quick links" className="grid gap-3 sm:grid-cols-2">
        {QUICK_LINKS.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className="rounded-lg border border-border bg-card p-4 text-card-foreground transition-colors hover:bg-accent/40"
          >
            <p className="text-sm font-semibold tracking-tight">{item.label}</p>
            <p className="mt-1 text-xs text-muted-foreground">{quickLinkHint(item.to)}</p>
          </Link>
        ))}
      </section>

      <div className="flex flex-wrap gap-2">
        <Button asChild>
          <Link to="/transactions">New activity</Link>
        </Button>
        <Button asChild variant="outline">
          <Link to="/reports">View spending report</Link>
        </Button>
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
    return <p className="text-sm text-muted-foreground">Session lifetime unavailable</p>;
  }

  const remaining = secondsUntil(expiresAt, nowMs);
  const label = formatRemainingDuration(remaining);
  const isExpired = remaining <= 0;

  return (
    <p className="text-sm" data-testid="session-ttl">
      <span className="text-muted-foreground">Time left to live: </span>
      <span className={isExpired ? "font-medium text-destructive" : "font-medium tabular-nums"}>
        {label}
      </span>
    </p>
  );
}

function SnapshotPanel({
  title,
  viewAllTo,
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
  viewAllTo: string;
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

  return (
    <section aria-label={title} className="space-y-3">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
        <Link
          to={viewAllTo}
          className="text-xs font-medium text-primary underline-offset-4 hover:underline"
        >
          View all
        </Link>
      </div>
      {isPending ? <p className="text-sm text-muted-foreground">Loading…</p> : null}
      {isError ? (
        <p className="text-sm text-destructive" role="alert">
          Could not load {title.toLowerCase()}.
        </p>
      ) : null}
      {isEmpty ? (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">{emptyLabel}</p>
          <Button asChild variant="outline" size="sm">
            <Link to={emptyActionTo}>{emptyActionLabel}</Link>
          </Button>
        </div>
      ) : null}
      {!isPending && !isError && itemCount > 0 ? children : null}
      {footer && !isEmpty ? <p className="text-xs text-muted-foreground">{footer}</p> : null}
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

function PendingMovementRow({ movement }: { movement: MovementResponse }) {
  const label = movement.description.trim() || "Scheduled transfer";
  const routeLabel =
    movement.source_account_name && movement.destination_account_name
      ? `${movement.source_account_name} → ${movement.destination_account_name}`
      : null;

  return (
    <li className="space-y-0.5 py-2 text-sm">
      <div className="flex items-baseline justify-between gap-3">
        <span className="truncate font-medium">{label}</span>
        <span className="shrink-0 tabular-nums text-muted-foreground">
          {formatMoney(movement.amount, movement.currency)}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">
        {formatDate(movement.movement_date)}
        {routeLabel ? ` · ${routeLabel}` : ""}
      </p>
    </li>
  );
}

function quickLinkHint(path: string): string {
  switch (path) {
    case "/accounts":
      return "Balances and account details";
    case "/categories":
      return "Income and expense labels";
    case "/transactions":
      return "Income and expenses";
    case "/movements":
      return "Transfers between accounts";
    case "/reports":
      return "Spending breakdowns";
    default:
      return "Open this section";
  }
}
