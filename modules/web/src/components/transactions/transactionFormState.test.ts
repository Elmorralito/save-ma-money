import { describe, expect, it } from "vitest";

import {
  emptyTransactionFormState,
  toTransactionCreate,
  toTransactionUpdate,
  transactionFormFromResponse,
} from "@/components/transactions/transactionFormState";

describe("transactionFormState", () => {
  it("maps create payload from form state", () => {
    const body = toTransactionCreate(
      emptyTransactionFormState({
        account_id: "11111111-1111-1111-1111-111111111111",
        category_id: "33333333-3333-3333-3333-333333333333",
        transaction_type: "expense",
        amount: "12.5",
        currency: "usd",
        description: "Lunch",
        transaction_date: "2026-08-01",
        tags: "food, out",
      }),
    );

    expect(body).toEqual({
      account_id: "11111111-1111-1111-1111-111111111111",
      category_id: "33333333-3333-3333-3333-333333333333",
      transaction_type: "expense",
      amount: 12.5,
      currency: "USD",
      description: "Lunch",
      transaction_date: "2026-08-01",
      tags: ["food", "out"],
    });
  });

  it("round-trips response into update without inventing fields", () => {
    const form = transactionFormFromResponse({
      id: "22222222-2222-2222-2222-222222222222",
      account_id: "11111111-1111-1111-1111-111111111111",
      category_id: "33333333-3333-3333-3333-333333333333",
      amount: 20,
      currency: "USD",
      description: "Pay",
      status: "completed",
      transaction_date: "2026-07-01",
      transaction_type: "income",
      is_recurring: false,
      tags: ["salary"],
    });
    const update = toTransactionUpdate(form);
    expect(update.transaction_type).toBe("income");
    expect(update.amount).toBe(20);
    expect(update.tags).toEqual(["salary"]);
  });

  it("rejects non-positive amounts", () => {
    expect(() =>
      toTransactionCreate(
        emptyTransactionFormState({
          account_id: "11111111-1111-1111-1111-111111111111",
          category_id: "33333333-3333-3333-3333-333333333333",
          amount: "0",
          transaction_date: "2026-08-01",
        }),
      ),
    ).toThrow(/positive/i);
  });
});
