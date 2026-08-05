import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { accountsListQueryOptions } from "@/api/queries";
import { AccountFormDialog } from "@/components/accounts/AccountFormDialog";
import { QueryState } from "@/components/QueryState";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatMoney } from "@/lib/formatMoney";
import { formatSlugLabel } from "@/lib/formatSlugLabel";

/** First-page list window (pagination UI deferred). */
const LIST_PARAMS = { limit: 100, skip: 0 } as const;

export function AccountsPage() {
  const [createOpen, setCreateOpen] = useState(false);
  const listQuery = useQuery(accountsListQueryOptions(LIST_PARAMS));
  const items = listQuery.data?.items ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Accounts</h1>
          <p className="text-sm text-muted-foreground">
            Your bank, card, and other balances in one place.
          </p>
        </div>
        <Button
          type="button"
          onClick={() => {
            setCreateOpen(true);
          }}
        >
          New account
        </Button>
      </div>

      <QueryState
        isPending={listQuery.isPending}
        isError={listQuery.isError}
        error={listQuery.error}
        isEmpty={!listQuery.isPending && !listQuery.isError && items.length === 0}
        emptyTitle="No accounts yet"
        emptyDescription="Create an account to start tracking balances."
        emptyAction={
          <Button
            type="button"
            onClick={() => {
              setCreateOpen(true);
            }}
          >
            Create your first account
          </Button>
        }
        onRetry={() => {
          void listQuery.refetch();
        }}
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Kind</TableHead>
              <TableHead>Side</TableHead>
              <TableHead className="text-right">Balance</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((account) => (
              <TableRow key={account.id}>
                <TableCell>
                  <Link
                    to={`/accounts/${account.id}`}
                    className="font-medium text-primary underline-offset-4 hover:underline"
                  >
                    {account.name}
                  </Link>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {formatSlugLabel(account.account_kind)}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {formatSlugLabel(account.ledger_side)}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatMoney(account.balance, account.currency)}
                </TableCell>
                <TableCell>{account.is_active ? "Active" : "Inactive"}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {listQuery.data ? (
          <p className="text-xs text-muted-foreground">
            Showing {items.length} of {listQuery.data.total}
            {listQuery.data.total > LIST_PARAMS.limit
              ? ` (first ${String(LIST_PARAMS.limit)} only)`
              : ""}
          </p>
        ) : null}
      </QueryState>

      <AccountFormDialog open={createOpen} onOpenChange={setCreateOpen} mode="create" />
    </div>
  );
}
