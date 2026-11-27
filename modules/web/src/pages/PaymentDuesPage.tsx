import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  CheckCircle2,
  CircleCheckBig,
  Landmark,
  Link2,
  Pencil,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import { invalidateAfterTemplateWrite } from "@/api/invalidateLedger";
import {
  accountsListQueryOptions,
  categoriesListQueryOptions,
  transactionTemplatesListQueryOptions,
  transactionsListQueryOptions,
} from "@/api/queries";
import {
  clearTemplatePaid,
  deleteTransactionTemplate,
  markTemplatePaid,
} from "@/api/transactionTemplates";
import { getAIConfig } from "@/api/ai";
import { ScopedAIPanel, ScopedAITrigger, useScopedAIToggle } from "@/components/ai/ScopedAICopilot";
import { PaymentDueFormDialog } from "@/components/paymentDues/PaymentDueFormDialog";
import { QueryState } from "@/components/QueryState";
import {
  SortableTableHead,
  sortItems,
  toggleSort,
  type SortState,
} from "@/components/table/SortableTableHead";
import { DEFAULT_PAGE_SIZE, TablePagination } from "@/components/table/TablePagination";
import { ActionIconButton as DueActionButton } from "@/components/ui/action-icon-button";
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
import { formatApiError } from "@/lib/formatApiError";
import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import type { TransactionTemplateResponse } from "@/types/domain";

const CATEGORY_PICKER_PARAMS = { limit: 100, skip: 0 } as const;
const RECENT_TXNS_PARAMS = { limit: 100, skip: 0, exclude_transfer: true } as const;

type DueSortKey = "name" | "schedule" | "amount" | "remind";

function currentMonthDueDateIso(template: TransactionTemplateResponse): string {
  if (template.due_date) {
    return template.due_date;
  }
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth(); // 0-indexed
  const lastDayOfMonth = new Date(year, month + 1, 0).getDate();
  const day = template.use_month_end
    ? lastDayOfMonth
    : Math.min(Math.max(1, template.planned_day), lastDayOfMonth);
  const mm = String(month + 1).padStart(2, "0");
  const dd = String(day).padStart(2, "0");
  return `${String(year)}-${mm}-${dd}`;
}

function scheduleCadenceLabel(
  template: TransactionTemplateResponse,
  labels: { oneOff: string; monthlyEnd: string; monthlyDayPrefix: string },
): string {
  if (template.due_date) {
    return labels.oneOff;
  }
  if (template.use_month_end) {
    return labels.monthlyEnd;
  }
  return `${labels.monthlyDayPrefix} ${String(template.planned_day)}`;
}

export function PaymentDuesPage() {
  const queryClient = useQueryClient();
  const { locale, messages } = useLocale();
  const pt = messages.paymentDues;
  const duesAi = useScopedAIToggle();
  const aiConfigQuery = useQuery({
    queryKey: ["ai-config"],
    queryFn: ({ signal }) => getAIConfig(signal),
    staleTime: 60_000,
  });
  const duesAiEnabled = aiConfigQuery.data?.payment_dues_ai_enabled ?? true;
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<TransactionTemplateResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<TransactionTemplateResponse | null>(null);
  const [search, setSearch] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [activeOnly, setActiveOnly] = useState(true);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState<number>(DEFAULT_PAGE_SIZE);
  const [sort, setSort] = useState<SortState<DueSortKey>>({ key: "schedule", direction: "asc" });

  const hasSearch = search.trim() !== "";
  const listParams = useMemo(
    () => ({
      limit: hasSearch ? 100 : pageSize,
      skip: hasSearch ? 0 : (page - 1) * pageSize,
      ...(categoryId ? { category_id: categoryId } : {}),
      ...(activeOnly ? { is_active: true } : {}),
    }),
    [activeOnly, categoryId, hasSearch, page, pageSize],
  );

  const listQuery = useQuery(transactionTemplatesListQueryOptions(listParams));
  const categoriesQuery = useQuery(categoriesListQueryOptions(CATEGORY_PICKER_PARAMS));
  const accountsQuery = useQuery(accountsListQueryOptions(CATEGORY_PICKER_PARAMS));
  const transactionsQuery = useQuery(transactionsListQueryOptions(RECENT_TXNS_PARAMS));
  const rawItems = listQuery.data?.items ?? [];
  const categories = categoriesQuery.data?.items ?? [];
  const accounts = accountsQuery.data?.items ?? [];
  const transactions = transactionsQuery.data?.items ?? [];

  const accountById = useMemo(() => {
    const map = new Map<string, { id: string; name: string; currency: string }>();
    for (const acc of accounts) {
      map.set(acc.id, { id: acc.id, name: acc.name, currency: acc.currency });
    }
    return map;
  }, [accounts]);

  const categoryNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const cat of categories) {
      map.set(cat.id, cat.name);
    }
    return map;
  }, [categories]);

  const wiredTxnsByTemplateId = useMemo(() => {
    const map = new Map<
      string,
      {
        count: number;
        latest: { id: string; amount: number; currency: string; date: string; description: string };
      }
    >();
    for (const txn of transactions) {
      if (!txn.template_id) continue;
      const prev = map.get(txn.template_id);
      const ts = txn.transaction_date ?? "";
      if (!prev) {
        map.set(txn.template_id, {
          count: 1,
          latest: {
            id: txn.id,
            amount: txn.amount,
            currency: txn.currency,
            date: ts,
            description: txn.description,
          },
        });
      } else {
        const newer = ts > prev.latest.date;
        map.set(txn.template_id, {
          count: prev.count + 1,
          latest: newer
            ? {
                id: txn.id,
                amount: txn.amount,
                currency: txn.currency,
                date: ts,
                description: txn.description,
              }
            : prev.latest,
        });
      }
    }
    return map;
  }, [transactions]);

  const filteredItems = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rawItems;
    return rawItems.filter(
      (tmpl) => tmpl.name.toLowerCase().includes(q) || tmpl.description.toLowerCase().includes(q),
    );
  }, [rawItems, search]);

  const sortedItems = useMemo(
    () =>
      sortItems(filteredItems, sort, {
        name: (t) => t.name,
        schedule: (t) => currentMonthDueDateIso(t),
        amount: (t) => t.planned_amount,
        remind: (t) => t.remind_days_before ?? -1,
      }),
    [filteredItems, sort],
  );

  const displayItems = useMemo(() => {
    if (!hasSearch) return sortedItems;
    const start = (page - 1) * pageSize;
    return sortedItems.slice(start, start + pageSize);
  }, [hasSearch, page, pageSize, sortedItems]);

  const total = hasSearch ? sortedItems.length : (listQuery.data?.total ?? sortedItems.length);
  const hasActiveFilters = search.trim() !== "" || categoryId !== "" || !activeOnly;

  const markPaidMutation = useMutation({
    mutationFn: (templateId: string) => markTemplatePaid(templateId),
    onSuccess: async (txn, templateId) => {
      await invalidateAfterTemplateWrite(queryClient, {
        templateId,
        markPaid: true,
        transactionId: txn.id,
      });
      toast.success(pt.markedPaidToast);
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err));
    },
  });

  const clearPaidMutation = useMutation({
    mutationFn: (templateId: string) => clearTemplatePaid(templateId),
    onSuccess: async (_txn, templateId) => {
      await invalidateAfterTemplateWrite(queryClient, {
        templateId,
        markPaid: true,
      });
      toast.success(pt.clearedPaidToast);
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (templateId: string) => deleteTransactionTemplate(templateId),
    onSuccess: async (_void, templateId) => {
      await invalidateAfterTemplateWrite(queryClient, { removeTemplateId: templateId });
      toast.success(pt.deletedToast);
      setDeleteTarget(null);
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err));
    },
  });

  const actionPending =
    markPaidMutation.isPending || clearPaidMutation.isPending || deleteMutation.isPending;

  function clearFilters() {
    setSearch("");
    setCategoryId("");
    setActiveOnly(true);
    setPage(1);
  }

  return (
    <div className="mx-auto w-full max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-5">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight text-balance">{pt.title}</h1>
          <p className="text-sm text-muted-foreground text-pretty">{pt.subtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {duesAiEnabled ? (
            <ScopedAITrigger
              open={duesAi.open}
              panelId={duesAi.panelId}
              onToggle={duesAi.toggle}
              compact={false}
            />
          ) : null}
          <Button
            type="button"
            onClick={() => {
              setCreateOpen(true);
            }}
          >
            {pt.newPaymentDue}
          </Button>
        </div>
      </header>

      <ScopedAIPanel
        id={duesAi.panelId}
        open={duesAiEnabled && duesAi.open}
        onClose={duesAi.close}
        module="payment-dues"
        view="templates"
        control="payment-dues-table"
        title={pt.title}
        surfaceContext={{
          total_matching: total,
          search: search || null,
          category_id: categoryId || null,
          active_only: activeOnly,
          sort,
          visible_templates: displayItems.slice(0, 15).map((d) => ({
            name: d.name,
            schedule: currentMonthDueDateIso(d),
            amount: d.planned_amount,
            has_wired_payment: Boolean(wiredTxnsByTemplateId.get(d.id)?.count),
          })),
        }}
        suggestedPrompts={
          locale === "es-CO"
            ? [
                "Ordena por urgencia e impacto mis próximos compromisos recurrentes.",
                "¿Qué vencimientos aún no tienen pago vinculado?",
              ]
            : [
                "Prioritize these recurring commitments by due date and cash impact.",
                "Which visible due templates still lack a wired ledger payment?",
              ]
        }
      />

      <div className="grid gap-3 rounded-2xl border border-border bg-card p-4 shadow-xs sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-1.5 lg:col-span-2">
          <Label htmlFor="dues-filter-search">{pt.searchLabel}</Label>
          <Input
            id="dues-filter-search"
            placeholder={pt.searchPlaceholder}
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="dues-filter-category">{pt.categoryLabel}</Label>
          <NativeSelect
            id="dues-filter-category"
            value={categoryId}
            onChange={(event) => {
              setCategoryId(event.target.value);
              setPage(1);
            }}
          >
            <option value="">{pt.allCategories}</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="dues-filter-status">{pt.statusLabel}</Label>
          <div className="flex items-center gap-2">
            <NativeSelect
              id="dues-filter-status"
              value={activeOnly ? "active" : "all"}
              onChange={(event) => {
                setActiveOnly(event.target.value === "active");
                setPage(1);
              }}
            >
              <option value="active">{pt.activeOnly}</option>
              <option value="all">{pt.allDues}</option>
            </NativeSelect>
            {hasActiveFilters ? (
              <Button type="button" variant="ghost" size="sm" onClick={clearFilters}>
                {pt.clear}
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
        emptyTitle={hasActiveFilters ? pt.emptyFilteredTitle : pt.emptyTitle}
        emptyDescription={hasActiveFilters ? pt.emptyFilteredDescription : pt.emptyDescription}
        emptyAction={
          hasActiveFilters ? (
            <Button type="button" variant="outline" onClick={clearFilters}>
              {pt.clearFilters}
            </Button>
          ) : (
            <Button
              type="button"
              onClick={() => {
                setCreateOpen(true);
              }}
            >
              {pt.createFirst}
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
                  label={pt.colName}
                  sortKey="name"
                  sort={sort}
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key));
                  }}
                />
                <SortableTableHead
                  label={pt.colSchedule}
                  sortKey="schedule"
                  sort={sort}
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key));
                  }}
                />
                <TableHead>{pt.colAccountMarkers}</TableHead>
                <TableHead>{pt.colWiredPayments}</TableHead>
                <SortableTableHead
                  label={pt.colAmount}
                  sortKey="amount"
                  sort={sort}
                  align="right"
                  onSort={(key) => {
                    setSort((prev) => toggleSort(prev, key, "desc"));
                  }}
                />
                <TableHead className="text-right">{pt.colActions}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayItems.map((template) => {
                const account = template.from_account_id
                  ? accountById.get(template.from_account_id)
                  : undefined;
                const categoryName = categoryNameById.get(template.category_id);
                const wired = wiredTxnsByTemplateId.get(template.id);
                const markerTags = (template.tags ?? []).filter((t) => t !== "imported");

                return (
                  <TableRow key={template.id}>
                    <TableCell>
                      <div className="space-y-0.5">
                        <p className="font-medium">{template.name}</p>
                        {categoryName ? (
                          <p className="text-xs text-muted-foreground">{categoryName}</p>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-0.5">
                        <p className="font-medium tabular-nums text-foreground">
                          {formatDate(currentMonthDueDateIso(template))}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {scheduleCadenceLabel(template, pt)}
                          {template.remind_days_before !== null &&
                          template.remind_days_before !== undefined
                            ? ` · ${pt.remindPrefix} ${String(template.remind_days_before)}${pt.remindSuffix}`
                            : ""}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1.5">
                        {account ? (
                          <Link
                            to={`/accounts/${account.id}`}
                            className="inline-flex items-center gap-1.5 text-xs font-medium text-primary hover:underline"
                          >
                            <Landmark aria-hidden="true" className="size-3.5 shrink-0" />
                            <span>{account.name}</span>
                          </Link>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            {pt.noAccountLinked}
                          </span>
                        )}
                        {markerTags.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {markerTags.slice(0, 4).map((tag) => (
                              <span
                                key={tag}
                                className="inline-flex rounded-full border border-border bg-muted/60 px-2 py-0.5 text-[10px] font-medium text-muted-foreground"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell>
                      {wired ? (
                        <Link
                          to="/transactions"
                          className="group inline-flex flex-col gap-0.5 text-xs hover:text-primary"
                        >
                          <span className="inline-flex items-center gap-1 font-medium text-emerald-700 dark:text-emerald-400">
                            <CheckCircle2 aria-hidden="true" className="size-3.5 shrink-0" />
                            {formatMoney(wired.latest.amount, wired.latest.currency)}
                          </span>
                          <span className="inline-flex items-center gap-1 text-muted-foreground">
                            <Link2 aria-hidden="true" className="size-3 shrink-0" />
                            {wired.latest.date ? formatDate(wired.latest.date) : pt.recent} ·{" "}
                            {wired.count}{" "}
                            {wired.count === 1 ? pt.paymentSingular : pt.paymentPlural}
                          </span>
                        </Link>
                      ) : (
                        <span className="text-xs text-muted-foreground">{pt.noWiredPayments}</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums">
                      {formatMoney(template.planned_amount, account?.currency ?? "COP")}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="inline-flex items-center justify-end gap-1.5">
                        <DueActionButton
                          icon={CircleCheckBig}
                          label={pt.markPaid}
                          tone="emerald"
                          disabled={actionPending}
                          onClick={() => {
                            markPaidMutation.mutate(template.id);
                          }}
                        />
                        <DueActionButton
                          icon={RotateCcw}
                          label={pt.clearPaidStatus}
                          tone="amber"
                          disabled={actionPending}
                          onClick={() => {
                            clearPaidMutation.mutate(template.id);
                          }}
                        />
                        <DueActionButton
                          icon={Pencil}
                          label={pt.editPaymentDue}
                          tone="sky"
                          disabled={actionPending}
                          onClick={() => {
                            setEditTarget(template);
                          }}
                        />
                        <DueActionButton
                          icon={Trash2}
                          label={pt.deletePaymentDue}
                          tone="rose"
                          disabled={actionPending}
                          onClick={() => {
                            setDeleteTarget(template);
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

      <PaymentDueFormDialog open={createOpen} onOpenChange={setCreateOpen} mode="create" />
      <PaymentDueFormDialog
        open={editTarget !== null}
        onOpenChange={(open) => {
          if (!open) {
            setEditTarget(null);
          }
        }}
        mode="edit"
        template={editTarget}
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
            <DialogTitle>{pt.deleteTitle}</DialogTitle>
            <DialogDescription>
              {pt.deleteDescriptionPrefix} “{deleteTarget?.name ?? pt.deleteThisDue}”.{" "}
              {pt.deleteDescriptionSuffix}
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
              {pt.cancel}
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
              {deleteMutation.isPending ? pt.deleting : pt.delete}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
