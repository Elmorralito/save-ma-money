import { QueryClient } from "@tanstack/react-query";

import { isClientHttpError } from "@/api/errors";

/** Shared QueryClient defaults for the SPA (PPT-048). */
export function createAppQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        retry: (failureCount, error) => {
          if (isClientHttpError(error)) {
            return false;
          }
          return failureCount < 2;
        },
        refetchOnWindowFocus: false,
      },
    },
  });
}
