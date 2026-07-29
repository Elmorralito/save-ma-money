import { QueryClient } from "@tanstack/react-query";

/** Test helper: fresh QueryClient (no retries, no shared cache). */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        staleTime: 0,
        gcTime: 0,
      },
    },
  });
}
