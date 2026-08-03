import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
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
import { NativeSelect } from "@/components/ui/native-select";
import { applyMutationError } from "@/forms/applyMutationError";
import { CATEGORY_SERVER_FIELD_MAP } from "@/forms/fieldMaps";
import { FormField, FormRootError } from "@/forms/FormField";
import { categoryFormSchema } from "@/forms/schemas/category";
import { CATEGORY_TYPE_SLUGS } from "@/lib/categoryTypes";
import { isGlobalOrMissingCategoryError } from "@/lib/formatApiError";
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
  const form = useForm<CategoryFormState>({
    resolver: zodResolver(categoryFormSchema),
    defaultValues:
      mode === "edit" && category ? categoryFormFromResponse(category) : emptyCategoryFormState(),
  });

  const mutation = useMutation({
    mutationFn: async (values: CategoryFormState) => {
      if (mode === "create") {
        return createCategory(toCategoryCreate(values));
      }
      if (!category) {
        throw new Error("Missing category");
      }
      return updateCategory(category.id, toCategoryUpdate(values));
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
        form.setError("root", { type: "server", message });
        onGlobalMutationBlocked?.(category.id);
        toast.error(message);
        return;
      }
      applyMutationError(err, {
        setError: form.setError,
        fieldMap: CATEGORY_SERVER_FIELD_MAP,
      });
    },
  });

  const idPrefix = mode === "create" ? "cat-create" : "cat-edit";
  const {
    register,
    formState: { errors },
  } = form;
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
      <FormField label="Name" htmlFor={`${idPrefix}-name`} error={errors.name?.message}>
        <Input id={`${idPrefix}-name`} maxLength={255} {...register("name")} />
      </FormField>
      <FormField
        label="Description"
        htmlFor={`${idPrefix}-description`}
        error={errors.description?.message}
      >
        <Input id={`${idPrefix}-description`} {...register("description")} />
      </FormField>
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField
          label="Category type"
          htmlFor={`${idPrefix}-type`}
          error={errors.category_type?.message}
        >
          <NativeSelect id={`${idPrefix}-type`} {...register("category_type")}>
            {CATEGORY_TYPE_SLUGS.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </NativeSelect>
        </FormField>
        <FormField label="Parent" htmlFor={`${idPrefix}-parent`} error={errors.parent_id?.message}>
          <NativeSelect id={`${idPrefix}-parent`} {...register("parent_id")}>
            <option value="">None</option>
            {parentOptions
              .filter((option) => option.id !== category?.id)
              .map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
          </NativeSelect>
        </FormField>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="Icon" htmlFor={`${idPrefix}-icon`} error={errors.icon?.message}>
          <Input id={`${idPrefix}-icon`} maxLength={64} {...register("icon")} />
        </FormField>
        <FormField label="Color" htmlFor={`${idPrefix}-color`} error={errors.color?.message}>
          <Input
            id={`${idPrefix}-color`}
            maxLength={7}
            placeholder="#RRGGBB"
            {...register("color")}
          />
        </FormField>
      </div>
      {mode === "edit" ? (
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" {...register("is_active")} />
          Active
        </label>
      ) : null}
      <FormRootError message={errors.root?.message} />
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
