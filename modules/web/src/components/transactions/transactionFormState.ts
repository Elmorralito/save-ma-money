import type { TransactionCreate, TransactionResponse, TransactionUpdate } from "@/types/domain";

export type TransactionTypeSlug = "income" | "expense" | "transfer";

export type TransactionFormState = {
  account_id: string;
  source_account_id: string;
  destination_account_id: string;
  category_id: string;
  transaction_type: TransactionTypeSlug;
  amount: string;
  currency: string;
  description: string;
  transaction_date: string;
  reference_number: string;
  tags: string;
  status: string;
  scheduled: boolean;
  settlement_status: "settled" | "in_transit";
};

function todayDateInput(): string {
  return new Date().toISOString().slice(0, 10);
}

export function emptyTransactionFormState(
  overrides: Partial<TransactionFormState> = {},
): TransactionFormState {
  return {
    account_id: "",
    source_account_id: "",
    destination_account_id: "",
    category_id: "",
    transaction_type: "expense",
    amount: "",
    currency: "USD",
    description: "",
    transaction_date: todayDateInput(),
    reference_number: "",
    tags: "",
    status: "",
    scheduled: false,
    settlement_status: "settled",
    ...overrides,
  };
}

export function transactionFormFromResponse(txn: TransactionResponse): TransactionFormState {
  const type: TransactionTypeSlug =
    txn.transaction_type === "income"
      ? "income"
      : txn.transaction_type === "transfer"
        ? "transfer"
        : "expense";
  return emptyTransactionFormState({
    account_id: txn.account_id ?? "",
    source_account_id: txn.source_account_id ?? txn.from_account_id ?? "",
    destination_account_id: txn.destination_account_id ?? txn.to_account_id ?? "",
    category_id: txn.category_id ?? "",
    transaction_type: type,
    amount: String(txn.amount),
    currency: txn.currency,
    description: txn.description,
    transaction_date: txn.transaction_date,
    reference_number: txn.reference_number ?? "",
    tags: (txn.tags ?? []).join(", "),
    status: txn.status,
    scheduled: txn.status === "pending",
    settlement_status: txn.settlement_status === "in_transit" ? "in_transit" : "settled",
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
  if (!state.transaction_date.trim()) {
    throw new Error("Transaction date is required");
  }

  if (state.transaction_type === "transfer") {
    if (!state.source_account_id) {
      throw new Error("Source account is required");
    }
    if (!state.destination_account_id) {
      throw new Error("Destination account is required");
    }
    const create: TransactionCreate = {
      source_account_id: state.source_account_id,
      destination_account_id: state.destination_account_id,
      transaction_type: "transfer",
      amount: parseRequiredAmount(state.amount),
      currency: state.currency.trim().toUpperCase() || "USD",
      description: state.description.trim(),
      transaction_date: state.transaction_date.trim(),
      scheduled: state.scheduled,
      settlement_status: state.settlement_status,
    };
    return create;
  }

  if (!state.account_id) {
    throw new Error("Account is required");
  }
  if (!state.category_id) {
    throw new Error("Category is required");
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
  if (!state.transaction_date.trim()) {
    throw new Error("Transaction date is required");
  }

  if (state.transaction_type === "transfer") {
    if (!state.source_account_id) {
      throw new Error("Source account is required");
    }
    if (!state.destination_account_id) {
      throw new Error("Destination account is required");
    }
    const update: TransactionUpdate = {
      source_account_id: state.source_account_id,
      destination_account_id: state.destination_account_id,
      transaction_type: "transfer",
      amount: parseRequiredAmount(state.amount),
      currency: state.currency.trim().toUpperCase() || "USD",
      transaction_date: state.transaction_date.trim(),
      settlement_status: state.settlement_status,
    };
    if (state.description.trim() !== "") {
      update.description = state.description.trim();
    }
    return update;
  }

  if (!state.account_id) {
    throw new Error("Account is required");
  }
  if (!state.category_id) {
    throw new Error("Category is required");
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
