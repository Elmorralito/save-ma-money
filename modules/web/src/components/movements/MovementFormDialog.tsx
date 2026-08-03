import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { invalidateAfterLedgerWrite } from "@/api/invalidateLedger";
import { createMovement, updateMovement } from "@/api/movements";
import { accountsListQueryOptions } from "@/api/queries";
import {
  emptyMovementFormState,
  movementFormFromResponse,
  toMovementCreate,
  toMovementUpdate,
  type MovementFormState,
} from "@/components/movements/movementFormState";
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
import type { MovementResponse } from "@/types/domain";

const PICKER_PARAMS = { limit: 100, skip: 0 } as const;

type MovementFormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  movement?: MovementResponse | null;
};

type MovementFormBodyProps = {
  mode: "create" | "edit";
  movement?: MovementResponse | null;
  onOpenChange: (open: boolean) => void;
};

function MovementFormBody({ mode, movement, onOpenChange }: MovementFormBodyProps) {
  const queryClient = useQueryClient();
  const accountsQuery = useQuery(accountsListQueryOptions(PICKER_PARAMS));
  const [form, setForm] = useState<MovementFormState>(() =>
    mode === "edit" && movement ? movementFormFromResponse(movement) : emptyMovementFormState(),
  );
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      if (mode === "create") {
        return createMovement(toMovementCreate(form));
      }
      if (!movement) {
        throw new Error("Missing movement");
      }
      return updateMovement(movement.id, toMovementUpdate(form));
    },
    onSuccess: async (saved) => {
      await invalidateAfterLedgerWrite(queryClient, {
        transactions: true,
        movements: true,
        movementId: saved.id,
      });
      toast.success(mode === "create" ? "Movement created" : "Movement updated");
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
        toMovementCreate(form);
      } else {
        toMovementUpdate(form);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid form");
      return;
    }
    mutation.mutate();
  }

  function patch(partial: Partial<MovementFormState>) {
    setForm((prev) => ({ ...prev, ...partial }));
  }

  const idPrefix = mode === "create" ? "mov-create" : "mov-edit";
  const accounts = accountsQuery.data?.items ?? [];

  return (
    <form className="space-y-4" onSubmit={onSubmit}>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2 sm:col-span-2">
          <Label htmlFor={`${idPrefix}-source`}>Source account</Label>
          <NativeSelect
            id={`${idPrefix}-source`}
            required
            value={form.source_account_id}
            onChange={(event) => {
              patch({ source_account_id: event.target.value });
            }}
          >
            <option value="">Select source</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="space-y-2 sm:col-span-2">
          <Label htmlFor={`${idPrefix}-destination`}>Destination account</Label>
          <NativeSelect
            id={`${idPrefix}-destination`}
            required
            value={form.destination_account_id}
            onChange={(event) => {
              patch({ destination_account_id: event.target.value });
            }}
          >
            <option value="">Select destination</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
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
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-date`}>Date</Label>
          <Input
            id={`${idPrefix}-date`}
            type="date"
            required
            value={form.movement_date}
            onChange={(event) => {
              patch({ movement_date: event.target.value });
            }}
          />
        </div>
        {mode === "create" ? (
          <div className="flex items-end gap-2 pb-1">
            <input
              id={`${idPrefix}-scheduled`}
              type="checkbox"
              className="size-4"
              checked={form.scheduled}
              onChange={(event) => {
                patch({ scheduled: event.target.checked });
              }}
            />
            <Label htmlFor={`${idPrefix}-scheduled`}>Schedule (leave pending until Execute)</Label>
          </div>
        ) : null}
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

export function MovementFormDialog({
  open,
  onOpenChange,
  mode,
  movement,
}: MovementFormDialogProps) {
  const formKey = mode === "edit" ? (movement?.id ?? "edit") : "create";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "Create movement" : "Edit movement"}</DialogTitle>
          <DialogDescription>
            Transfers use API status semantics. Immediate creates auto-complete; scheduled stays
            pending until Execute.
          </DialogDescription>
        </DialogHeader>
        {open ? (
          <MovementFormBody
            key={formKey}
            mode={mode}
            movement={movement}
            onOpenChange={onOpenChange}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
