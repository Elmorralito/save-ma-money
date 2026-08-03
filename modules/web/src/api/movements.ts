import { apiFetch } from "@/api/http";
import type {
  MovementCreate,
  MovementExecuteResponse,
  MovementResponse,
  MovementUpdate,
  PaginatedMovements,
} from "@/types/domain";

const MOVEMENTS_PATH = "/api/v1/movements";

export type ListMovementsParams = {
  source_account_id?: string;
  destination_account_id?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

function buildListQuery(params: ListMovementsParams): string {
  const search = new URLSearchParams();
  if (params.source_account_id) {
    search.set("source_account_id", params.source_account_id);
  }
  if (params.destination_account_id) {
    search.set("destination_account_id", params.destination_account_id);
  }
  if (params.status) {
    search.set("status", params.status);
  }
  if (params.start_date) {
    search.set("start_date", params.start_date);
  }
  if (params.end_date) {
    search.set("end_date", params.end_date);
  }
  if (params.skip !== undefined) {
    search.set("skip", String(params.skip));
  }
  if (params.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  const qs = search.toString();
  return qs === "" ? MOVEMENTS_PATH : `${MOVEMENTS_PATH}?${qs}`;
}

/** ``GET /api/v1/movements`` — paginated TRANSFER rows. */
export async function listMovements(params: ListMovementsParams = {}): Promise<PaginatedMovements> {
  const { signal, ...filters } = params;
  const result = await apiFetch<PaginatedMovements>(buildListQuery(filters), { signal });
  return result.data;
}

/** ``GET /api/v1/movements/{movement_id}``. */
export async function getMovement(
  movementId: string,
  signal?: AbortSignal,
): Promise<MovementResponse> {
  const result = await apiFetch<MovementResponse>(`${MOVEMENTS_PATH}/${movementId}`, { signal });
  return result.data;
}

/** ``POST /api/v1/movements``. */
export async function createMovement(
  body: MovementCreate,
  signal?: AbortSignal,
): Promise<MovementResponse> {
  const result = await apiFetch<MovementResponse>(MOVEMENTS_PATH, {
    method: "POST",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return result.data;
}

/** ``PUT /api/v1/movements/{movement_id}`` — pending only. */
export async function updateMovement(
  movementId: string,
  body: MovementUpdate,
  signal?: AbortSignal,
): Promise<MovementResponse> {
  const result = await apiFetch<MovementResponse>(`${MOVEMENTS_PATH}/${movementId}`, {
    method: "PUT",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return result.data;
}

/** ``DELETE /api/v1/movements/{movement_id}`` — cancel pending (204). */
export async function cancelMovement(movementId: string, signal?: AbortSignal): Promise<void> {
  await apiFetch<undefined>(`${MOVEMENTS_PATH}/${movementId}`, {
    method: "DELETE",
    signal,
  });
}

/** ``POST /api/v1/movements/{movement_id}/execute``. */
export async function executeMovement(
  movementId: string,
  signal?: AbortSignal,
): Promise<MovementExecuteResponse> {
  const result = await apiFetch<MovementExecuteResponse>(
    `${MOVEMENTS_PATH}/${movementId}/execute`,
    {
      method: "POST",
      signal,
    },
  );
  return result.data;
}
