import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/native-select";

export const DEFAULT_PAGE_SIZE = 25;
export const PAGE_SIZE_OPTIONS = [10, 25, 50, 100] as const;

type TablePaginationProps = {
  /** 1-based current page number. */
  page: number;
  pageSize: number;
  total: number;
  /** Number of items currently rendered on this page (for range display). */
  visibleCount?: number;
  onPageChange: (nextPage: number) => void;
  onPageSizeChange: (nextSize: number) => void;
};

export function TablePagination({
  page,
  pageSize,
  total,
  visibleCount,
  onPageChange,
  onPageSizeChange,
}: TablePaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(Math.max(1, page), totalPages);
  const start = total === 0 ? 0 : (safePage - 1) * pageSize + 1;
  const end =
    total === 0
      ? 0
      : visibleCount !== undefined
        ? Math.min(total, start + Math.max(visibleCount, 0) - 1)
        : Math.min(total, safePage * pageSize);

  return (
    <div
      className="flex flex-wrap items-center justify-between gap-3 border-t border-border bg-muted/20 px-4 py-3 text-xs text-muted-foreground"
      aria-label="Table pagination"
    >
      <p className="tabular-nums">
        {total === 0
          ? "Showing 0 of 0"
          : `Showing ${String(start)}–${String(end)} of ${String(total)}`}
      </p>

      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2">
          <span className="whitespace-nowrap">Rows per page</span>
          <NativeSelect
            aria-label="Rows per page"
            className="h-8 w-20 text-xs"
            value={String(pageSize)}
            onChange={(event) => {
              const next = Number(event.target.value);
              if (Number.isFinite(next) && next > 0) {
                onPageSizeChange(next);
              }
            }}
          >
            {PAGE_SIZE_OPTIONS.map((size) => (
              <option key={size} value={String(size)}>
                {String(size)}
              </option>
            ))}
          </NativeSelect>
        </label>

        <span className="tabular-nums">
          Page {String(safePage)} of {String(totalPages)}
        </span>

        <div className="flex items-center gap-1.5">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8 gap-1 px-2.5 text-xs"
            disabled={safePage <= 1}
            onClick={() => {
              onPageChange(safePage - 1);
            }}
          >
            <ChevronLeft aria-hidden="true" className="size-3.5" />
            <span>Previous</span>
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="h-8 gap-1 px-2.5 text-xs"
            disabled={safePage >= totalPages}
            onClick={() => {
              onPageChange(safePage + 1);
            }}
          >
            <span>Next</span>
            <ChevronRight aria-hidden="true" className="size-3.5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
