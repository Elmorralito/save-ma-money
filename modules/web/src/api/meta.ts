import type { DiscoveryHeaders } from "@/api/headers";
import { apiFetch } from "@/api/http";
import type { ClientContract } from "@/types/domain";

const CLIENT_CONTRACT_PATH = "/api/v1/meta/client-contract";

/** Probe `GET /api/v1/meta/client-contract` (unauthenticated PPT-044 discovery). */
export async function getClientContract(signal?: AbortSignal): Promise<{
  contract: ClientContract;
  discovery: DiscoveryHeaders;
}> {
  const result = await apiFetch<ClientContract>(CLIENT_CONTRACT_PATH, { signal });
  return { contract: result.data, discovery: result.discovery };
}
