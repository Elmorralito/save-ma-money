import {
  defaultLedgerSideForKind,
  extensionFieldForAccountKind,
  type AccountKindSlug,
  type LedgerSideSlug,
} from "@/lib/accountKinds";
import type {
  AccountCreate,
  AccountResponse,
  AccountUpdate,
  BankingDetailsSchema,
  CreditCardDetailsSchema,
  LoanDetailsSchema,
  RealEstateDetailsSchema,
  TradingDetailsSchema,
} from "@/types/domain";

export type AccountFormState = {
  name: string;
  description: string;
  account_kind: AccountKindSlug;
  ledger_side: LedgerSideSlug;
  currency: string;
  initial_value: string;
  banking_entity: string;
  banking_account_number: string;
  trading_buy_value: string;
  trading_units: string;
  re_address: string;
  re_city: string;
  re_country: string;
  re_total_area: string;
  re_built_area: string;
  re_area_unit: string;
  re_ownership: string;
  re_participation: string;
  credit_limit: string;
  loan_is_paid_off: boolean;
  loan_insurance_payment: string;
  loan_extras_payment: string;
  is_active: boolean;
};

export function emptyAccountFormState(overrides: Partial<AccountFormState> = {}): AccountFormState {
  return {
    name: "",
    description: "",
    account_kind: "checking",
    ledger_side: "asset",
    currency: "USD",
    initial_value: "",
    banking_entity: "",
    banking_account_number: "",
    trading_buy_value: "",
    trading_units: "1",
    re_address: "",
    re_city: "",
    re_country: "",
    re_total_area: "",
    re_built_area: "",
    re_area_unit: "sq_mt",
    re_ownership: "full",
    re_participation: "1",
    credit_limit: "",
    loan_is_paid_off: false,
    loan_insurance_payment: "0",
    loan_extras_payment: "0",
    is_active: true,
    ...overrides,
  };
}

export function accountFormFromResponse(account: AccountResponse): AccountFormState {
  return emptyAccountFormState({
    name: account.name,
    description: "",
    account_kind: account.account_kind as AccountKindSlug,
    ledger_side: account.ledger_side as LedgerSideSlug,
    currency: account.currency,
    initial_value: "",
    banking_entity: account.banking_details?.entity ?? "",
    banking_account_number: account.banking_details?.account_number ?? "",
    trading_buy_value:
      account.trading_details?.buy_value !== undefined
        ? String(account.trading_details.buy_value)
        : "",
    trading_units:
      account.trading_details?.units !== undefined ? String(account.trading_details.units) : "1",
    re_address: account.real_estate_details?.address ?? "",
    re_city: account.real_estate_details?.city ?? "",
    re_country: account.real_estate_details?.country ?? "",
    re_total_area:
      account.real_estate_details?.total_area !== undefined
        ? String(account.real_estate_details.total_area)
        : "",
    re_built_area:
      account.real_estate_details?.built_area !== undefined
        ? String(account.real_estate_details.built_area)
        : "",
    re_area_unit: account.real_estate_details?.area_unit ?? "sq_mt",
    re_ownership: account.real_estate_details?.ownership ?? "full",
    re_participation:
      account.real_estate_details?.participation !== undefined
        ? String(account.real_estate_details.participation)
        : "1",
    credit_limit:
      account.credit_card_details?.credit_limit !== undefined
        ? String(account.credit_card_details.credit_limit)
        : "",
    loan_is_paid_off: account.loan_details?.is_paid_off ?? false,
    loan_insurance_payment:
      account.loan_details?.insurance_payment !== undefined
        ? String(account.loan_details.insurance_payment)
        : "0",
    loan_extras_payment:
      account.loan_details?.extras_payment !== undefined
        ? String(account.loan_details.extras_payment)
        : "0",
    is_active: account.is_active,
  });
}

function parseOptionalNumber(value: string): number | null {
  const trimmed = value.trim();
  if (trimmed === "") {
    return null;
  }
  const parsed = Number(trimmed);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseRequiredNumber(value: string, label: string): number {
  const parsed = parseOptionalNumber(value);
  if (parsed === null) {
    throw new Error(`${label} is required`);
  }
  return parsed;
}

function buildExtensionBlocks(
  state: AccountFormState,
): Pick<
  AccountCreate,
  | "banking_details"
  | "trading_details"
  | "real_estate_details"
  | "credit_card_details"
  | "loan_details"
> {
  const field = extensionFieldForAccountKind(state.account_kind);
  if (field === "banking_details") {
    const banking_details: BankingDetailsSchema = {
      entity: state.banking_entity.trim(),
      account_number: state.banking_account_number.trim() || null,
    };
    return { banking_details };
  }
  if (field === "trading_details") {
    const trading_details: TradingDetailsSchema = {
      buy_value: parseRequiredNumber(state.trading_buy_value, "Buy value"),
      units: Math.max(1, Math.trunc(parseRequiredNumber(state.trading_units, "Units"))),
    };
    return { trading_details };
  }
  if (field === "real_estate_details") {
    const real_estate_details: RealEstateDetailsSchema = {
      address: state.re_address.trim(),
      city: state.re_city.trim(),
      country: state.re_country.trim(),
      total_area: parseRequiredNumber(state.re_total_area, "Total area"),
      built_area: parseRequiredNumber(state.re_built_area, "Built area"),
      area_unit: state.re_area_unit,
      ownership: state.re_ownership,
      participation: parseRequiredNumber(state.re_participation, "Participation"),
    };
    return { real_estate_details };
  }
  if (field === "credit_card_details") {
    const credit_card_details: CreditCardDetailsSchema = {
      credit_limit: parseRequiredNumber(state.credit_limit, "Credit limit"),
    };
    return { credit_card_details };
  }
  if (field === "loan_details") {
    const loan_details: LoanDetailsSchema = {
      is_paid_off: state.loan_is_paid_off,
      insurance_payment: parseRequiredNumber(state.loan_insurance_payment, "Insurance payment"),
      extras_payment: parseRequiredNumber(state.loan_extras_payment, "Extras payment"),
    };
    return { loan_details };
  }
  return {};
}

/** Map form state → OpenAPI ``AccountCreate`` (no client-invented fields). */
export function toAccountCreate(state: AccountFormState): AccountCreate {
  // Omit empty initial_value — sending JSON null can persist SQL NULL that later
  // surfaces as NaN through DataFrame→DTO list paths (breaks /accounts).
  const create: AccountCreate = {
    name: state.name.trim(),
    description: state.description,
    account_kind: state.account_kind,
    ledger_side: state.ledger_side,
    currency: state.currency.trim().toUpperCase() || "USD",
    ...buildExtensionBlocks(state),
  };
  const initialValue = parseOptionalNumber(state.initial_value);
  if (initialValue !== null) {
    create.initial_value = initialValue;
  }
  return create;
}

/** Map form state → OpenAPI ``AccountUpdate`` (kind/ledger immutable on wire). */
export function toAccountUpdate(state: AccountFormState): AccountUpdate {
  // Omit response-missing optionals when empty so ``exclude_unset`` merges do not wipe
  // server ``description`` / ``initial_value`` (AccountResponse does not round-trip them).
  const update: AccountUpdate = {
    name: state.name.trim(),
    currency: state.currency.trim().toUpperCase() || "USD",
    is_active: state.is_active,
    ...buildExtensionBlocks(state),
  };
  if (state.description.trim() !== "") {
    update.description = state.description;
  }
  const initialValue = parseOptionalNumber(state.initial_value);
  if (initialValue !== null) {
    update.initial_value = initialValue;
  }
  return update;
}

export function applyAccountKindChange(
  state: AccountFormState,
  kind: AccountKindSlug,
): AccountFormState {
  return {
    ...state,
    account_kind: kind,
    ledger_side: defaultLedgerSideForKind(kind),
  };
}
