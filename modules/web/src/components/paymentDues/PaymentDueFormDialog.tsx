import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { invalidateAfterTemplateWrite } from "@/api/invalidateLedger";
import { accountsListQueryOptions, categoriesListQueryOptions } from "@/api/queries";
import { createTransactionTemplate, updateTransactionTemplate } from "@/api/transactionTemplates";
import {
  emptyPaymentDueFormState,
  paymentDueFormFromResponse,
  toTransactionTemplateCreate,
  toTransactionTemplateUpdate,
  type PaymentDueFormState,
  type PaymentDueSchedule,
} from "@/components/paymentDues/paymentDueFormState";
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
import type { TransactionTemplateResponse } from "@/types/domain";

const PICKER_PARAMS = { limit: 100, skip: 0 } as const;

type PaymentDueFormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  template?: TransactionTemplateResponse | null;
};

type PaymentDueFormBodyProps = {
  mode: "create" | "edit";
  template?: TransactionTemplateResponse | null;
  onOpenChange: (open: boolean) => void;
};

function PaymentDueFormBody({ mode, template, onOpenChange }: PaymentDueFormBodyProps) {
  const queryClient = useQueryClient();
  const accountsQuery = useQuery(accountsListQueryOptions(PICKER_PARAMS));
  const categoriesQuery = useQuery(categoriesListQueryOptions(PICKER_PARAMS));
  const [form, setForm] = useState<PaymentDueFormState>(() =>
    mode === "edit" && template ? paymentDueFormFromResponse(template) : emptyPaymentDueFormState(),
  );
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      if (mode === "create") {
        return createTransactionTemplate(toTransactionTemplateCreate(form));
      }
      if (!template) {
        throw new Error("Missing payment due");
      }
      return updateTransactionTemplate(template.id, toTransactionTemplateUpdate(form));
    },
    onSuccess: async (saved) => {
      await invalidateAfterTemplateWrite(queryClient, { templateId: saved.id });
      toast.success(mode === "create" ? "Payment due created" : "Payment due updated");
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
        toTransactionTemplateCreate(form);
      } else {
        toTransactionTemplateUpdate(form);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid form");
      return;
    }
    mutation.mutate();
  }

  function patch(partial: Partial<PaymentDueFormState>) {
    setForm((prev) => ({ ...prev, ...partial }));
  }

  const idPrefix = mode === "create" ? "due-create" : "due-edit";
  const accounts = accountsQuery.data?.items ?? [];
  const categories = categoriesQuery.data?.items ?? [];

  return (
    <form className="space-y-4" onSubmit={onSubmit}>
      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-name`}>Name</Label>
        <Input
          id={`${idPrefix}-name`}
          value={form.name}
          onChange={(event) => {
            patch({ name: event.target.value });
          }}
          placeholder="Rent, credit card, utilities…"
          required
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-description`}>Description</Label>
        <Input
          id={`${idPrefix}-description`}
          value={form.description}
          onChange={(event) => {
            patch({ description: event.target.value });
          }}
        />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-category`}>Category</Label>
          <NativeSelect
            id={`${idPrefix}-category`}
            value={form.category_id}
            onChange={(event) => {
              patch({ category_id: event.target.value });
            }}
            required
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
          <Label htmlFor={`${idPrefix}-from-account`}>Pay from (optional)</Label>
          <NativeSelect
            id={`${idPrefix}-from-account`}
            value={form.from_account_id}
            onChange={(event) => {
              patch({ from_account_id: event.target.value });
            }}
          >
            <option value="">Not set</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </NativeSelect>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-amount`}>Planned amount</Label>
          <Input
            id={`${idPrefix}-amount`}
            inputMode="decimal"
            value={form.planned_amount}
            onChange={(event) => {
              patch({ planned_amount: event.target.value });
            }}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-schedule`}>Schedule</Label>
          <NativeSelect
            id={`${idPrefix}-schedule`}
            value={form.schedule}
            onChange={(event) => {
              patch({ schedule: event.target.value as PaymentDueSchedule });
            }}
          >
            <option value="recurring">Recurring monthly</option>
            <option value="one_off">One-off deadline</option>
          </NativeSelect>
        </div>
      </div>

      {form.schedule === "recurring" ? (
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor={`${idPrefix}-planned-day`}>Day of month</Label>
            <Input
              id={`${idPrefix}-planned-day`}
              inputMode="numeric"
              value={form.planned_day}
              onChange={(event) => {
                patch({ planned_day: event.target.value });
              }}
              disabled={form.use_month_end}
              required={!form.use_month_end}
            />
          </div>
          <div className="flex items-end gap-2 pb-2">
            <input
              id={`${idPrefix}-month-end`}
              type="checkbox"
              checked={form.use_month_end}
              onChange={(event) => {
                patch({ use_month_end: event.target.checked });
              }}
            />
            <Label htmlFor={`${idPrefix}-month-end`}>Use month end</Label>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-due-date`}>Due date</Label>
          <Input
            id={`${idPrefix}-due-date`}
            type="date"
            value={form.due_date}
            onChange={(event) => {
              patch({ due_date: event.target.value });
            }}
            required
          />
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-remind`}>Remind days before</Label>
          <Input
            id={`${idPrefix}-remind`}
            inputMode="numeric"
            value={form.remind_days_before}
            onChange={(event) => {
              patch({ remind_days_before: event.target.value });
            }}
            placeholder="Optional"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-tags`}>Tags</Label>
          <Input
            id={`${idPrefix}-tags`}
            value={form.tags}
            onChange={(event) => {
              patch({ tags: event.target.value });
            }}
            placeholder="comma, separated"
          />
        </div>
      </div>

      {mode === "edit" ? (
        <div className="flex items-center gap-2">
          <input
            id={`${idPrefix}-active`}
            type="checkbox"
            checked={form.is_active}
            onChange={(event) => {
              patch({ is_active: event.target.checked });
            }}
          />
          <Label htmlFor={`${idPrefix}-active`}>Active</Label>
        </div>
      ) : null}

      {error ? (
        <p className="text-sm text-destructive" role="alert">
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

export function PaymentDueFormDialog({
  open,
  onOpenChange,
  mode,
  template,
}: PaymentDueFormDialogProps) {
  const formKey = mode === "edit" ? (template?.id ?? "edit") : "create";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "New payment due" : "Edit payment due"}</DialogTitle>
          <DialogDescription>
            Recurring bills and one-off deadlines. Due dates and mark-paid live in the API — this
            screen only collects the fields.
          </DialogDescription>
        </DialogHeader>
        {open ? (
          <PaymentDueFormBody
            key={formKey}
            mode={mode}
            template={template}
            onOpenChange={onOpenChange}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
