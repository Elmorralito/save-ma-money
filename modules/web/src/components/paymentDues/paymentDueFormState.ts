import type {
  TransactionTemplateCreate,
  TransactionTemplateResponse,
  TransactionTemplateUpdate,
} from "@/types/domain";

export type PaymentDueSchedule = "recurring" | "one_off";

export type PaymentDueFormState = {
  name: string;
  description: string;
  category_id: string;
  from_account_id: string;
  planned_amount: string;
  schedule: PaymentDueSchedule;
  planned_day: string;
  use_month_end: boolean;
  due_date: string;
  remind_days_before: string;
  tags: string;
  is_active: boolean;
};

function todayDateInput(): string {
  return new Date().toISOString().slice(0, 10);
}

export function emptyPaymentDueFormState(
  overrides: Partial<PaymentDueFormState> = {},
): PaymentDueFormState {
  return {
    name: "",
    description: "",
    category_id: "",
    from_account_id: "",
    planned_amount: "",
    schedule: "recurring",
    planned_day: "1",
    use_month_end: false,
    due_date: todayDateInput(),
    remind_days_before: "3",
    tags: "",
    is_active: true,
    ...overrides,
  };
}

export function paymentDueFormFromResponse(
  template: TransactionTemplateResponse,
): PaymentDueFormState {
  const isOneOff = Boolean(template.due_date);
  return emptyPaymentDueFormState({
    name: template.name,
    description: template.description ?? "",
    category_id: template.category_id,
    from_account_id: template.from_account_id ?? "",
    planned_amount: String(template.planned_amount),
    schedule: isOneOff ? "one_off" : "recurring",
    planned_day: String(template.planned_day),
    use_month_end: Boolean(template.use_month_end),
    due_date: template.due_date ?? todayDateInput(),
    remind_days_before:
      template.remind_days_before === null || template.remind_days_before === undefined
        ? ""
        : String(template.remind_days_before),
    tags: (template.tags ?? []).join(", "),
    is_active: Boolean(template.is_active),
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

function parsePlannedDay(value: string): number {
  const parsed = Number(value.trim());
  if (!Number.isInteger(parsed) || parsed < 1 || parsed > 31) {
    throw new Error("Planned day must be an integer from 1 to 31");
  }
  return parsed;
}

function parseOptionalRemindDays(value: string): number | null | undefined {
  const trimmed = value.trim();
  if (trimmed === "") {
    return null;
  }
  const parsed = Number(trimmed);
  if (!Number.isInteger(parsed) || parsed < 0) {
    throw new Error("Remind days before must be zero or a positive integer");
  }
  return parsed;
}

function parseTags(value: string): string[] {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part.length > 0);
}

function dayFromDateInput(value: string): number {
  const day = Number(value.slice(8, 10));
  if (!Number.isInteger(day) || day < 1 || day > 31) {
    throw new Error("Due date is required for one-off dues");
  }
  return day;
}

/** Map form state → OpenAPI ``TransactionTemplateCreate``. */
export function toTransactionTemplateCreate(state: PaymentDueFormState): TransactionTemplateCreate {
  if (!state.name.trim()) {
    throw new Error("Name is required");
  }
  if (!state.category_id) {
    throw new Error("Category is required");
  }

  const remind = parseOptionalRemindDays(state.remind_days_before);
  const create: TransactionTemplateCreate = {
    name: state.name.trim(),
    description: state.description.trim(),
    category_id: state.category_id,
    planned_amount: parseRequiredAmount(state.planned_amount),
    planned_day:
      state.schedule === "one_off"
        ? dayFromDateInput(state.due_date)
        : parsePlannedDay(state.planned_day),
    use_month_end: state.schedule === "recurring" ? state.use_month_end : false,
    tags: parseTags(state.tags),
  };

  if (state.schedule === "one_off") {
    if (!state.due_date.trim()) {
      throw new Error("Due date is required for one-off dues");
    }
    create.due_date = state.due_date.trim();
  } else {
    create.due_date = null;
  }

  if (state.from_account_id) {
    create.from_account_id = state.from_account_id;
  } else {
    create.from_account_id = null;
  }

  if (remind !== undefined) {
    create.remind_days_before = remind;
  }

  return create;
}

/** Map form state → OpenAPI ``TransactionTemplateUpdate``. */
export function toTransactionTemplateUpdate(state: PaymentDueFormState): TransactionTemplateUpdate {
  const create = toTransactionTemplateCreate(state);
  return {
    name: create.name,
    description: create.description,
    category_id: create.category_id,
    planned_amount: create.planned_amount,
    planned_day: create.planned_day,
    use_month_end: create.use_month_end,
    due_date: create.due_date ?? null,
    remind_days_before: create.remind_days_before ?? null,
    from_account_id: create.from_account_id ?? null,
    tags: create.tags ?? [],
    is_active: state.is_active,
  };
}
