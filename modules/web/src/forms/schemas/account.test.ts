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
});
