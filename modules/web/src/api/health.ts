import { apiFetch } from "@/api/http";
import type { HealthResponse } from "@/types/domain";

const HEALTH_PATH = "/api/v1/health";
const HEALTH_LIVE_PATH = "/api/v1/health/live";

/** Aggregate health probe (`GET /api/v1/health`). */
export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const result = await apiFetch<HealthResponse>(HEALTH_PATH, { signal });
  return result.data;
}

/** Liveness probe (`GET /api/v1/health/live`) — no dependency checks. */
export async function getHealthLive(signal?: AbortSignal): Promise<unknown> {
  const result = await apiFetch<unknown>(HEALTH_LIVE_PATH, { signal });
  return result.data;
}
