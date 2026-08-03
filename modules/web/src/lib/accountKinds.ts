/**
 * API account_kind / ledger_side slugs used for form selects.
 *
 * Values match papita_txnsapi lowercase slugs — not a reimplementation of model enums.
 */

export const ACCOUNT_KIND_SLUGS = [
  "checking",
  "savings",
  "cash",
  "investment_brokerage",
  "real_estate",
  "credit_card",
  "loan_mortgage",
  "other_asset",
  "other_liability",
] as const;

export type AccountKindSlug = (typeof ACCOUNT_KIND_SLUGS)[number];

export const LEDGER_SIDE_SLUGS = ["asset", "liability"] as const;

export type LedgerSideSlug = (typeof LEDGER_SIDE_SLUGS)[number];

export const AREA_UNIT_SLUGS = ["sq_mt", "sq_ft", "ac", "ha", "blk"] as const;

export const OWNERSHIP_SLUGS = ["full", "partial"] as const;

export type AccountExtensionField =
  | "banking_details"
  | "trading_details"
  | "real_estate_details"
  | "credit_card_details"
  | "loan_details"
  | null;

/** Which OpenAPI extension block the create/update form should collect for a kind. */
export function extensionFieldForAccountKind(kind: string): AccountExtensionField {
  switch (kind) {
    case "checking":
    case "savings":
    case "cash":
      return "banking_details";
    case "investment_brokerage":
      return "trading_details";
    case "real_estate":
      return "real_estate_details";
    case "credit_card":
      return "credit_card_details";
    case "loan_mortgage":
      return "loan_details";
    default:
      return null;
  }
}

/** Presentation default for ledger_side when the user changes kind (still user-editable). */
export function defaultLedgerSideForKind(kind: string): LedgerSideSlug {
  if (kind === "credit_card" || kind === "loan_mortgage" || kind === "other_liability") {
    return "liability";
  }
  return "asset";
}
