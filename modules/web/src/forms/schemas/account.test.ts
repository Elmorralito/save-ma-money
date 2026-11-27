import { describe, expect, it } from "vitest";

import { emptyAccountFormState } from "@/components/accounts/accountFormState";
import { accountFormSchema } from "@/forms/schemas/account";

describe("accountFormSchema", () => {
  it("accepts a valid checking account form", () => {
    const result = accountFormSchema.safeParse(
      emptyAccountFormState({
        name: "Everyday",
        banking_entity: "Local Bank",
      }),
    );
    expect(result.success).toBe(true);
  });

  it("requires banking entity for checking", () => {
    const result = accountFormSchema.safeParse(
      emptyAccountFormState({
        name: "Everyday",
        banking_entity: "",
      }),
    );
    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error.issues.some((issue) => issue.path[0] === "banking_entity")).toBe(true);
    }
  });

  it("rejects empty name", () => {
    const result = accountFormSchema.safeParse(emptyAccountFormState({ name: "  " }));
    expect(result.success).toBe(false);
  });

  it("validates extension-specific required fields for trading, credit card, loan, and real estate", () => {
    const trading = accountFormSchema.safeParse(
      emptyAccountFormState({ account_kind: "investment_brokerage", name: "IBKR" }),
    );
    expect(trading.success).toBe(false);

    const cc = accountFormSchema.safeParse(
      emptyAccountFormState({ account_kind: "credit_card", name: "Visa" }),
    );
    expect(cc.success).toBe(false);

    const loan = accountFormSchema.safeParse(
      emptyAccountFormState({
        account_kind: "loan_mortgage",
        name: "Mortgage",
        loan_insurance_payment: "",
        loan_extras_payment: "",
      }),
    );
    expect(loan.success).toBe(false);

    const re = accountFormSchema.safeParse(
      emptyAccountFormState({ account_kind: "real_estate", name: "Apt" }),
    );
    expect(re.success).toBe(false);
  });
});
