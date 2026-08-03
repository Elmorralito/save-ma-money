import { describe, expect, it } from "vitest";

import { formatMoney } from "@/lib/formatMoney";

describe("formatMoney", () => {
  it("formats a known ISO currency", () => {
    const formatted = formatMoney(42.5, "USD");
    expect(formatted).toMatch(/42/);
    expect(formatted).toMatch(/\$|USD/);
  });

  it("falls back for an invalid currency code", () => {
    expect(formatMoney(1.5, "NOTACURRENCY")).toBe("1.50 NOTACURRENCY");
  });
});
