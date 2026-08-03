import type { MovementCreate, MovementResponse, MovementUpdate } from "@/types/domain";

export type MovementFormState = {
  source_account_id: string;
  destination_account_id: string;
  amount: string;
  currency: string;
  description: string;
  movement_date: string;
  scheduled: boolean;
};

function todayDateInput(): string {
  return new Date().toISOString().slice(0, 10);
}

export function emptyMovementFormState(
  overrides: Partial<MovementFormState> = {},
): MovementFormState {
  return {
    source_account_id: "",
    destination_account_id: "",
    amount: "",
    currency: "USD",
    description: "",
    movement_date: todayDateInput(),
    scheduled: false,
    ...overrides,
  };
}

export function movementFormFromResponse(movement: MovementResponse): MovementFormState {
  return emptyMovementFormState({
    source_account_id: movement.source_account_id,
    destination_account_id: movement.destination_account_id,
    amount: String(movement.amount),
    currency: movement.currency,
    description: movement.description,
    movement_date: movement.movement_date,
    scheduled: movement.status === "pending",
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

/** Map form state → OpenAPI ``MovementCreate``. */
export function toMovementCreate(state: MovementFormState): MovementCreate {
  if (!state.source_account_id) {
    throw new Error("Source account is required");
  }
  if (!state.destination_account_id) {
    throw new Error("Destination account is required");
  }
  if (state.source_account_id === state.destination_account_id) {
    throw new Error("Source and destination accounts must differ");
  }
  if (!state.movement_date.trim()) {
    throw new Error("Movement date is required");
  }

  return {
    source_account_id: state.source_account_id,
    destination_account_id: state.destination_account_id,
    amount: parseRequiredAmount(state.amount),
    currency: state.currency.trim().toUpperCase() || "USD",
    description: state.description.trim(),
    movement_date: state.movement_date.trim(),
    scheduled: state.scheduled,
  };
}

/** Map form state → OpenAPI ``MovementUpdate`` (pending only on the server). */
export function toMovementUpdate(state: MovementFormState): MovementUpdate {
  if (!state.source_account_id) {
    throw new Error("Source account is required");
  }
  if (!state.destination_account_id) {
    throw new Error("Destination account is required");
  }
  if (state.source_account_id === state.destination_account_id) {
    throw new Error("Source and destination accounts must differ");
  }
  if (!state.movement_date.trim()) {
    throw new Error("Movement date is required");
  }

  const update: MovementUpdate = {
    source_account_id: state.source_account_id,
    destination_account_id: state.destination_account_id,
    amount: parseRequiredAmount(state.amount),
    currency: state.currency.trim().toUpperCase() || "USD",
    movement_date: state.movement_date.trim(),
  };
  if (state.description.trim() !== "") {
    update.description = state.description.trim();
  }
  return update;
}
