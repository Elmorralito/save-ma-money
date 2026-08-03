import { describe, expect, it } from "vitest";

import {
  emptyAccountFormState,
  toAccountCreate,
  toAccountUpdate,
} from "@/components/accounts/accountFormState";

describe("accountFormState", () => {
  it("builds OpenAPI AccountCreate with banking_details for checking", () => {
    const payload = toAccountCreate(
      emptyAccountFormState({
        name: " Everyday ",
        account_kind: "checking",
        ledger_side: "asset",
        banking_entity: "Local Bank",
        banking_account_number: "****1234",
        initial_value: "100",
      }),
    );

    expect(payload).toEqual({
      name: "Everyday",
      description: "",
      account_kind: "checking",
      ledger_side: "asset",
      currency: "USD",
      initial_value: 100,
      banking_details: { entity: "Local Bank", account_number: "****1234" },
    });
  });

  it("omits kind/ledger on AccountUpdate", () => {
    const payload = toAccountUpdate(
      emptyAccountFormState({
        name: "Savings",
        account_kind: "savings",
        ledger_side: "asset",
        banking_entity: "CU",
        is_active: false,
      }),
    );

    expect(payload).toMatchObject({
      name: "Savings",
      is_active: false,
      banking_details: { entity: "CU", account_number: null },
    });
    expect(payload).not.toHaveProperty("account_kind");
    expect(payload).not.toHaveProperty("ledger_side");
  });

  it("omits empty description and initial_value on AccountUpdate", () => {
    const payload = toAccountUpdate(
      emptyAccountFormState({
        name: "Cash",
        account_kind: "cash",
        banking_entity: "Wallet",
        description: "  ",
        initial_value: "",
      }),
    );
    expect(payload).not.toHaveProperty("description");
    expect(payload).not.toHaveProperty("initial_value");
  });
});
