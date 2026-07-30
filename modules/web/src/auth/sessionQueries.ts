import { queryOptions } from "@tanstack/react-query";

import { getBffSession } from "@/api/auth";
import { queryKeys } from "@/api/queryKeys";

/** Shared BFF session bootstrap query (cookie credentials). */
export function bffSessionQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.auth.session(),
    queryFn: ({ signal }) => getBffSession(signal),
    staleTime: 30_000,
    retry: false,
  });
}
