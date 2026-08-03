import { describe, expect, it } from "vitest";

import {
  emptyMovementFormState,
  toMovementCreate,
  toMovementUpdate,
} from "@/components/movements/movementFormState";

describe("movementFormState", () => {
  it("maps create payload including scheduled flag", () => {
    const body = toMovementCreate(
      emptyMovementFormState({
        source_account_id: "11111111-1111-1111-1111-111111111111",
        destination_account_id: "22222222-2222-2222-2222-222222222222",
        amount: "40",
        currency: "usd",
        description: "Rent split",
        movement_date: "2026-08-01",
        scheduled: true,
      }),
    );
    expect(body).toEqual({
      source_account_id: "11111111-1111-1111-1111-111111111111",
      destination_account_id: "22222222-2222-2222-2222-222222222222",
      amount: 40,
      currency: "USD",
      description: "Rent split",
      movement_date: "2026-08-01",
      scheduled: true,
    });
  });

  it("rejects identical source and destination", () => {
    expect(() =>
      toMovementUpdate(
        emptyMovementFormState({
          source_account_id: "11111111-1111-1111-1111-111111111111",
          destination_account_id: "11111111-1111-1111-1111-111111111111",
          amount: "10",
          movement_date: "2026-08-01",
        }),
      ),
    ).toThrow(/differ/i);
  });
});
