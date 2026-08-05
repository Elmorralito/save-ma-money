import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { invalidateAfterLedgerWrite } from "@/api/invalidateLedger";
import { cancelMovement, executeMovement } from "@/api/movements";
import { accountsListQueryOptions, movementsListQueryOptions } from "@/api/queries";
import { MovementFormDialog } from "@/components/movements/MovementFormDialog";
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
import { formatApiError } from "@/lib/formatApiError";
import { formatDate } from "@/lib/formatDate";
import { formatMoney } from "@/lib/formatMoney";
import { formatSlugLabel } from "@/lib/formatSlugLabel";
import type { MovementResponse } from "@/types/domain";

const PAGE_LIMIT = 100;
const PICKER_PARAMS = { limit: 100, skip: 0 } as const;

type FilterState = {
  source_account_id: string;
  destination_account_id: string;
  status: string;
  start_date: string;
  end_date: string;
};

const EMPTY_FILTERS: FilterState = {
  source_account_id: "",
  destination_account_id: "",
  status: "",
  start_date: "",
  end_date: "",
};

function isPending(movement: MovementResponse): boolean {
  return movement.status === "pending";
}

export function MovementsPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [createOpen, setCreateOpen] = useState(false);
  const [editTarget, setEditTarget] = useState<MovementResponse | null>(null);
  const [cancelTarget, setCancelTarget] = useState<MovementResponse | null>(null);

  const listParams = useMemo(
    () => ({
      limit: PAGE_LIMIT,
      skip: 0,
      ...(filters.source_account_id ? { source_account_id: filters.source_account_id } : {}),
      ...(filters.destination_account_id
        ? { destination_account_id: filters.destination_account_id }
        : {}),
      ...(filters.status ? { status: filters.status } : {}),
      ...(filters.start_date ? { start_date: filters.start_date } : {}),
      ...(filters.end_date ? { end_date: filters.end_date } : {}),
    }),
    [filters],
  );

  const listQuery = useQuery(movementsListQueryOptions(listParams));
  const accountsQuery = useQuery(accountsListQueryOptions(PICKER_PARAMS));
  const items = listQuery.data?.items ?? [];
  const accounts = accountsQuery.data?.items ?? [];
  const hasActiveFilters = Object.values(filters).some((value) => value.trim() !== "");

  const executeMutation = useMutation({
    mutationFn: (movementId: string) => executeMovement(movementId),
    onSuccess: async (result) => {
      await invalidateAfterLedgerWrite(queryClient, {
        transactions: true,
        movements: true,
        movementId: result.id,
      });
      toast.success("Movement executed");
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err));
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (movementId: string) => cancelMovement(movementId),
    onSuccess: async (_void, movementId) => {
      await invalidateAfterLedgerWrite(queryClient, {
        transactions: true,
        movements: true,
        removeMovementId: movementId,
      });
      toast.success("Movement cancelled");
      setCancelTarget(null);
    },
    onError: (err: unknown) => {
      toast.error(formatApiError(err));
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Movements</h1>
          <p className="text-sm text-muted-foreground">
            Move money between accounts. Execute or cancel only applies to pending transfers.
          </p>
        </div>
        <Button
          type="button"
          onClick={() => {
            setCreateOpen(true);
          }}
        >
          New movement
        </Button>
      </div>

      <div className="grid gap-3 rounded-md border border-border p-4 sm:grid-cols-2 lg:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="mov-filter-source">Source</Label>
          <NativeSelect
            id="mov-filter-source"
            value={filters.source_account_id}
            onChange={(event) => {
              setFilters((prev) => ({ ...prev, source_account_id: event.target.value }));
            }}
          >
            <option value="">All sources</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="space-y-2">
          <Label htmlFor="mov-filter-destination">Destination</Label>
          <NativeSelect
            id="mov-filter-destination"
            value={filters.destination_account_id}
            onChange={(event) => {
              setFilters((prev) => ({ ...prev, destination_account_id: event.target.value }));
            }}
          >
            <option value="">All destinations</option>
            {accounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.name}
              </option>
            ))}
          </NativeSelect>
        </div>
        <div className="space-y-2">
          <Label htmlFor="mov-filter-status">Status</Label>
          <NativeSelect
            id="mov-filter-status"
            value={filters.status}
            onChange={(event) => {
              setFilters((prev) => ({ ...prev, status: event.target.value }));
            }}
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="completed">Completed</option>
            <option value="cancelled">Cancelled</option>
          </NativeSelect>
        </div>
        <div className="space-y-2">
          <Label htmlFor="mov-filter-start">Start date</Label>
          <Input
            id="mov-filter-start"
            type="date"
            value={filters.start_date}
            onChange={(event) => {
              setFilters((prev) => ({ ...prev, start_date: event.target.value }));
            }}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="mov-filter-end">End date</Label>
          <Input
            id="mov-filter-end"
            type="date"
            value={filters.end_date}
            onChange={(event) => {
              setFilters((prev) => ({ ...prev, end_date: event.target.value }));
            }}
          />
        </div>
        <div className="flex items-end">
          <Button
            type="button"
            variant="ghost"
            onClick={() => {
              setFilters(EMPTY_FILTERS);
            }}
          >
            Clear filters
          </Button>
        </div>
      </div>

      <QueryState
        isPending={listQuery.isPending}
        isError={listQuery.isError}
        error={listQuery.error}
        isEmpty={!listQuery.isPending && !listQuery.isError && items.length === 0}
        emptyTitle={hasActiveFilters ? "No matching movements" : "No movements yet"}
        emptyDescription={
          hasActiveFilters
            ? "Try clearing filters or broadening the date range."
            : "Create a transfer between two accounts."
        }
        emptyAction={
          hasActiveFilters ? (
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setFilters(EMPTY_FILTERS);
              }}
            >
              Clear filters
            </Button>
          ) : (
            <Button
              type="button"
              onClick={() => {
                setCreateOpen(true);
              }}
            >
              Create your first transfer
            </Button>
          )
        }
        onRetry={() => {
          void listQuery.refetch();
        }}
      >
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Date</TableHead>
              <TableHead>Source</TableHead>
              <TableHead>Destination</TableHead>
              <TableHead>Description</TableHead>
              <TableHead className="text-right">Amount</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((movement) => (
              <TableRow key={movement.id}>
                <TableCell className="tabular-nums">{formatDate(movement.movement_date)}</TableCell>
                <TableCell>{movement.source_account_name ?? movement.source_account_id}</TableCell>
                <TableCell>
                  {movement.destination_account_name ?? movement.destination_account_id}
                </TableCell>
                <TableCell>{movement.description || "—"}</TableCell>
                <TableCell className="text-right tabular-nums">
                  {formatMoney(movement.amount, movement.currency)}
                </TableCell>
                <TableCell>{formatSlugLabel(movement.status)}</TableCell>
                <TableCell className="text-right">
                  {isPending(movement) ? (
                    <div className="flex justify-end gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setEditTarget(movement);
                        }}
                      >
                        Edit
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        disabled={executeMutation.isPending}
                        onClick={() => {
                          executeMutation.mutate(movement.id);
                        }}
                      >
                        Execute
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="destructive"
                        onClick={() => {
                          setCancelTarget(movement);
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {listQuery.data ? (
          <p className="text-xs text-muted-foreground">
            Showing {items.length} of {listQuery.data.total}
            {listQuery.data.total > PAGE_LIMIT ? ` (first ${String(PAGE_LIMIT)} only)` : ""}
          </p>
        ) : null}
      </QueryState>

      <MovementFormDialog open={createOpen} onOpenChange={setCreateOpen} mode="create" />
      <MovementFormDialog
        open={editTarget !== null}
        onOpenChange={(open) => {
          if (!open) {
            setEditTarget(null);
          }
        }}
        mode="edit"
        movement={editTarget}
      />

      <Dialog
        open={cancelTarget !== null}
        onOpenChange={(open) => {
          if (!open) {
            setCancelTarget(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel movement</DialogTitle>
            <DialogDescription>
              Cancel this pending transfer
              {cancelTarget?.description ? ` (“${cancelTarget.description}”)` : ""}? The API sets
              status to cancelled (row is kept).
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setCancelTarget(null);
              }}
            >
              Keep pending
            </Button>
            <Button
              type="button"
              variant="destructive"
              disabled={cancelMutation.isPending || !cancelTarget}
              onClick={() => {
                if (cancelTarget) {
                  cancelMutation.mutate(cancelTarget.id);
                }
              }}
            >
              {cancelMutation.isPending ? "Cancelling…" : "Cancel movement"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
