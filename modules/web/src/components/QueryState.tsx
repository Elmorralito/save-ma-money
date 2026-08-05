import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { formatApiError } from "@/lib/formatApiError";

type QueryStateProps = {
  isPending: boolean;
  isError: boolean;
  error: unknown;
  isEmpty: boolean;
  emptyTitle: string;
  emptyDescription?: string;
  emptyAction?: ReactNode;
  onRetry?: () => void;
  children: ReactNode;
};

/** Loading / empty / error chrome for feature list/detail queries. */
export function QueryState({
  isPending,
  isError,
  error,
  isEmpty,
  emptyTitle,
  emptyDescription,
  emptyAction,
  onRetry,
  children,
}: QueryStateProps) {
  if (isPending) {
    return (
      <p className="text-sm text-muted-foreground" role="status">
        Loading…
      </p>
    );
  }

  if (isError) {
    return (
      <div className="space-y-3" role="alert">
        <p className="text-sm text-destructive">{formatApiError(error)}</p>
        {onRetry ? (
          <Button type="button" variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        ) : null}
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className="rounded-md border border-dashed border-border px-4 py-8 text-center">
        <p className="text-sm font-medium">{emptyTitle}</p>
        {emptyDescription ? (
          <p className="mt-1 text-sm text-muted-foreground">{emptyDescription}</p>
        ) : null}
        {emptyAction ? <div className="mt-4 flex justify-center">{emptyAction}</div> : null}
      </div>
    );
  }

  return children;
}
