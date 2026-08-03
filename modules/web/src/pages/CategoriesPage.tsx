import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { deleteCategory } from "@/api/categories";
import { categoriesListQueryOptions } from "@/api/queries";
import { queryKeys } from "@/api/queryKeys";
import { CategoryFormDialog } from "@/components/categories/CategoryFormDialog";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatApiError, isGlobalOrMissingCategoryError } from "@/lib/formatApiError";
import type { CategoryResponse } from "@/types/domain";

/** First-page list window (pagination UI deferred). */
const LIST_PARAMS = { limit: 100, skip: 0 } as const;

export function CategoriesPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<CategoryResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CategoryResponse | null>(null);
  const [readOnlyIds, setReadOnlyIds] = useState<Set<string>>(() => new Set());

  const listQuery = useQuery(categoriesListQueryOptions(LIST_PARAMS));
  const items = listQuery.data?.items ?? [];

  const deleteMutation = useMutation({
    mutationFn: (categoryId: string) => deleteCategory(categoryId),
    onSuccess: async (_void, categoryId) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.categories.lists() });
      await queryClient.removeQueries({ queryKey: queryKeys.categories.detail(categoryId) });
      toast.success("Category deleted");
      setDeleteTarget(null);
    },
    onError: (err: unknown, categoryId) => {
      if (isGlobalOrMissingCategoryError(err)) {
        const message = "This category cannot be deleted (global seed or not found).";
        setReadOnlyIds((prev) => new Set(prev).add(categoryId));
        toast.error(message);
        setDeleteTarget(null);
        return;
      }
      toast.error(formatApiError(err));
    },
  });

  function markReadOnly(categoryId: string) {
    setReadOnlyIds((prev) => new Set(prev).add(categoryId));
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Categories</h1>
          <p className="text-sm text-muted-foreground">
            Tenant categories are editable. Global seeds may appear in the list but reject writes.
          </p>
        </div>
        <Button
          type="button"
          onClick={() => {
            setCreateOpen(true);
          }}
        >
          New category
        </Button>
      </div>

      <QueryState
        isPending={listQuery.isPending}
        isError={listQuery.isError}
        error={listQuery.error}
        isEmpty={!listQuery.isPending && !listQuery.isError && items.length === 0}
        emptyTitle="No categories yet"
        emptyDescription="Create a category or wait for global seeds from the API."
        onRetry={() => {
          void listQuery.refetch();
        }}
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Children</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((category) => {
              const isReadOnly = readOnlyIds.has(category.id);
              return (
                <TableRow key={category.id}>
                  <TableCell className="font-medium">
                    {category.name}
                    {isReadOnly ? (
                      <span className="ml-2 text-xs text-muted-foreground">(read-only)</span>
                    ) : null}
                  </TableCell>
                  <TableCell className="text-muted-foreground">{category.category_type}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {category.subcategories?.length ?? 0}
                  </TableCell>
                  <TableCell>{category.is_active ? "Active" : "Inactive"}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={isReadOnly}
                        onClick={() => {
                          setEditTarget(category);
                        }}
                      >
                        Edit
                      </Button>
                      <Button
                        type="button"
                        variant="destructive"
                        size="sm"
                        disabled={isReadOnly}
                        onClick={() => {
                          setDeleteTarget(category);
                        }}
                      >
                        Delete
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
        {listQuery.data ? (
          <p className="text-xs text-muted-foreground">
            Showing {items.length} of {listQuery.data.total}
            {listQuery.data.total > LIST_PARAMS.limit
              ? ` (first ${String(LIST_PARAMS.limit)} only)`
              : ""}
          </p>
        ) : null}
      </QueryState>

      <CategoryFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        mode="create"
        parentOptions={items}
      />
      <CategoryFormDialog
        open={editTarget !== null}
        onOpenChange={(open) => {
          if (!open) {
            setEditTarget(null);
          }
        }}
        mode="edit"
        category={editTarget}
        parentOptions={items}
        onGlobalMutationBlocked={markReadOnly}
      />

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
            <DialogTitle>Delete category?</DialogTitle>
            <DialogDescription>
              Soft-deletes the category via the API. Global seeds return not found.
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
