import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { invalidateAfterLedgerWrite } from "@/api/invalidateLedger";
import {
  accountsListQueryOptions,
  categoriesListQueryOptions,
  transactionsListQueryOptions,
} from "@/api/queries";
import { deleteTransaction } from "@/api/transactions";
import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import { BulkTransactionsDialog } from "@/components/transactions/BulkTransactionsDialog";
import { TransactionFormDialog } from "@/components/transactions/TransactionFormDialog";
import { QueryState } from "@/components/QueryState";
import {
  SortableTableHead,
  sortItems,
  toggleSort,
  type SortState,
} from "@/components/table/SortableTableHead";
import { DEFAULT_PAGE_SIZE, TablePagination } from "@/components/table/TablePagination";
import { ActionIconButton } from "@/components/ui/action-icon-button";
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
import { useLocale } from "@/i18n/LocaleProvider";
import { formatApiError } from "@/lib/formatApiError";
import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import { formatSlugLabel } from "@/lib/formatSlugLabel";
import type { TransactionResponse } from "@/types/domain";

const PICKER_PARAMS = { limit: 100, skip: 0 } as const;

type TxnSortKey = "date" | "type" | "account" | "category" | "description" | "amount" | "status";

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
  const { locale, messages } = useLocale();
  const tt = messages.transactions;
  const txnsAi = useScopedAIToggle();
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(DEFAULT_PAGE_SIZE);
  const [sort, setSort] = useState<SortState<TxnSortKey>>({ key: "date", direction: "desc" });
  const [createOpen, setCreateOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<TransactionResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<TransactionResponse | null>(null);

  function updateFilters(updater: (prev: FilterState) => FilterState) {
    setFilters(updater);
    setPage(1);
  }

  const listParams = useMemo(
    () => ({
      limit: pageSize,
      skip: (page - 1) * pageSize,
      ...(filters.account_id ? { account_id: filters.account_id } : {}),
      ...(filters.category_id ? { category_id: filters.category_id } : {}),
      ...(filters.transaction_type ? { transaction_type: filters.transaction_type } : {}),
      ...(filters.status ? { status: filters.status } : {}),
      ...(filters.start_date ? { start_date: filters.start_date } : {}),
      ...(filters.end_date ? { end_date: filters.end_date } : {}),
      ...(filters.search.trim() ? { search: filters.search.trim() } : {}),
    }),
    [filters, page, pageSize],
  );

  const listQuery = useQuery(transactionsListQueryOptions(listParams));
  const accountsQuery = useQuery(accountsListQueryOptions(PICKER_PARAMS));
  const categoriesQuery = useQuery(categoriesListQueryOptions(PICKER_PARAMS));
  const rawItems = listQuery.data?.items ?? [];
  const accounts = accountsQuery.data?.items ?? [];
  const categories = categoriesQuery.data?.items ?? [];

  const accountNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const acct of accounts) {
      map.set(acct.id, acct.name);
    }
    return map;
  }, [accounts]);

  const categoryNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const cat of categories) {
      map.set(cat.id, cat.name);
      for (const sub of cat.subcategories ?? []) {
        map.set(sub.id, sub.name);
      }
    }
    return map;
  }, [categories]);

  const resolveAccountLabel = (t: TransactionResponse): string => {
    if (t.transaction_type === "transfer") {
      const src =
        t.source_account_name ??
        (t.source_account_id ? accountNameById.get(t.source_account_id) : undefined) ??
        t.source_account_id ??
        "";
      const dst =
        t.destination_account_name ??
        (t.destination_account_id ? accountNameById.get(t.destination_account_id) : undefined) ??
        t.destination_account_id ??
        "";
      return [src, dst].filter(Boolean).join(" → ");
    }
    return (
      t.account_name ??
      (t.account_id ? accountNameById.get(t.account_id) : undefined) ??
      t.account_id ??
      ""
    );
  };

  const resolveCategoryLabel = (t: TransactionResponse): string =>
    t.category_name ??
    (t.category_id ? categoryNameById.get(t.category_id) : undefined) ??
    t.category_id ??
    "";

  const items = useMemo(
    () =>
      sortItems(rawItems, sort, {
        date: (t) => t.transaction_date,
        type: (t) => t.transaction_type,
        account: (t) => resolveAccountLabel(t),
        category: (t) => resolveCategoryLabel(t),
        description: (t) => t.description,
        amount: (t) => t.amount,
        status: (t) => t.status,
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [rawItems, sort, accountNameById, categoryNameById],
  );
  const hasActiveFilters = Object.values(filters).some((value) => value.trim() !== "");
  const total = listQuery.data?.total ?? items.length;

  const deleteMutation = useMutation({
    mutationFn: (transactionId: string) => deleteTransaction(transactionId),
    onSuccess: async (_void, transactionId) => {
      await invalidateAfterLedgerWrite(queryClient, {
        transactions: true,
        removeTransactionId: transactionId,
      });
      toast.success(tt.deletedToast);
      setDeleteTarget(null);
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err));
    },
  });

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-balance">{tt.title}</h1>
          <p className="text-sm text-muted-foreground text-pretty">{tt.subtitle}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <ScopedAITrigger
            open={txnsAi.open}
            panelId={txnsAi.panelId}
            onToggle={txnsAi.toggle}
            compact={false}
          />
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setBulkOpen(true);
            }}
          >
            {tt.bulkCreate}
          </Button>
          <Button
            type="button"
            onClick={() => {
              setCreateOpen(true);
            }}
          >
            {tt.newTransaction}
          </Button>
        </div>
      </header>

      <ScopedAIPanel
        id={txnsAi.panelId}
        open={txnsAi.open}
        onClose={txnsAi.close}
        module="transactions"
        view="ledger"
        control="transactions-table"
        title={tt.title}
        surfaceContext={{
          total_matching: total,
          filters,
          sort,
          visible_transactions: items.slice(0, 15).map((t) => ({
            date: t.transaction_date,
            type: t.transaction_type,
            account: resolveAccountLabel(t),
            category: resolveCategoryLabel(t),
            description: t.description,
            amount: t.amount,
            currency: t.currency,
            status: t.status,
          })),
        }}
        suggestedPrompts={
          locale === "es-CO"
            ? [
                "Resume los movimientos visibles en este libro filtrado.",
                "¿Detectas cobros repetidos, transferencias inusuales o pendientes?",
              ]
            : [
                "Summarize patterns in these filtered ledger transactions.",
                "Spot any notable spikes, recurring charges, or pending items here.",
              ]
        }
      />

      <div className="grid gap-3 rounded-2xl border border-border bg-card p-5 shadow-xs sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-2">
          <Label htmlFor="txn-filter-account">{tt.accountLabel}</Label>
          <NativeSelect
            id="txn-filter-account"
            value={filters.account_id}
            onChange={(event) => {
              updateFilters((prev) => ({ ...prev, account_id: event.target.value }));
            }}
          >
            <option value="">{tt.allAccounts}</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="space-y-2">
          <Label htmlFor="txn-filter-category">{tt.categoryLabel}</Label>
          <NativeSelect
            id="txn-filter-category"
            value={filters.category_id}
            onChange={(event) => {
              updateFilters((prev) => ({ ...prev, category_id: event.target.value }));
            }}
          >
            <option value="">{tt.allCategories}</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="space-y-2">
          <Label htmlFor="txn-filter-type">{tt.typeLabel}</Label>
          <NativeSelect
            id="txn-filter-type"
            value={filters.transaction_type}
            onChange={(event) => {
              updateFilters((prev) => ({ ...prev, transaction_type: event.target.value }));
            }}
          >
            <option value="">{tt.allTypesIncomeExpense}</option>
            <option value="income">{tt.income}</option>
            <option value="expense">{tt.expense}</option>
            <option value="transfer">{tt.transfer}</option>
          </NativeSelect>
        </div>
        <div className="space-y-2">
          <Label htmlFor="txn-filter-status">{tt.statusLabel}</Label>
          <NativeSelect
            id="txn-filter-status"
            value={filters.status}
            onChange={(event) => {
              updateFilters((prev) => ({ ...prev, status: event.target.value }));
            }}
          >
            <option value="">{tt.allStatuses}</option>
            <option value="pending">{tt.pending}</option>
            <option value="completed">{tt.completed}</option>
            <option value="cancelled">{tt.cancelled}</option>
          </NativeSelect>
        </div>
        <div className="space-y-2">
          <Label htmlFor="txn-filter-start">{tt.startDate}</Label>
          <Input
            id="txn-filter-start"
            type="date"
            value={filters.start_date}
            onChange={(event) => {
              updateFilters((prev) => ({ ...prev, start_date: event.target.value }));
            }}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="txn-filter-end">{tt.endDate}</Label>
          <Input
            id="txn-filter-end"
            type="date"
            value={filters.end_date}
            onChange={(event) => {
              updateFilters((prev) => ({ ...prev, end_date: event.target.value }));
            }}
          />
        </div>
        <div className="space-y-2 sm:col-span-2">
          <Label htmlFor="txn-filter-search">{tt.searchLabel}</Label>
          <Input
            id="txn-filter-search"
            placeholder={tt.searchPlaceholder}
            value={filters.search}
            onChange={(event) => {
              updateFilters((prev) => ({ ...prev, search: event.target.value }));
            }}
          />
        </div>
        <div className="flex items-end sm:col-span-2 lg:col-span-4">
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              updateFilters(() => EMPTY_FILTERS);
            }}
          >
            {tt.clearFilters}
          </Button>
        </div>
      </div>

      <QueryState
        isPending={listQuery.isPending}
        isError={listQuery.isError}
        error={listQuery.error}
        isEmpty={!listQuery.isPending && !listQuery.isError && items.length === 0}
        emptyTitle={hasActiveFilters ? tt.emptyFilteredTitle : tt.emptyTitle}
        emptyDescription={hasActiveFilters ? tt.emptyFilteredDescription : tt.emptyDescription}
        emptyAction={
          hasActiveFilters ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setFilters(EMPTY_FILTERS);
              }}
            >
              {tt.clearFilters}
            </Button>
          ) : (
            <Button
              type="button"
              onClick={() => {
                setCreateOpen(true);
              }}
            >
              {tt.createFirst}
            </Button>
          )
        }
        onRetry={() => {
          void listQuery.refetch();
        }}
      >
        <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-xs">
          <Table>
            <TableHeader>
              <TableRow>
                <SortableTableHead
                  label={tt.colDate}
                  sortKey="date"
                  sort={sort}
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key, "desc"));
                  }}
                />
                <SortableTableHead
                  label={tt.colType}
                  sortKey="type"
                  sort={sort}
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key));
                  }}
                />
                <SortableTableHead
                  label={tt.colAccount}
                  sortKey="account"
                  sort={sort}
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key));
                  }}
                />
                <SortableTableHead
                  label={tt.colCategory}
                  sortKey="category"
                  sort={sort}
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key));
                  }}
                />
                <SortableTableHead
                  label={tt.colDescription}
                  sortKey="description"
                  sort={sort}
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key));
                  }}
                />
                <SortableTableHead
                  label={tt.colAmount}
                  sortKey="amount"
                  sort={sort}
                  align="right"
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key, "desc"));
                  }}
                />
                <SortableTableHead
                  label={tt.colStatus}
                  sortKey="status"
                  sort={sort}
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key));
                  }}
                />
                <TableHead className="text-right">{tt.colActions}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((txn) => {
                const statusBadge =
                  txn.status === "completed"
                    ? "bg-success-soft text-success"
                    : txn.status === "pending"
                      ? "bg-warning-soft text-warning"
                      : "bg-muted text-muted-foreground";
                return (
                  <TableRow key={txn.id}>
                    <TableCell className="tabular-nums">
                      {formatDate(txn.transaction_date)}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {tt.types[txn.transaction_type] ?? formatSlugLabel(txn.transaction_type)}
                    </TableCell>
                    <TableCell>
                      {txn.transaction_type === "transfer" &&
                      (txn.source_account_id || txn.destination_account_id) ? (
                        <span className="inline-flex flex-wrap items-center gap-1">
                          {txn.source_account_id ? (
                            <Link
                              to={`/accounts/${txn.source_account_id}`}
                              className="font-medium text-primary underline-offset-4 hover:underline"
                            >
                              {txn.source_account_name ??
                                accountNameById.get(txn.source_account_id) ??
                                txn.source_account_id}
                            </Link>
                          ) : (
                            "—"
                          )}
                          <span aria-hidden="true" className="text-muted-foreground">
                            →
                          </span>
                          {txn.destination_account_id ? (
                            <Link
                              to={`/accounts/${txn.destination_account_id}`}
                              className="font-medium text-primary underline-offset-4 hover:underline"
                            >
                              {txn.destination_account_name ??
                                accountNameById.get(txn.destination_account_id) ??
                                txn.destination_account_id}
                            </Link>
                          ) : (
                            "—"
                          )}
                        </span>
                      ) : txn.account_id ? (
                        <Link
                          to={`/accounts/${txn.account_id}`}
                          className="font-medium text-primary underline-offset-4 hover:underline"
                        >
                          {txn.account_name ??
                            accountNameById.get(txn.account_id) ??
                            txn.account_id}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell>
                      {txn.category_id
                        ? (() => {
                            const catLabel =
                              txn.category_name ??
                              categoryNameById.get(txn.category_id) ??
                              txn.category_id;
                            return (
                              <Link
                                to={`/categories?search=${encodeURIComponent(catLabel)}`}
                                className="font-medium text-primary underline-offset-4 hover:underline"
                              >
                                {catLabel}
                              </Link>
                            );
                          })()
                        : "—"}
                    </TableCell>
                    <TableCell>{txn.description || "—"}</TableCell>
                    <TableCell className="text-right font-medium tabular-nums">
                      {formatMoney(txn.amount, txn.currency)}
                    </TableCell>
                    <TableCell>
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadge}`}
                      >
                        {tt.statuses[txn.status] ?? formatSlugLabel(txn.status)}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-1.5">
                        <ActionIconButton
                          icon={Pencil}
                          label={tt.editTransaction}
                          tone="sky"
                          onClick={() => {
                            setEditTarget(txn);
                          }}
                        />
                        <ActionIconButton
                          icon={Trash2}
                          label={tt.deleteTransaction}
                          tone="rose"
                          onClick={() => {
                            setDeleteTarget(txn);
                          }}
                        />
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
          <TablePagination
            page={page}
            pageSize={pageSize}
            total={total}
            visibleCount={items.length}
            onPageChange={setPage}
            onPageSizeChange={(nextSize) => {
              setPageSize(nextSize);
              setPage(1);
            }}
          />
        </div>
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
            <DialogTitle>{tt.deleteTitle}</DialogTitle>
            <DialogDescription>
              {tt.deleteConfirmPrefix}{" "}
              {deleteTarget
                ? (tt.types[deleteTarget.transaction_type] ?? deleteTarget.transaction_type)
                : ""}
              {deleteTarget?.description ? ` (“${deleteTarget.description}”)` : ""}?{" "}
              {tt.deleteConfirmSuffix}
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
              {tt.cancel}
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
              {deleteMutation.isPending ? tt.deleting : tt.delete}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
