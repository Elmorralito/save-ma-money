import { apiFetch } from "@/api/http";
import type {
  AccountCreate,
  AccountResponse,
  AccountUpdate,
  PaginatedAccounts,
} from "@/types/domain";

const ACCOUNTS_PATH = "/api/v1/accounts";

export type ListAccountsParams = {
  account_kind?: string;
  ledger_side?: string;
  is_active?: boolean;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

function buildListQuery(params: ListAccountsParams): string {
  const search = new URLSearchParams();
  if (params.account_kind) {
    search.set("account_kind", params.account_kind);
  }
  if (params.ledger_side) {
    search.set("ledger_side", params.ledger_side);
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
  return qs === "" ? ACCOUNTS_PATH : `${ACCOUNTS_PATH}?${qs}`;
}

/** ``GET /api/v1/accounts`` — paginated tenant accounts with API ``balance``. */
export async function listAccounts(params: ListAccountsParams = {}): Promise<PaginatedAccounts> {
  const { signal, ...filters } = params;
  const result = await apiFetch<PaginatedAccounts>(buildListQuery(filters), { signal });
  return result.data;
}

/** ``GET /api/v1/accounts/{account_id}``. */
export async function getAccount(
  accountId: string,
  signal?: AbortSignal,
): Promise<AccountResponse> {
  const result = await apiFetch<AccountResponse>(`${ACCOUNTS_PATH}/${accountId}`, { signal });
  return result.data;
}

/** ``POST /api/v1/accounts``. */
export async function createAccount(
  body: AccountCreate,
  signal?: AbortSignal,
): Promise<AccountResponse> {
  const result = await apiFetch<AccountResponse>(ACCOUNTS_PATH, {
    method: "POST",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return result.data;
}

/** ``PUT /api/v1/accounts/{account_id}``. */
export async function updateAccount(
  accountId: string,
  body: AccountUpdate,
  signal?: AbortSignal,
): Promise<AccountResponse> {
  const result = await apiFetch<AccountResponse>(`${ACCOUNTS_PATH}/${accountId}`, {
    method: "PUT",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return result.data;
}

/** ``DELETE /api/v1/accounts/{account_id}`` — soft-delete (204). */
export async function deleteAccount(accountId: string, signal?: AbortSignal): Promise<void> {
  await apiFetch<undefined>(`${ACCOUNTS_PATH}/${accountId}`, {
    method: "DELETE",
    signal,
  });
}
