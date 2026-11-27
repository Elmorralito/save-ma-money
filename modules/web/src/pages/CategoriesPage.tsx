import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { deleteCategory } from "@/api/categories";
import { categoriesListQueryOptions } from "@/api/queries";
import { queryKeys } from "@/api/queryKeys";
import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import { CategoryFormDialog } from "@/components/categories/CategoryFormDialog";
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
import { formatApiError, isGlobalOrMissingCategoryError } from "@/lib/formatApiError";
import { formatSlugLabel } from "@/lib/formatSlugLabel";
import type { CategoryResponse } from "@/types/domain";

type CategorySortKey = "name" | "type" | "children" | "status";

export function CategoriesPage() {
  const queryClient = useQueryClient();
  const { locale, messages } = useLocale();
  const ct = messages.categories;
  const categoriesAi = useScopedAIToggle();
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<CategoryResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CategoryResponse | null>(null);
  const [readOnlyIds, setReadOnlyIds] = useState<Set<string>>(() => new Set());
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState(() => searchParams.get("search") ?? "");
  const [categoryType, setCategoryType] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(DEFAULT_PAGE_SIZE);
  const [sort, setSort] = useState<SortState<CategorySortKey>>({ key: "name", direction: "asc" });

  const hasSearch = search.trim() !== "";
  const listParams = useMemo(
    () => ({
      limit: hasSearch ? 100 : pageSize,
      skip: hasSearch ? 0 : (page - 1) * pageSize,
      ...(categoryType ? { category_type: categoryType } : {}),
    }),
    [categoryType, hasSearch, page, pageSize],
  );

  const listQuery = useQuery(categoriesListQueryOptions(listParams));
  const rawItems = listQuery.data?.items ?? [];

  const filteredItems = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rawItems;
    return rawItems.filter(
      (cat) =>
        cat.name.toLowerCase().includes(q) ||
        formatSlugLabel(cat.category_type).toLowerCase().includes(q),
    );
  }, [rawItems, search]);

  const sortedItems = useMemo(
    () =>
      sortItems(filteredItems, sort, {
        name: (c) => c.name,
        type: (c) => c.category_type,
        children: (c) => c.subcategories?.length ?? 0,
        status: (c) => (c.is_active ? 1 : 0),
      }),
    [filteredItems, sort],
  );

  const displayItems = useMemo(() => {
    if (!hasSearch) return sortedItems;
    const start = (page - 1) * pageSize;
    return sortedItems.slice(start, start + pageSize);
  }, [hasSearch, page, pageSize, sortedItems]);

  const total = hasSearch ? sortedItems.length : (listQuery.data?.total ?? sortedItems.length);
  const hasActiveFilters = search.trim() !== "" || categoryType !== "";

  const deleteMutation = useMutation({
    mutationFn: (categoryId: string) => deleteCategory(categoryId),
    onSuccess: async (_void, categoryId) => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.categories.lists() });
      await queryClient.removeQueries({ queryKey: queryKeys.categories.detail(categoryId) });
      await queryClient.invalidateQueries({ queryKey: queryKeys.reports.all });
      toast.success(ct.deletedToast);
      setDeleteTarget(null);
    },
    onError: (err: unknown, categoryId) => {
      if (isGlobalOrMissingCategoryError(err)) {
        const message = ct.deleteBlockedToast;
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

  function clearFilters() {
    setSearch("");
    setCategoryType("");
    setPage(1);
    if (searchParams.has("search")) {
      const next = new URLSearchParams(searchParams);
      next.delete("search");
      setSearchParams(next, { replace: true });
    }
  }

  function categoryTypeLabel(slug: string): string {
    if (slug === "income") return ct.income;
    if (slug === "expense") return ct.expense;
    return formatSlugLabel(slug);
  }

  function renderCategoriesSection(
    variantClass: string,
    badgeStyle: "plain" | "tinted" | "compact",
  ) {
    return (
      <div className={`mx-auto w-full max-w-6xl ${variantClass}`}>
        <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight text-balance">{ct.title}</h1>
            <p className="text-sm text-muted-foreground text-pretty">{ct.subtitle}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <ScopedAITrigger
              open={categoriesAi.open}
              panelId={categoriesAi.panelId}
              onToggle={categoriesAi.toggle}
              compact={false}
            />
            <Button
              type="button"
              onClick={() => {
                setCreateOpen(true);
              }}
            >
              {ct.newCategory}
            </Button>
          </div>
        </header>

        <ScopedAIPanel
          id={categoriesAi.panelId}
          open={categoriesAi.open}
          onClose={categoriesAi.close}
          module="categories"
          view="taxonomy"
          control="categories-table"
          title={ct.title}
          surfaceContext={{
            total_matching: total,
            category_type: categoryType || "all",
            search: search || null,
            visible_categories: displayItems.slice(0, 15).map((c) => ({
              name: c.name,
              type: c.category_type,
              subcategories_count: c.subcategories?.length ?? 0,
              is_active: c.is_active,
            })),
          }}
          suggestedPrompts={
            locale === "es-CO"
              ? [
                  "Revisa esta taxonomía y sugiere cómo organizar mejor ingresos y gastos.",
                  "¿Qué categorías conviene agrupar o subclasificar para mejores reportes?",
                ]
              : [
                  "Review this category taxonomy and suggest cleaner waterfall grouping.",
                  "How could I structure subcategories for clearer spending reports?",
                ]
          }
        />

        <div className="grid gap-3 rounded-2xl border border-border bg-card p-4 shadow-xs sm:grid-cols-3">
          <div className="space-y-1.5 sm:col-span-2">
            <Label htmlFor="categories-filter-search">{ct.searchLabel}</Label>
            <Input
              id="categories-filter-search"
              placeholder={ct.searchPlaceholder}
              value={search}
              onChange={(event) => {
                setSearch(event.target.value);
                setPage(1);
              }}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="categories-filter-type">{ct.typeLabel}</Label>
            <div className="flex items-center gap-2">
              <NativeSelect
                id="categories-filter-type"
                value={categoryType}
                onChange={(event) => {
                  setCategoryType(event.target.value);
                  setPage(1);
                }}
              >
                <option value="">{ct.allTypes}</option>
                <option value="income">{ct.income}</option>
                <option value="expense">{ct.expense}</option>
              </NativeSelect>
              {hasActiveFilters ? (
                <Button type="button" variant="ghost" size="sm" onClick={clearFilters}>
                  {ct.clear}
                </Button>
              ) : null}
            </div>
          </div>
        </div>

        <QueryState
          isPending={listQuery.isPending}
          isError={listQuery.isError}
          error={listQuery.error}
          isEmpty={!listQuery.isPending && !listQuery.isError && displayItems.length === 0}
          emptyTitle={hasActiveFilters ? ct.emptyFilteredTitle : ct.emptyTitle}
          emptyDescription={hasActiveFilters ? ct.emptyFilteredDescription : ct.emptyDescription}
          emptyAction={
            hasActiveFilters ? (
              <Button type="button" variant="outline" onClick={clearFilters}>
                {ct.clearFilters}
              </Button>
            ) : (
              <Button
                type="button"
                onClick={() => {
                  setCreateOpen(true);
                }}
              >
                {ct.createFirst}
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
                    label={ct.colName}
                    sortKey="name"
                    sort={sort}
                    onSort={(key) => {
                      setSort((prev) => toggleSort(prev, key));
                    }}
                  />
                  <SortableTableHead
                    label={ct.colType}
                    sortKey="type"
                    sort={sort}
                    onSort={(key) => {
                      setSort((prev) => toggleSort(prev, key));
                    }}
                  />
                  <SortableTableHead
                    label={ct.colChildren}
                    sortKey="children"
                    sort={sort}
                    onSort={(key) => {
                      setSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                  />
                  <SortableTableHead
                    label={ct.colStatus}
                    sortKey="status"
                    sort={sort}
                    onSort={(key) => {
                      setSort((prev) => toggleSort(prev, key, "desc"));
                    }}
                  />
                  <TableHead className="text-right">{ct.colActions}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {displayItems.map((category) => {
                  const isReadOnly = readOnlyIds.has(category.id);
                  return (
                    <TableRow
                      key={category.id}
                      className={badgeStyle === "compact" ? "h-10" : undefined}
                    >
                      <TableCell className="font-medium">
                        {category.name}
                        {isReadOnly ? (
                          <span className="ml-2 text-xs text-muted-foreground">
                            {ct.readOnlyTag}
                          </span>
                        ) : null}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {badgeStyle === "tinted" ? (
                          <span
                            className={
                              category.category_type === "income"
                                ? "inline-flex rounded-full bg-emerald-500/12 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-300"
                                : "inline-flex rounded-full bg-slate-500/12 px-2.5 py-0.5 text-xs font-medium text-slate-700 dark:text-slate-300"
                            }
                          >
                            {categoryTypeLabel(category.category_type)}
                          </span>
                        ) : (
                          categoryTypeLabel(category.category_type)
                        )}
                      </TableCell>
                      <TableCell className="tabular-nums text-muted-foreground">
                        {category.subcategories?.length ?? 0}
                      </TableCell>
                      <TableCell>
                        <span
                          className={
                            category.is_active
                              ? "inline-flex rounded-full bg-success-soft px-2.5 py-0.5 text-xs font-medium text-success"
                              : "inline-flex rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium text-muted-foreground"
                          }
                        >
                          {category.is_active ? ct.active : ct.inactive}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1.5">
                          <ActionIconButton
                            icon={Pencil}
                            label={isReadOnly ? ct.readOnlyAction : ct.editCategory}
                            tone="sky"
                            disabled={isReadOnly}
                            onClick={() => {
                              setEditTarget(category);
                            }}
                          />
                          <ActionIconButton
                            icon={Trash2}
                            label={isReadOnly ? ct.readOnlyAction : ct.deleteCategory}
                            tone="rose"
                            disabled={isReadOnly}
                            onClick={() => {
                              setDeleteTarget(category);
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
              visibleCount={displayItems.length}
              onPageChange={setPage}
              onPageSizeChange={(nextSize) => {
                setPageSize(nextSize);
                setPage(1);
              }}
            />
          </div>
        </QueryState>

        <CategoryFormDialog
          open={createOpen}
          onOpenChange={setCreateOpen}
          mode="create"
          parentOptions={rawItems}
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
          parentOptions={rawItems}
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
              <DialogTitle>{ct.deleteTitle}</DialogTitle>
              <DialogDescription>{ct.deleteDescription}</DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setDeleteTarget(null);
                }}
              >
                {ct.cancel}
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
                {deleteMutation.isPending ? ct.deleting : ct.delete}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    );
  }

  return renderCategoriesSection("space-y-5", "tinted");
}
