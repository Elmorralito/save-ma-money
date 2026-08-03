import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { createAccount, updateAccount } from "@/api/accounts";
import { queryKeys } from "@/api/queryKeys";
import { AccountFormFields } from "@/components/accounts/AccountFormFields";
import {
  accountFormFromResponse,
  emptyAccountFormState,
  toAccountCreate,
  toAccountUpdate,
  type AccountFormState,
} from "@/components/accounts/accountFormState";
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
import type { AccountResponse } from "@/types/domain";

type AccountFormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  account?: AccountResponse | null;
};

type AccountFormBodyProps = {
  mode: "create" | "edit";
  account?: AccountResponse | null;
  onOpenChange: (open: boolean) => void;
};

function AccountFormBody({ mode, account, onOpenChange }: AccountFormBodyProps) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<AccountFormState>(() =>
    mode === "edit" && account ? accountFormFromResponse(account) : emptyAccountFormState(),
  );
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      if (mode === "create") {
        return createAccount(toAccountCreate(form));
      }
      if (!account) {
        throw new Error("Missing account");
      }
      return updateAccount(account.id, toAccountUpdate(form));
    },
    onSuccess: async (saved) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.accounts.lists() });
      await queryClient.invalidateQueries({ queryKey: queryKeys.accounts.detail(saved.id) });
      toast.success(mode === "create" ? "Account created" : "Account updated");
      onOpenChange(false);
    },
    onError: (err: unknown) => {
      setError(formatApiError(err));
    },
  });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    try {
      if (mode === "create") {
        toAccountCreate(form);
      } else {
        toAccountUpdate(form);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid form");
      return;
    }
    mutation.mutate();
  }

  return (
    <form className="space-y-4" onSubmit={onSubmit}>
      <AccountFormFields
        idPrefix={mode === "create" ? "acct-create" : "acct-edit"}
        mode={mode}
        value={form}
        onChange={setForm}
      />
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

export function AccountFormDialog({ open, onOpenChange, mode, account }: AccountFormDialogProps) {
  const formKey = mode === "edit" ? (account?.id ?? "edit") : "create";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "Create account" : "Edit account"}</DialogTitle>
          <DialogDescription>
            Payloads follow the OpenAPI account schemas. Balance is read-only from the API.
          </DialogDescription>
        </DialogHeader>
        {open ? (
          <AccountFormBody
            key={formKey}
            mode={mode}
            account={account}
            onOpenChange={onOpenChange}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
