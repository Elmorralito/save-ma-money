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
      toast.success("Account deleted");
      await navigate("/accounts");
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err));
    },
  });

  return (
    <div className="space-y-6">
      <div className="space-y-1">
        <Link
          to="/accounts"
          className="text-sm text-muted-foreground underline-offset-4 hover:underline"
        >
          ← Accounts
        </Link>
        <h1 className="text-2xl font-semibold tracking-tight">
          {account?.name ?? "Account detail"}
        </h1>
      </div>

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
            <dl className="grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-xs text-muted-foreground">Balance</dt>
                <dd className="text-lg font-medium tabular-nums">
                  {formatMoney(account.balance, account.currency)}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Kind / side</dt>
                <dd className="text-sm">
                  {account.account_kind} · {account.ledger_side}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Status</dt>
                <dd className="text-sm">{account.is_active ? "Active" : "Inactive"}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Currency</dt>
                <dd className="text-sm">{account.currency}</dd>
              </div>
            </dl>

            {account.banking_details ? (
              <section className="rounded-md border border-border p-3 text-sm">
                <h2 className="font-medium">Banking</h2>
                <p className="text-muted-foreground">
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
