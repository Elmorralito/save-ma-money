import { PapitaApiError } from "@/api/errors";
import { apiFetch } from "@/api/http";
import type {
  IngestionRunResponse,
  PaginatedIngestionConnections,
  PaginatedIngestionRuns,
} from "@/types/domain";

const INGESTION_PATH = "/api/v1/ingestion";

export type LatestIngestionRunParams = {
  connection_id?: string | null;
  signal?: AbortSignal;
};

export type ListIngestionRunsParams = {
  connection_id?: string | null;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

export type ListIngestionConnectionsParams = {
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

function buildQuery(params: Record<string, string | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, value);
    }
  }
  const qs = search.toString();
  return qs === "" ? "" : `?${qs}`;
}

/**
 * ``GET /api/v1/ingestion/runs/latest`` — latest ingestion run for the owner.
 *
 * Returns ``null`` when the API replies 404 (no runs recorded yet).
 */
export async function getLatestIngestionRun(
  params: LatestIngestionRunParams = {},
): Promise<IngestionRunResponse | null> {
  const { signal, connection_id } = params;
  const path = `${INGESTION_PATH}/runs/latest${buildQuery({
    connection_id: connection_id ?? undefined,
  })}`;
  try {
    const result = await apiFetch<IngestionRunResponse>(path, { signal });
    return result.data;
  } catch (err) {
    if (err instanceof PapitaApiError && err.status === 404) {
      return null;
    }
    throw err;
  }
}

/** ``GET /api/v1/ingestion/runs`` — paginated recent ingestion runs. */
export async function listIngestionRuns(
  params: ListIngestionRunsParams = {},
): Promise<PaginatedIngestionRuns> {
  const { signal, connection_id, skip, limit } = params;
  const path = `${INGESTION_PATH}/runs${buildQuery({
    connection_id: connection_id ?? undefined,
    skip: skip !== undefined ? String(skip) : undefined,
    limit: limit !== undefined ? String(limit) : undefined,
  })}`;
  const result = await apiFetch<PaginatedIngestionRuns>(path, { signal });
  return result.data;
}

/** ``GET /api/v1/ingestion/connections`` — paginated ingestion connections. */
export async function listIngestionConnections(
  params: ListIngestionConnectionsParams = {},
): Promise<PaginatedIngestionConnections> {
  const { signal, skip, limit } = params;
  const path = `${INGESTION_PATH}/connections${buildQuery({
    skip: skip !== undefined ? String(skip) : undefined,
    limit: limit !== undefined ? String(limit) : undefined,
  })}`;
  const result = await apiFetch<PaginatedIngestionConnections>(path, { signal });
  return result.data;
}
