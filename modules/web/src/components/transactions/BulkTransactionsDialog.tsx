import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState, type FormEvent } from "react";
import { toast } from "sonner";

import { bulkMaxTransactions } from "@/api/contract";
import { invalidateAfterLedgerWrite } from "@/api/invalidateLedger";
import {
  accountsListQueryOptions,
  categoriesListQueryOptions,
  clientContractQueryOptions,
} from "@/api/queries";
import { bulkCreateTransactions } from "@/api/transactions";
import { isBulkOverCap } from "@/components/transactions/bulkCap";
import {
  emptyTransactionFormState,
  toTransactionCreate,
  type TransactionFormState,
} from "@/components/transactions/transactionFormState";
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
import { formatApiError } from "@/lib/formatApiError";

const PICKER_PARAMS = { limit: 100, skip: 0 } as const;
const DEFAULT_BULK_MAX = 100;

type BulkTransactionsDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

type BulkBodyProps = {
  onOpenChange: (open: boolean) => void;
};

function BulkBody({ onOpenChange }: BulkBodyProps) {
  const queryClient = useQueryClient();
  const contractQuery = useQuery(clientContractQueryOptions());
  const accountsQuery = useQuery(accountsListQueryOptions(PICKER_PARAMS));
  const categoriesQuery = useQuery(categoriesListQueryOptions(PICKER_PARAMS));
  const [rows, setRows] = useState<TransactionFormState[]>(() => [emptyTransactionFormState()]);
  const [error, setError] = useState<string | null>(null);

  const bulkMax = useMemo(() => {
    return bulkMaxTransactions(contractQuery.data) ?? DEFAULT_BULK_MAX;
  }, [contractQuery.data]);

  const overCap = isBulkOverCap(rows.length, bulkMax);

  const mutation = useMutation({
    mutationFn: async () => {
      if (overCap) {
        throw new Error(`Bulk create exceeds max of ${String(bulkMax)} (X-Papita-Bulk-Max).`);
      }
      const transactions = rows.map((row) => toTransactionCreate(row));
      return bulkCreateTransactions({ transactions });
    },
    onSuccess: async (result) => {
      await invalidateAfterLedgerWrite(queryClient, { transactions: true });
      if (result.failed > 0) {
        toast.warning(
          `Bulk finished: ${String(result.created)} created, ${String(result.failed)} failed`,
        );
      } else {
        toast.success(`Bulk created ${String(result.created)} transaction(s)`);
      }
      onOpenChange(false);
    },
    onError: (err: unknown) => {
      setError(formatApiError(err));
      toast.error(formatApiError(err));
    },
  });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (overCap) {
      setError(`Bulk create exceeds max of ${String(bulkMax)}.`);
      return;
    }
    try {
      for (const row of rows) {
        toTransactionCreate(row);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid form");
      return;
    }
    mutation.mutate();
  }

  function patchRow(index: number, partial: Partial<TransactionFormState>) {
    setRows((prev) => prev.map((row, i) => (i === index ? { ...row, ...partial } : row)));
  }

  function addRow() {
    if (rows.length >= bulkMax) {
      setError(`Cannot add more than ${String(bulkMax)} rows.`);
      return;
    }
    setRows((prev) => [...prev, emptyTransactionFormState()]);
  }

  function removeRow(index: number) {
    setRows((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== index)));
  }

  const accounts = accountsQuery.data?.items ?? [];
  const categories = categoriesQuery.data?.items ?? [];

  return (
    <form className="space-y-4" onSubmit={onSubmit}>
      <p className="text-sm text-muted-foreground">
        Max rows: <span className="font-medium text-foreground">{bulkMax}</span> (from client
        contract / <code className="text-xs">X-Papita-Bulk-Max</code>).
      </p>
      <div className="max-h-[50vh] space-y-4 overflow-y-auto pr-1">
        {rows.map((row, index) => (
          <fieldset
            key={`bulk-row-${String(index)}`}
            className="space-y-3 rounded-md border border-border p-3"
          >
            <legend className="px-1 text-sm font-medium">Row {index + 1}</legend>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor={`bulk-${String(index)}-type`}>Type</Label>
                <NativeSelect
                  id={`bulk-${String(index)}-type`}
                  value={row.transaction_type}
                  onChange={(event) => {
                    patchRow(index, {
                      transaction_type: event.target.value as "income" | "expense",
                    });
                  }}
                >
                  <option value="expense">Expense</option>
                  <option value="income">Income</option>
                </NativeSelect>
              </div>
              <div className="space-y-2">
                <Label htmlFor={`bulk-${String(index)}-date`}>Date</Label>
                <Input
                  id={`bulk-${String(index)}-date`}
                  type="date"
                  required
                  value={row.transaction_date}
                  onChange={(event) => {
                    patchRow(index, { transaction_date: event.target.value });
                  }}
                />
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor={`bulk-${String(index)}-account`}>Account</Label>
                <NativeSelect
                  id={`bulk-${String(index)}-account`}
                  required
                  value={row.account_id}
                  onChange={(event) => {
                    patchRow(index, { account_id: event.target.value });
                  }}
                >
                  <option value="">Select account</option>
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </NativeSelect>
              </div>
              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor={`bulk-${String(index)}-category`}>Category</Label>
                <NativeSelect
                  id={`bulk-${String(index)}-category`}
                  required
                  value={row.category_id}
                  onChange={(event) => {
                    patchRow(index, { category_id: event.target.value });
                  }}
                >
                  <option value="">Select category</option>
                  {categories.map((category) => (
                    <option key={category.id} value={category.id}>
                      {category.name}
                    </option>
                  ))}
                </NativeSelect>
              </div>
              <div className="space-y-2">
                <Label htmlFor={`bulk-${String(index)}-amount`}>Amount</Label>
                <Input
                  id={`bulk-${String(index)}-amount`}
                  inputMode="decimal"
                  required
                  value={row.amount}
                  onChange={(event) => {
                    patchRow(index, { amount: event.target.value });
                  }}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor={`bulk-${String(index)}-description`}>Description</Label>
                <Input
                  id={`bulk-${String(index)}-description`}
                  value={row.description}
                  onChange={(event) => {
                    patchRow(index, { description: event.target.value });
                  }}
                />
              </div>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={rows.length <= 1}
              onClick={() => {
                removeRow(index);
              }}
            >
              Remove row
            </Button>
          </fieldset>
        ))}
      </div>
      <Button type="button" variant="secondary" onClick={addRow} disabled={rows.length >= bulkMax}>
        Add row
      </Button>
      {error ? (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      ) : null}
      <DialogFooter>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            onOpenChange(false);
          }}
        >
          Cancel
        </Button>
        <Button type="submit" disabled={mutation.isPending || overCap}>
          {mutation.isPending ? "Creating…" : "Bulk create"}
        </Button>
      </DialogFooter>
    </form>
  );
}

export function BulkTransactionsDialog({ open, onOpenChange }: BulkTransactionsDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Bulk create transactions</DialogTitle>
          <DialogDescription>
            Sends an Idempotency-Key and respects the API bulk max. Partial item failures are
            reported in the toast.
          </DialogDescription>
        </DialogHeader>
        {open ? <BulkBody key="bulk" onOpenChange={onOpenChange} /> : null}
      </DialogContent>
    </Dialog>
  );
}
