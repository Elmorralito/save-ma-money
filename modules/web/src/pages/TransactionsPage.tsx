import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { invalidateAfterLedgerWrite } from "@/api/invalidateLedger";
import {
  accountsListQueryOptions,
  categoriesListQueryOptions,
  transactionsListQueryOptions,
} from "@/api/queries";
import { deleteTransaction } from "@/api/transactions";
import { BulkTransactionsDialog } from "@/components/transactions/BulkTransactionsDialog";
import { TransactionFormDialog } from "@/components/transactions/TransactionFormDialog";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatApiError } from "@/lib/formatApiError";
import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import { formatSlugLabel } from "@/lib/formatSlugLabel";
import type { TransactionResponse } from "@/types/domain";

const PAGE_LIMIT = 100;
const PICKER_PARAMS = { limit: 100, skip: 0 } as const;

type FilterState = {
  account_id: string;
  category_id: string;
  transaction_type: string;
  status: string;
  start_date: string;
  end_date: string;
  search: string;
};

const EMPTY_FILTERS: FilterState = {
  account_id: "",
  category_id: "",
  transaction_type: "",
  status: "",
  start_date: "",
  end_date: "",
  search: "",
};

export function TransactionsPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [createOpen, setCreateOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<TransactionResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<TransactionResponse | null>(null);

  const listParams = useMemo(
    () => ({
      limit: PAGE_LIMIT,
      skip: 0,
      ...(filters.account_id ? { account_id: filters.account_id } : {}),
      ...(filters.category_id ? { category_id: filters.category_id } : {}),
      ...(filters.transaction_type ? { transaction_type: filters.transaction_type } : {}),
      ...(filters.status ? { status: filters.status } : {}),
      ...(filters.start_date ? { start_date: filters.start_date } : {}),
      ...(filters.end_date ? { end_date: filters.end_date } : {}),
      ...(filters.search.trim() ? { search: filters.search.trim() } : {}),
    }),
    [filters],
  );

  const listQuery = useQuery(transactionsListQueryOptions(listParams));
  const accountsQuery = useQuery(accountsListQueryOptions(PICKER_PARAMS));
  const categoriesQuery = useQuery(categoriesListQueryOptions(PICKER_PARAMS));
  const items = listQuery.data?.items ?? [];
  const accounts = accountsQuery.data?.items ?? [];
  const categories = categoriesQuery.data?.items ?? [];
  const hasActiveFilters = Object.values(filters).some((value) => value.trim() !== "");

  const deleteMutation = useMutation({
    mutationFn: (transactionId: string) => deleteTransaction(transactionId),
    onSuccess: async (_void, transactionId) => {
      await invalidateAfterLedgerWrite(queryClient, {
        transactions: true,
        removeTransactionId: transactionId,
      });
      toast.success("Transaction deleted");
      setDeleteTarget(null);
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err));
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Transactions</h1>
          <p className="text-sm text-muted-foreground">
            Income and expense only by default (transfers live under Movements). No client-side
            ledger rules.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setBulkOpen(true);
            }}
          >
            Bulk create
          </Button>
          <Button
            type="button"
            onClick={() => {
              setCreateOpen(true);
            }}
          >
            New transaction
          </Button>
        </div>
      </div>

      <div className="grid gap-3 rounded-md border border-border p-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-2">
          <Label htmlFor="txn-filter-account">Account</Label>
          <NativeSelect
            id="txn-filter-account"
            value={filters.account_id}
            onChange={(event) => {
              setFilters((prev) => ({ ...prev, account_id: event.target.value }));
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
        <div className="space-y-2">
          <Label htmlFor="txn-filter-category">Category</Label>
          <NativeSelect
            id="txn-filter-category"
            value={filters.category_id}
            onChange={(event) => {
              setFilters((prev) => ({ ...prev, category_id: event.target.value }));
            }}
          >
            <option value="">All categories</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="space-y-2">
          <Label htmlFor="txn-filter-type">Type</Label>
          <NativeSelect
            id="txn-filter-type"
            value={filters.transaction_type}
            onChange={(event) => {
              setFilters((prev) => ({ ...prev, transaction_type: event.target.value }));
            }}
          >
            <option value="">Income &amp; expense</option>
            <option value="income">Income</option>
            <option value="expense">Expense</option>
          </NativeSelect>
        </div>
        <div className="space-y-2">
          <Label htmlFor="txn-filter-status">Status</Label>
          <NativeSelect
            id="txn-filter-status"
            value={filters.status}
            onChange={(event) => {
              setFilters((prev) => ({ ...prev, status: event.target.value }));
            }}
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </NativeSelect>
        </div>
        <div className="space-y-2">
          <Label htmlFor="txn-filter-start">Start date</Label>
          <Input
            id="txn-filter-start"
            type="date"
            value={filters.start_date}
            onChange={(event) => {
              setFilters((prev) => ({ ...prev, start_date: event.target.value }));
            }}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="txn-filter-end">End date</Label>
          <Input
            id="txn-filter-end"
            type="date"
            value={filters.end_date}
            onChange={(event) => {
              setFilters((prev) => ({ ...prev, end_date: event.target.value }));
            }}
          />
        </div>
        <div className="space-y-2 sm:col-span-2">
          <Label htmlFor="txn-filter-search">Search</Label>
          <Input
            id="txn-filter-search"
            placeholder="Description or reference"
            value={filters.search}
            onChange={(event) => {
              setFilters((prev) => ({ ...prev, search: event.target.value }));
            }}
          />
        </div>
        <div className="flex items-end sm:col-span-2 lg:col-span-4">
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setFilters(EMPTY_FILTERS);
            }}
          >
            Clear filters
          </Button>
        </div>
      </div>

      <QueryState
        isPending={listQuery.isPending}
        isError={listQuery.isError}
        error={listQuery.error}
        isEmpty={!listQuery.isPending && !listQuery.isError && items.length === 0}
        emptyTitle={hasActiveFilters ? "No matching transactions" : "No transactions yet"}
        emptyDescription={
          hasActiveFilters
            ? "Try clearing filters or broadening the date range."
            : "Create an income or expense to get started."
        }
        emptyAction={
          hasActiveFilters ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setFilters(EMPTY_FILTERS);
              }}
            >
              Clear filters
            </Button>
          ) : (
            <Button
              type="button"
              onClick={() => {
                setCreateOpen(true);
              }}
            >
              Create your first transaction
            </Button>
          )
        }
        onRetry={() => {
          void listQuery.refetch();
        }}
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Account</TableHead>
              <TableHead>Category</TableHead>
              <TableHead>Description</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((txn) => (
              <TableRow key={txn.id}>
                <TableCell className="tabular-nums">{formatDate(txn.transaction_date)}</TableCell>
                <TableCell className="text-muted-foreground">
                  {formatSlugLabel(txn.transaction_type)}
                </TableCell>
                <TableCell>{txn.account_name ?? txn.account_id ?? "—"}</TableCell>
                <TableCell>{txn.category_name ?? txn.category_id ?? "—"}</TableCell>
                <TableCell>{txn.description || "—"}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatMoney(txn.amount, txn.currency)}
                </TableCell>
                <TableCell>{formatSlugLabel(txn.status)}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setEditTarget(txn);
                      }}
                    >
                      Edit
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="destructive"
                      onClick={() => {
                        setDeleteTarget(txn);
                      }}
                    >
                      Delete
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {listQuery.data ? (
          <p className="text-xs text-muted-foreground">
            Showing {items.length} of {listQuery.data.total}
            {listQuery.data.total > PAGE_LIMIT ? ` (first ${String(PAGE_LIMIT)} only)` : ""}
          </p>
        ) : null}
      </QueryState>

      <TransactionFormDialog open={createOpen} onOpenChange={setCreateOpen} mode="create" />
      <TransactionFormDialog
        open={editTarget !== null}
        onOpenChange={(open) => {
          if (!open) {
            setEditTarget(null);
          }
        }}
        mode="edit"
        transaction={editTarget}
      />
      <BulkTransactionsDialog open={bulkOpen} onOpenChange={setBulkOpen} />

      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDeleteTarget(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete transaction</DialogTitle>
            <DialogDescription>
              Soft-delete this {deleteTarget?.transaction_type ?? "transaction"}
              {deleteTarget?.description ? ` (“${deleteTarget.description}”)` : ""}? This cannot be
              undone from the UI.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setDeleteTarget(null);
              }}
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={deleteMutation.isPending || !deleteTarget}
              onClick={() => {
                if (deleteTarget) {
                  deleteMutation.mutate(deleteTarget.id);
                }
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
