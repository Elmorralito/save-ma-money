import { apiFetch } from "@/api/http";
import { IDEMPOTENCY_KEY_HEADER, newIdempotencyKey } from "@/api/idempotency";
import type {
  PaginatedTransactions,
  TransactionBulkCreate,
  TransactionBulkResponse,
  TransactionCreate,
  TransactionResponse,
  TransactionUpdate,
} from "@/types/domain";

const TRANSACTIONS_PATH = "/api/v1/transactions";

export type ListTransactionsParams = {
  account_id?: string;
  category_id?: string;
  transaction_type?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  min_amount?: number;
  max_amount?: number;
  search?: string;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

function buildListQuery(params: ListTransactionsParams): string {
  const search = new URLSearchParams();
  if (params.account_id) {
    search.set("account_id", params.account_id);
  }
  if (params.category_id) {
    search.set("category_id", params.category_id);
  }
  if (params.transaction_type) {
    search.set("transaction_type", params.transaction_type);
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
  if (params.min_amount !== undefined) {
    search.set("min_amount", String(params.min_amount));
  }
  if (params.max_amount !== undefined) {
    search.set("max_amount", String(params.max_amount));
  }
  if (params.search) {
    search.set("search", params.search);
  }
  if (params.skip !== undefined) {
    search.set("skip", String(params.skip));
  }
  if (params.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  const qs = search.toString();
  return qs === "" ? TRANSACTIONS_PATH : `${TRANSACTIONS_PATH}?${qs}`;
}

/** ``GET /api/v1/transactions`` — excludes TRANSFER by default when type omitted. */
export async function listTransactions(
  params: ListTransactionsParams = {},
): Promise<PaginatedTransactions> {
  const { signal, ...filters } = params;
  const result = await apiFetch<PaginatedTransactions>(buildListQuery(filters), { signal });
  return result.data;
}

/** ``GET /api/v1/transactions/{transaction_id}``. */
export async function getTransaction(
  transactionId: string,
  signal?: AbortSignal,
): Promise<TransactionResponse> {
  const result = await apiFetch<TransactionResponse>(`${TRANSACTIONS_PATH}/${transactionId}`, {
    signal,
  });
  return result.data;
}

export type CreateTransactionOptions = {
  signal?: AbortSignal;
  /** Override generated Idempotency-Key (tests). */
  idempotencyKey?: string;
};

/** ``POST /api/v1/transactions`` — always sends ``Idempotency-Key``. */
export async function createTransaction(
  body: TransactionCreate,
  options: CreateTransactionOptions = {},
): Promise<TransactionResponse> {
  const key = options.idempotencyKey ?? newIdempotencyKey();
  const result = await apiFetch<TransactionResponse>(TRANSACTIONS_PATH, {
    method: "POST",
    signal: options.signal,
    headers: {
      "Content-Type": "application/json",
      [IDEMPOTENCY_KEY_HEADER]: key,
    },
    body: JSON.stringify(body),
  });
  return result.data;
}

/** ``PUT /api/v1/transactions/{transaction_id}``. */
export async function updateTransaction(
  transactionId: string,
  body: TransactionUpdate,
  signal?: AbortSignal,
): Promise<TransactionResponse> {
  const result = await apiFetch<TransactionResponse>(`${TRANSACTIONS_PATH}/${transactionId}`, {
    method: "PUT",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return result.data;
}

/** ``DELETE /api/v1/transactions/{transaction_id}`` — soft-delete (204). */
export async function deleteTransaction(
  transactionId: string,
  signal?: AbortSignal,
): Promise<void> {
  await apiFetch<undefined>(`${TRANSACTIONS_PATH}/${transactionId}`, {
    method: "DELETE",
    signal,
  });
}

export type BulkCreateTransactionsOptions = {
  signal?: AbortSignal;
  idempotencyKey?: string;
};

/** ``POST /api/v1/transactions/bulk`` — always sends ``Idempotency-Key``. */
export async function bulkCreateTransactions(
  body: TransactionBulkCreate,
  options: BulkCreateTransactionsOptions = {},
): Promise<TransactionBulkResponse> {
  const key = options.idempotencyKey ?? newIdempotencyKey();
  const result = await apiFetch<TransactionBulkResponse>(`${TRANSACTIONS_PATH}/bulk`, {
    method: "POST",
    signal: options.signal,
    headers: {
      "Content-Type": "application/json",
      [IDEMPOTENCY_KEY_HEADER]: key,
    },
    body: JSON.stringify(body),
  });
  return result.data;
}
