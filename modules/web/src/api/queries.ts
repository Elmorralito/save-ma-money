import { queryOptions } from "@tanstack/react-query";

import { getHealth, getHealthLive } from "@/api/health";
import { getClientContract } from "@/api/meta";
import { queryKeys } from "@/api/queryKeys";

/** Shared query definition for PPT-044 client-contract discovery. */
export function clientContractQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.meta.clientContract(),
    queryFn: ({ signal }) => getClientContract(signal).then((result) => result.contract),
  });
}

/** Shared query definition for aggregate API health. */
export function healthQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.health.root(),
    queryFn: ({ signal }) => getHealth(signal),
  });
}

/** Shared query definition for liveness (no DB/Auth/Redis). */
export function healthLiveQueryOptions() {
  return queryOptions({
    queryKey: queryKeys.health.live(),
    queryFn: ({ signal }) => getHealthLive(signal),
  });
}
