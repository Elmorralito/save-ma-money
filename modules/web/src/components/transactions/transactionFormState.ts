import type { TransactionCreate, TransactionResponse, TransactionUpdate } from "@/types/domain";

export type TransactionTypeSlug = "income" | "expense";

export type TransactionFormState = {
  account_id: string;
  category_id: string;
  transaction_type: TransactionTypeSlug;
  amount: string;
  currency: string;
  description: string;
  transaction_date: string;
  reference_number: string;
  tags: string;
  status: string;
};

function todayDateInput(): string {
  return new Date().toISOString().slice(0, 10);
}

export function emptyTransactionFormState(
  overrides: Partial<TransactionFormState> = {},
): TransactionFormState {
  return {
    account_id: "",
    category_id: "",
    transaction_type: "expense",
    amount: "",
    currency: "USD",
    description: "",
    transaction_date: todayDateInput(),
    reference_number: "",
    tags: "",
    status: "",
    ...overrides,
  };
}

export function transactionFormFromResponse(txn: TransactionResponse): TransactionFormState {
  const type: TransactionTypeSlug = txn.transaction_type === "income" ? "income" : "expense";
  return emptyTransactionFormState({
    account_id: txn.account_id ?? "",
    category_id: txn.category_id ?? "",
    transaction_type: type,
    amount: String(txn.amount),
    currency: txn.currency,
    description: txn.description,
    transaction_date: txn.transaction_date,
    reference_number: txn.reference_number ?? "",
    tags: (txn.tags ?? []).join(", "),
    status: txn.status,
  });
}

function parseRequiredAmount(value: string): number {
  const trimmed = value.trim();
  if (trimmed === "") {
    throw new Error("Amount is required");
  }
  const parsed = Number(trimmed);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error("Amount must be a positive number");
  }
  return parsed;
}

function parseTags(value: string): string[] | undefined {
  const tags = value
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part.length > 0);
  return tags.length > 0 ? tags : undefined;
}

/** Map form state → OpenAPI ``TransactionCreate``. */
export function toTransactionCreate(state: TransactionFormState): TransactionCreate {
  if (!state.account_id) {
    throw new Error("Account is required");
  }
  if (!state.category_id) {
    throw new Error("Category is required");
  }
  if (!state.transaction_date.trim()) {
    throw new Error("Transaction date is required");
  }

  const create: TransactionCreate = {
    account_id: state.account_id,
    category_id: state.category_id,
    transaction_type: state.transaction_type,
    amount: parseRequiredAmount(state.amount),
    currency: state.currency.trim().toUpperCase() || "USD",
    description: state.description.trim(),
    transaction_date: state.transaction_date.trim(),
  };

  const reference = state.reference_number.trim();
  if (reference !== "") {
    create.reference_number = reference;
  }
  const tags = parseTags(state.tags);
  if (tags) {
    create.tags = tags;
  }
  const status = state.status.trim();
  if (status !== "") {
    create.status = status;
  }
  return create;
}

/** Map form state → OpenAPI ``TransactionUpdate`` (omit empties that would wipe server fields). */
export function toTransactionUpdate(state: TransactionFormState): TransactionUpdate {
  if (!state.account_id) {
    throw new Error("Account is required");
  }
  if (!state.category_id) {
    throw new Error("Category is required");
  }
  if (!state.transaction_date.trim()) {
    throw new Error("Transaction date is required");
  }

  const update: TransactionUpdate = {
    account_id: state.account_id,
    category_id: state.category_id,
    transaction_type: state.transaction_type,
    amount: parseRequiredAmount(state.amount),
    currency: state.currency.trim().toUpperCase() || "USD",
    transaction_date: state.transaction_date.trim(),
  };

  if (state.description.trim() !== "") {
    update.description = state.description.trim();
  }
  if (state.reference_number.trim() !== "") {
    update.reference_number = state.reference_number.trim();
  }
  const tags = parseTags(state.tags);
  if (tags) {
    update.tags = tags;
  }
  if (state.status.trim() !== "") {
    update.status = state.status.trim();
  }
  return update;
}
