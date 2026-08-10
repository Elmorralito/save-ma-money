import { apiFetch } from "@/api/http";
import type {
  ClearPaidRequest,
  MarkPaidRequest,
  PaginatedTransactionTemplates,
  TransactionResponse,
  TransactionTemplateCreate,
  TransactionTemplateResponse,
  TransactionTemplateUpdate,
  UpcomingDuesResponse,
} from "@/types/domain";

const TEMPLATES_PATH = "/api/v1/transaction-templates";

export type ListTransactionTemplatesParams = {
  category_id?: string;
  is_active?: boolean;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

export type ListUpcomingDuesParams = {
  as_of?: string;
  window_days?: number;
  include_paid?: boolean;
  signal?: AbortSignal;
};

function buildListQuery(params: ListTransactionTemplatesParams): string {
  const search = new URLSearchParams();
  if (params.category_id) {
    search.set("category_id", params.category_id);
  }
  if (params.is_active !== undefined) {
    search.set("is_active", String(params.is_active));
  }
  if (params.skip !== undefined) {
    search.set("skip", String(params.skip));
  }
  if (params.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  const qs = search.toString();
  return qs === "" ? TEMPLATES_PATH : `${TEMPLATES_PATH}?${qs}`;
}

function buildUpcomingDuesQuery(params: ListUpcomingDuesParams): string {
  const search = new URLSearchParams();
  if (params.as_of) {
    search.set("as_of", params.as_of);
  }
  if (params.window_days !== undefined) {
    search.set("window_days", String(params.window_days));
  }
  if (params.include_paid !== undefined) {
    search.set("include_paid", String(params.include_paid));
  }
  const qs = search.toString();
  const path = `${TEMPLATES_PATH}/upcoming-dues`;
  return qs === "" ? path : `${path}?${qs}`;
}

/** ``GET /api/v1/transaction-templates`` — paginated payment-due templates. */
export async function listTransactionTemplates(
  params: ListTransactionTemplatesParams = {},
): Promise<PaginatedTransactionTemplates> {
  const { signal, ...filters } = params;
  const result = await apiFetch<PaginatedTransactionTemplates>(buildListQuery(filters), { signal });
  return result.data;
}

/** ``GET /api/v1/transaction-templates/upcoming-dues``. */
export async function listUpcomingDues(
  params: ListUpcomingDuesParams = {},
): Promise<UpcomingDuesResponse> {
  const { signal, ...filters } = params;
  const result = await apiFetch<UpcomingDuesResponse>(buildUpcomingDuesQuery(filters), { signal });
  return result.data;
}

/** ``GET /api/v1/transaction-templates/{template_id}``. */
export async function getTransactionTemplate(
  templateId: string,
  signal?: AbortSignal,
): Promise<TransactionTemplateResponse> {
  const result = await apiFetch<TransactionTemplateResponse>(`${TEMPLATES_PATH}/${templateId}`, {
    signal,
  });
  return result.data;
}

/** ``POST /api/v1/transaction-templates``. */
export async function createTransactionTemplate(
  body: TransactionTemplateCreate,
  signal?: AbortSignal,
): Promise<TransactionTemplateResponse> {
  const result = await apiFetch<TransactionTemplateResponse>(TEMPLATES_PATH, {
    method: "POST",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return result.data;
}

/** ``PUT /api/v1/transaction-templates/{template_id}``. */
export async function updateTransactionTemplate(
  templateId: string,
  body: TransactionTemplateUpdate,
  signal?: AbortSignal,
): Promise<TransactionTemplateResponse> {
  const result = await apiFetch<TransactionTemplateResponse>(`${TEMPLATES_PATH}/${templateId}`, {
    method: "PUT",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return result.data;
}

/** ``DELETE /api/v1/transaction-templates/{template_id}`` — soft-delete (204). */
export async function deleteTransactionTemplate(
  templateId: string,
  signal?: AbortSignal,
): Promise<void> {
  await apiFetch<undefined>(`${TEMPLATES_PATH}/${templateId}`, {
    method: "DELETE",
    signal,
  });
}

/** ``POST /api/v1/transaction-templates/{template_id}/mark-paid``. */
export async function markTemplatePaid(
  templateId: string,
  body: MarkPaidRequest = {},
  signal?: AbortSignal,
): Promise<TransactionResponse> {
  const result = await apiFetch<TransactionResponse>(`${TEMPLATES_PATH}/${templateId}/mark-paid`, {
    method: "POST",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return result.data;
}

/** ``POST /api/v1/transaction-templates/{template_id}/clear-paid``. */
export async function clearTemplatePaid(
  templateId: string,
  body: ClearPaidRequest = {},
  signal?: AbortSignal,
): Promise<TransactionResponse> {
  const result = await apiFetch<TransactionResponse>(`${TEMPLATES_PATH}/${templateId}/clear-paid`, {
    method: "POST",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return result.data;
}
