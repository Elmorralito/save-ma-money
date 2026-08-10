import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { invalidateAfterTemplateWrite } from "@/api/invalidateLedger";
import { transactionTemplatesListQueryOptions } from "@/api/queries";
import {
  clearTemplatePaid,
  deleteTransactionTemplate,
  markTemplatePaid,
} from "@/api/transactionTemplates";
import { PaymentDueFormDialog } from "@/components/paymentDues/PaymentDueFormDialog";
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
import { formatApiError } from "@/lib/formatApiError";
import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import type { TransactionTemplateResponse } from "@/types/domain";

/** First-page list window (pagination UI deferred). */
const LIST_PARAMS = { limit: 100, skip: 0, is_active: true } as const;

function scheduleLabel(template: TransactionTemplateResponse): string {
  if (template.due_date) {
    return `One-off · ${formatDate(template.due_date)}`;
  }
  if (template.use_month_end) {
    return "Monthly · month end";
  }
  return `Monthly · day ${String(template.planned_day)}`;
}

export function PaymentDuesPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<TransactionTemplateResponse | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<TransactionTemplateResponse | null>(null);

  const listQuery = useQuery(transactionTemplatesListQueryOptions(LIST_PARAMS));
  const items = listQuery.data?.items ?? [];

  const markPaidMutation = useMutation({
    mutationFn: (templateId: string) => markTemplatePaid(templateId),
    onSuccess: async (txn, templateId) => {
      await invalidateAfterTemplateWrite(queryClient, {
        templateId,
        markPaid: true,
        transactionId: txn.id,
      });
      toast.success("Marked paid");
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
      toast.success("Cleared paid status");
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (templateId: string) => deleteTransactionTemplate(templateId),
    onSuccess: async (_void, templateId) => {
      await invalidateAfterTemplateWrite(queryClient, { removeTemplateId: templateId });
      toast.success("Payment due deleted");
      setDeleteTarget(null);
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err));
    },
  });

  const actionPending =
    markPaidMutation.isPending || clearPaidMutation.isPending || deleteMutation.isPending;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Payment dues</h1>
          <p className="text-sm text-muted-foreground">
            Recurring bills and one-off deadlines — when something must be paid, not account
            balances.
          </p>
        </div>
        <Button
          type="button"
          onClick={() => {
            setCreateOpen(true);
          }}
        >
          New payment due
        </Button>
      </div>

      <QueryState
        isPending={listQuery.isPending}
        isError={listQuery.isError}
        error={listQuery.error}
        isEmpty={!listQuery.isPending && !listQuery.isError && items.length === 0}
        emptyTitle="No payment dues yet"
        emptyDescription="Add a recurring bill or one-off deadline to see it under Due soon."
        emptyAction={
          <Button
            type="button"
            onClick={() => {
              setCreateOpen(true);
            }}
          >
            Create your first payment due
          </Button>
        }
        onRetry={() => {
          void listQuery.refetch();
        }}
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Schedule</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Remind</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((template) => (
              <TableRow key={template.id}>
                <TableCell>
                  <div className="space-y-0.5">
                    <p className="font-medium">{template.name}</p>
                    {template.description.trim() ? (
                      <p className="text-xs text-muted-foreground">{template.description}</p>
                    ) : null}
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground">{scheduleLabel(template)}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatMoney(template.planned_amount, "USD")}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {template.remind_days_before === null || template.remind_days_before === undefined
                    ? "—"
                    : `${String(template.remind_days_before)}d`}
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex flex-wrap justify-end gap-2">
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      disabled={actionPending}
                      onClick={() => {
                        markPaidMutation.mutate(template.id);
                      }}
                    >
                      Mark paid
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={actionPending}
                      onClick={() => {
                        clearPaidMutation.mutate(template.id);
                      }}
                    >
                      Clear paid
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={actionPending}
                      onClick={() => {
                        setEditTarget(template);
                      }}
                    >
                      Edit
                    </Button>
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      disabled={actionPending}
                      onClick={() => {
                        setDeleteTarget(template);
                      }}
                    >
                      Delete
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
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
            <DialogTitle>Delete payment due?</DialogTitle>
            <DialogDescription>
              Soft-deletes “{deleteTarget?.name ?? "this due"}”. You can recreate it later if
              needed.
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
