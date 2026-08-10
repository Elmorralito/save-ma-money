import { describe, expect, it } from "vitest";

import {
  emptyPaymentDueFormState,
  toTransactionTemplateCreate,
  toTransactionTemplateUpdate,
} from "@/components/paymentDues/paymentDueFormState";

const CATEGORY_ID = "11111111-1111-1111-1111-111111111111";
const ACCOUNT_ID = "22222222-2222-2222-2222-222222222222";

describe("paymentDueFormState", () => {
  it("maps recurring form to create payload", () => {
    const create = toTransactionTemplateCreate(
      emptyPaymentDueFormState({
        name: " Rent ",
        category_id: CATEGORY_ID,
        from_account_id: ACCOUNT_ID,
        planned_amount: "1200.5",
        schedule: "recurring",
        planned_day: "15",
        use_month_end: false,
        remind_days_before: "3",
        tags: "housing, bills",
      }),
    );

    expect(create).toEqual({
      name: "Rent",
      description: "",
      category_id: CATEGORY_ID,
      planned_amount: 1200.5,
      planned_day: 15,
      use_month_end: false,
      due_date: null,
      from_account_id: ACCOUNT_ID,
      remind_days_before: 3,
      tags: ["housing", "bills"],
    });
  });

  it("maps one-off form using due date day for planned_day", () => {
    const create = toTransactionTemplateCreate(
      emptyPaymentDueFormState({
        name: "Passport renewal",
        category_id: CATEGORY_ID,
        planned_amount: "160",
        schedule: "one_off",
        due_date: "2026-09-20",
        remind_days_before: "",
      }),
    );

    expect(create.due_date).toBe("2026-09-20");
    expect(create.planned_day).toBe(20);
    expect(create.use_month_end).toBe(false);
    expect(create.remind_days_before).toBeNull();
  });

  it("includes is_active on update", () => {
    const update = toTransactionTemplateUpdate(
      emptyPaymentDueFormState({
        name: "Utilities",
        category_id: CATEGORY_ID,
        planned_amount: "80",
        schedule: "recurring",
        planned_day: "1",
        is_active: false,
      }),
    );

    expect(update.is_active).toBe(false);
    expect(update.name).toBe("Utilities");
  });

  it("rejects missing category", () => {
    expect(() =>
      toTransactionTemplateCreate(
        emptyPaymentDueFormState({
          name: "Bill",
          planned_amount: "10",
        }),
      ),
    ).toThrow("Category is required");
  });
});
