import { describe, expect, it } from "vitest";

import { emptyCategoryFormState } from "@/components/categories/categoryFormState";
import { categoryFormSchema } from "@/forms/schemas/category";

describe("categoryFormSchema", () => {
  it("accepts a minimal valid category", () => {
    const result = categoryFormSchema.safeParse(emptyCategoryFormState({ name: "Food" }));
    expect(result.success).toBe(true);
  });

  it("rejects invalid color when provided", () => {
    const result = categoryFormSchema.safeParse(
      emptyCategoryFormState({ name: "Food", color: "red" }),
    );
    expect(result.success).toBe(false);
  });

  it("allows empty color", () => {
    const result = categoryFormSchema.safeParse(
      emptyCategoryFormState({ name: "Food", color: "" }),
    );
    expect(result.success).toBe(true);
  });
});
