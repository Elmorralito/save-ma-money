import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
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
import { applyMutationError } from "@/forms/applyMutationError";
import { ACCOUNT_SERVER_FIELD_MAP } from "@/forms/fieldMaps";
import { FormRootError } from "@/forms/FormField";
import { accountFormSchema } from "@/forms/schemas/account";
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
  const form = useForm<AccountFormState>({
    resolver: zodResolver(accountFormSchema),
    defaultValues:
      mode === "edit" && account ? accountFormFromResponse(account) : emptyAccountFormState(),
  });

  const mutation = useMutation({
    mutationFn: async (values: AccountFormState) => {
      if (mode === "create") {
        return createAccount(toAccountCreate(values));
      }
      if (!account) {
        throw new Error("Missing account");
      }
      return updateAccount(account.id, toAccountUpdate(values));
    },
    onSuccess: async (saved) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.accounts.lists() });
      await queryClient.invalidateQueries({ queryKey: queryKeys.accounts.detail(saved.id) });
      toast.success(mode === "create" ? "Account created" : "Account updated");
      onOpenChange(false);
    },
    onError: (err: unknown) => {
      applyMutationError(err, {
        setError: form.setError,
        fieldMap: ACCOUNT_SERVER_FIELD_MAP,
      });
    },
  });

  const isPending = mutation.isPending || form.formState.isSubmitting;

  return (
    <form
      className="space-y-4"
      onSubmit={(event) => {
        void form.handleSubmit((values) => {
          mutation.mutate(values);
        })(event);
      }}
    >
      <AccountFormFields
        form={form}
        idPrefix={mode === "create" ? "acct-create" : "acct-edit"}
        mode={mode}
      />
      <FormRootError message={form.formState.errors.root?.message} />
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
        <Button type="submit" disabled={isPending}>
          {isPending ? "Saving…" : "Save"}
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
