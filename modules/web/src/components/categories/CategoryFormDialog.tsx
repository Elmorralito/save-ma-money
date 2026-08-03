import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { createCategory, updateCategory } from "@/api/categories";
import { queryKeys } from "@/api/queryKeys";
import {
  categoryFormFromResponse,
  emptyCategoryFormState,
  toCategoryCreate,
  toCategoryUpdate,
  type CategoryFormState,
} from "@/components/categories/categoryFormState";
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
import { CATEGORY_TYPE_SLUGS } from "@/lib/categoryTypes";
import { formatApiError, isGlobalOrMissingCategoryError } from "@/lib/formatApiError";
import type { CategoryResponse } from "@/types/domain";

type CategoryFormDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  category?: CategoryResponse | null;
  /** Parent options for hierarchy (tenant + seed names). */
  parentOptions: CategoryResponse[];
  onGlobalMutationBlocked?: (categoryId: string) => void;
};

type CategoryFormBodyProps = {
  mode: "create" | "edit";
  category?: CategoryResponse | null;
  parentOptions: CategoryResponse[];
  onOpenChange: (open: boolean) => void;
  onGlobalMutationBlocked?: (categoryId: string) => void;
};

function CategoryFormBody({
  mode,
  category,
  parentOptions,
  onOpenChange,
  onGlobalMutationBlocked,
}: CategoryFormBodyProps) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<CategoryFormState>(() =>
    mode === "edit" && category ? categoryFormFromResponse(category) : emptyCategoryFormState(),
  );
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      if (mode === "create") {
        return createCategory(toCategoryCreate(form));
      }
      if (!category) {
        throw new Error("Missing category");
      }
      return updateCategory(category.id, toCategoryUpdate(form));
    },
    onSuccess: async (saved) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.categories.lists() });
      await queryClient.invalidateQueries({ queryKey: queryKeys.categories.detail(saved.id) });
      toast.success(mode === "create" ? "Category created" : "Category updated");
      onOpenChange(false);
    },
    onError: (err: unknown) => {
      if (mode === "edit" && category && isGlobalOrMissingCategoryError(err)) {
        const message = "This category cannot be modified (global seed or not found).";
        setError(message);
        onGlobalMutationBlocked?.(category.id);
        toast.error(message);
        return;
      }
      setError(formatApiError(err));
    },
  });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    mutation.mutate();
  }

  function patch(partial: Partial<CategoryFormState>) {
    setForm((prev) => ({ ...prev, ...partial }));
  }

  const idPrefix = mode === "create" ? "cat-create" : "cat-edit";

  return (
    <form className="space-y-4" onSubmit={onSubmit}>
      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-name`}>Name</Label>
        <Input
          id={`${idPrefix}-name`}
          required
          maxLength={255}
          value={form.name}
          onChange={(event) => {
            patch({ name: event.target.value });
          }}
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
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-type`}>Category type</Label>
          <NativeSelect
            id={`${idPrefix}-type`}
            required
            value={form.category_type}
            onChange={(event) => {
              patch({
                category_type: event.target.value as CategoryFormState["category_type"],
              });
            }}
          >
            {CATEGORY_TYPE_SLUGS.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-parent`}>Parent</Label>
          <NativeSelect
            id={`${idPrefix}-parent`}
            value={form.parent_id}
            onChange={(event) => {
              patch({ parent_id: event.target.value });
            }}
          >
            <option value="">None</option>
            {parentOptions
              .filter((option) => option.id !== category?.id)
              .map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
          </NativeSelect>
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-icon`}>Icon</Label>
          <Input
            id={`${idPrefix}-icon`}
            maxLength={64}
            value={form.icon}
            onChange={(event) => {
              patch({ icon: event.target.value });
            }}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor={`${idPrefix}-color`}>Color</Label>
          <Input
            id={`${idPrefix}-color`}
            maxLength={7}
            placeholder="#RRGGBB"
            value={form.color}
            onChange={(event) => {
              patch({ color: event.target.value });
            }}
          />
        </div>
      </div>
      {mode === "edit" ? (
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.is_active}
            onChange={(event) => {
              patch({ is_active: event.target.checked });
            }}
          />
          Active
        </label>
      ) : null}
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

export function CategoryFormDialog({
  open,
  onOpenChange,
  mode,
  category,
  parentOptions,
  onGlobalMutationBlocked,
}: CategoryFormDialogProps) {
  const formKey = mode === "edit" ? (category?.id ?? "edit") : "create";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "Create category" : "Edit category"}</DialogTitle>
          <DialogDescription>
            Global seed categories are readable but not writable by tenants.
          </DialogDescription>
        </DialogHeader>
        {open ? (
          <CategoryFormBody
            key={formKey}
            mode={mode}
            category={category}
            parentOptions={parentOptions}
            onOpenChange={onOpenChange}
            onGlobalMutationBlocked={onGlobalMutationBlocked}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
