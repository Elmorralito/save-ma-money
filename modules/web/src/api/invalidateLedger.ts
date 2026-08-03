import type { QueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/api/queryKeys";

/**
 * Invalidate list/detail caches after ledger writes (txns / movements).
 *
 * Account balances come from the API; refresh accounts after any money movement.
 */
export async function invalidateAfterLedgerWrite(
  queryClient: QueryClient,
  options: {
    transactions?: boolean;
    movements?: boolean;
    transactionId?: string;
    movementId?: string;
    removeTransactionId?: string;
    removeMovementId?: string;
  } = {},
): Promise<void> {
  const tasks: Promise<unknown>[] = [
    queryClient.invalidateQueries({ queryKey: queryKeys.accounts.lists() }),
    queryClient.invalidateQueries({ queryKey: queryKeys.accounts.details() }),
  ];

  if (options.transactions !== false) {
    tasks.push(queryClient.invalidateQueries({ queryKey: queryKeys.transactions.lists() }));
  }
  if (options.movements) {
    tasks.push(queryClient.invalidateQueries({ queryKey: queryKeys.movements.lists() }));
  }
  if (options.transactionId) {
    tasks.push(
      queryClient.invalidateQueries({
        queryKey: queryKeys.transactions.detail(options.transactionId),
      }),
    );
  }
  if (options.movementId) {
    tasks.push(
      queryClient.invalidateQueries({ queryKey: queryKeys.movements.detail(options.movementId) }),
    );
  }
  if (options.removeTransactionId) {
    queryClient.removeQueries({
      queryKey: queryKeys.transactions.detail(options.removeTransactionId),
    });
  }
  if (options.removeMovementId) {
    queryClient.removeQueries({
      queryKey: queryKeys.movements.detail(options.removeMovementId),
    });
  }

  await Promise.all(tasks);
}
