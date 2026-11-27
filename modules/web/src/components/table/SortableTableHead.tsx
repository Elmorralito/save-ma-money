import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";

import { TableHead } from "@/components/ui/table";
import { cn } from "@/lib/utils";

export type SortDirection = "asc" | "desc";

export type SortState<K extends string> = {
  key: K;
  direction: SortDirection;
} | null;

export function toggleSort<K extends string>(
  current: SortState<K>,
  key: K,
  defaultDirection: SortDirection = "asc",
): SortState<K> {
  if (current?.key === key) {
    return { key, direction: current.direction === "asc" ? "desc" : "asc" };
  }
  return { key, direction: defaultDirection };
}

export type SortableValue = string | number | boolean | null | undefined;

/** Pure presentation comparator for table rows (zero domain math). */
export function sortItems<T, K extends string>(
  items: readonly T[],
  sort: SortState<K>,
  getters: Record<K, (row: T) => SortableValue>,
): T[] {
  if (!sort) {
    return [...items];
  }
  const getter = getters[sort.key];
  const factor = sort.direction === "asc" ? 1 : -1;

  return [...items].sort((a, b) => {
    const va = getter(a);
    const vb = getter(b);
    const aNil = va === null || va === undefined || va === "";
    const bNil = vb === null || vb === undefined || vb === "";
    if (aNil && bNil) return 0;
    if (aNil) return 1;
    if (bNil) return -1;

    if (typeof va === "number" && typeof vb === "number") {
      return (va - vb) * factor;
    }
    if (typeof va === "boolean" && typeof vb === "boolean") {
      return (Number(va) - Number(vb)) * factor;
    }
    return (
      String(va).localeCompare(String(vb), undefined, {
        numeric: true,
        sensitivity: "base",
      }) * factor
    );
  });
}

type SortableTableHeadProps<K extends string> = {
  label: string;
  sortKey: K;
  sort: SortState<K>;
  onSort: (key: K) => void;
  align?: "left" | "right";
  className?: string;
};

export function SortableTableHead<K extends string>({
  label,
  sortKey,
  sort,
  onSort,
  align = "left",
  className,
}: SortableTableHeadProps<K>) {
  const isActive = sort?.key === sortKey;
  const ariaSort = isActive ? (sort.direction === "asc" ? "ascending" : "descending") : "none";

  return (
    <TableHead aria-sort={ariaSort} className={cn(align === "right" && "text-right", className)}>
      <button
        type="button"
        onClick={() => {
          onSort(sortKey);
        }}
        className={cn(
          "inline-flex items-center gap-1.5 rounded px-1 py-0.5 text-xs font-semibold uppercase tracking-wide transition-colors hover:text-foreground",
          align === "right" && "ml-auto flex-row-reverse",
          isActive ? "text-primary" : "text-muted-foreground",
        )}
      >
        <span>{label}</span>
        {isActive ? (
          sort.direction === "asc" ? (
            <ArrowUp aria-hidden="true" className="size-3.5 shrink-0" />
          ) : (
            <ArrowDown aria-hidden="true" className="size-3.5 shrink-0" />
          )
        ) : (
          <ArrowUpDown aria-hidden="true" className="size-3.5 shrink-0 opacity-50" />
        )}
      </button>
    </TableHead>
  );
}
