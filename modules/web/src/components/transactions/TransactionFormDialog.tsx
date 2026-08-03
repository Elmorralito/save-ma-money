import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { invalidateAfterLedgerWrite } from "@/api/invalidateLedger";
import { accountsListQueryOptions, categoriesListQueryOptions } from "@/api/queries";
import { createTransaction, updateTransaction } from "@/api/transactions";
import {
  emptyTransactionFormState,
  toTransactionCreate,
  toTransactionUpdate,
  transactionFormFromResponse,
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
import type { TransactionResponse } from "@/types/domain";

const PICKER_PARAMS = { limit: 100, skip: 0 } as const;

type TransactionFormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  transaction?: TransactionResponse | null;
};

type TransactionFormBodyProps = {
  mode: "create" | "edit";
  transaction?: TransactionResponse | null;
  onOpenChange: (open: boolean) => void;
};

function TransactionFormBody({ mode, transaction, onOpenChange }: TransactionFormBodyProps) {
  const queryClient = useQueryClient();
  const accountsQuery = useQuery(accountsListQueryOptions(PICKER_PARAMS));
  const categoriesQuery = useQuery(categoriesListQueryOptions(PICKER_PARAMS));
  const [form, setForm] = useState<TransactionFormState>(() =>
    mode === "edit" && transaction
      ? transactionFormFromResponse(transaction)
      : emptyTransactionFormState(),
  );
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      if (mode === "create") {
        return createTransaction(toTransactionCreate(form));
      }
      if (!transaction) {
        throw new Error("Missing transaction");
      }
      return updateTransaction(transaction.id, toTransactionUpdate(form));
    },
    onSuccess: async (saved) => {
      await invalidateAfterLedgerWrite(queryClient, {
        transactions: true,
        transactionId: saved.id,
      });
      toast.success(mode === "create" ? "Transaction created" : "Transaction updated");
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
    try {
      if (mode === "create") {
        toTransactionCreate(form);
      } else {
        toTransactionUpdate(form);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid form");
      return;
    }
    mutation.mutate();
  }

  function patch(partial: Partial<TransactionFormState>) {
    setForm((prev) => ({ ...prev, ...partial }));
  }

  const idPrefix = mode === "create" ? "txn-create" : "txn-edit";
  const accounts = accountsQuery.data?.items ?? [];
  const categories = categoriesQuery.data?.items ?? [];

  return (
    <form className="space-y-4" onSubmit={onSubmit}>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-type`}>Type</Label>
          <NativeSelect
            id={`${idPrefix}-type`}
            value={form.transaction_type}
            onChange={(event) => {
              patch({ transaction_type: event.target.value as "income" | "expense" });
            }}
          >
            <option value="expense">Expense</option>
            <option value="income">Income</option>
          </NativeSelect>
        </div>
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-date`}>Date</Label>
          <Input
            id={`${idPrefix}-date`}
            type="date"
            required
            value={form.transaction_date}
            onChange={(event) => {
              patch({ transaction_date: event.target.value });
            }}
          />
        </div>
        <div className="space-y-2 sm:col-span-2">
          <Label htmlFor={`${idPrefix}-account`}>Account</Label>
          <NativeSelect
            id={`${idPrefix}-account`}
            required
            value={form.account_id}
            onChange={(event) => {
              patch({ account_id: event.target.value });
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
          <Label htmlFor={`${idPrefix}-category`}>Category</Label>
          <NativeSelect
            id={`${idPrefix}-category`}
            required
            value={form.category_id}
            onChange={(event) => {
              patch({ category_id: event.target.value });
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
          <Label htmlFor={`${idPrefix}-amount`}>Amount</Label>
          <Input
            id={`${idPrefix}-amount`}
            inputMode="decimal"
            required
            value={form.amount}
            onChange={(event) => {
              patch({ amount: event.target.value });
            }}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-currency`}>Currency</Label>
          <Input
            id={`${idPrefix}-currency`}
            value={form.currency}
            onChange={(event) => {
              patch({ currency: event.target.value });
            }}
          />
        </div>
        <div className="space-y-2 sm:col-span-2">
          <Label htmlFor={`${idPrefix}-description`}>Description</Label>
          <Input
            id={`${idPrefix}-description`}
            value={form.description}
            onChange={(event) => {
              patch({ description: event.target.value });
            }}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-reference`}>Reference</Label>
          <Input
            id={`${idPrefix}-reference`}
            value={form.reference_number}
            onChange={(event) => {
              patch({ reference_number: event.target.value });
            }}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-tags`}>Tags</Label>
          <Input
            id={`${idPrefix}-tags`}
            placeholder="comma,separated"
            value={form.tags}
            onChange={(event) => {
              patch({ tags: event.target.value });
            }}
          />
        </div>
      </div>
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
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Saving…" : "Save"}
        </Button>
      </DialogFooter>
    </form>
  );
}

export function TransactionFormDialog({
  open,
  onOpenChange,
  mode,
  transaction,
}: TransactionFormDialogProps) {
  const formKey = mode === "edit" ? (transaction?.id ?? "edit") : "create";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "Create transaction" : "Edit transaction"}</DialogTitle>
          <DialogDescription>
            Income and expense only. Transfers use the Movements page. Payloads follow OpenAPI.
          </DialogDescription>
        </DialogHeader>
        {open ? (
          <TransactionFormBody
            key={formKey}
            mode={mode}
            transaction={transaction}
            onOpenChange={onOpenChange}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
