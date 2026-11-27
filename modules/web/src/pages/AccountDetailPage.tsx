import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { deleteAccount } from "@/api/accounts";
import { accountDetailQueryOptions } from "@/api/queries";
import { queryKeys } from "@/api/queryKeys";
import { AccountFormDialog } from "@/components/accounts/AccountFormDialog";
import { QueryState } from "@/components/QueryState";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { formatApiError } from "@/lib/formatApiError";
import { formatMoney } from "@/lib/formatMoney";
import { formatSlugLabel } from "@/lib/formatSlugLabel";

export function AccountDetailPage() {
  const { accountId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const detailQuery = useQuery(accountDetailQueryOptions(accountId));
  const account = detailQuery.data;

  const deleteMutation = useMutation({
    mutationFn: () => deleteAccount(accountId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.accounts.lists() });
      await queryClient.removeQueries({ queryKey: queryKeys.accounts.detail(accountId) });
      await queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      toast.success("Account deleted");
      await navigate("/accounts");
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err));
    },
  });

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <header className="space-y-1 border-b border-border pb-5">
        <Link
          to="/accounts"
          className="text-sm font-medium text-primary underline-offset-4 hover:underline"
        >
          ← Accounts
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight">
          {account?.name ?? "Account detail"}
        </h1>
      </header>

      <QueryState
        isPending={detailQuery.isPending}
        isError={detailQuery.isError}
        error={detailQuery.error}
        isEmpty={false}
        emptyTitle=""
        onRetry={() => {
          void detailQuery.refetch();
        }}
      >
        {account ? (
          <div className="space-y-4">
            <dl className="grid gap-4 rounded-xl border border-border bg-card p-5 shadow-xs sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Balance
                </dt>
                <dd className="mt-1 text-xl font-semibold tabular-nums">
                  {formatMoney(account.balance, account.currency)}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Kind / side
                </dt>
                <dd className="mt-1 text-sm font-medium">
                  {formatSlugLabel(account.account_kind)} · {formatSlugLabel(account.ledger_side)}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Status
                </dt>
                <dd className="mt-1">
                  <span
                    className={
                      account.is_active
                        ? "inline-flex rounded-full bg-success-soft px-2.5 py-0.5 text-xs font-medium text-success"
                        : "inline-flex rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground"
                    }
                  >
                    {account.is_active ? "Active" : "Inactive"}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Currency
                </dt>
                <dd className="mt-1 text-sm font-medium">{account.currency}</dd>
              </div>
            </dl>

            {account.banking_details ? (
              <section className="rounded-xl border border-border bg-card p-5 text-sm shadow-xs">
                <h2 className="font-semibold">Banking</h2>
                <p className="mt-1 text-muted-foreground">
                  {account.banking_details.entity}
                  {account.banking_details.account_number
                    ? ` · ${account.banking_details.account_number}`
                    : ""}
                </p>
              </section>
            ) : null}

            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                onClick={() => {
                  setEditOpen(true);
                }}
              >
                Edit
              </Button>
              <Button
                type="button"
                variant="destructive"
                onClick={() => {
                  setDeleteOpen(true);
                }}
              >
                Delete
              </Button>
            </div>
          </div>
        ) : null}
      </QueryState>

      <AccountFormDialog open={editOpen} onOpenChange={setEditOpen} mode="edit" account={account} />

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete account?</DialogTitle>
            <DialogDescription>
              Soft-deletes the account via the API. This cannot be undone from the UI.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setDeleteOpen(false);
              }}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={() => {
                deleteMutation.mutate();
              }}
            >
              {deleteMutation.isPending ? "Deleting…" : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
