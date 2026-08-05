import { describe, expect, it } from "vitest";

import { formatSlugLabel } from "@/lib/formatSlugLabel";

describe("formatSlugLabel", () => {
  it("maps known API slugs to friendly labels", () => {
    expect(formatSlugLabel("checking")).toBe("Checking");
    expect(formatSlugLabel("investment_brokerage")).toBe("Investment brokerage");
    expect(formatSlugLabel("expense")).toBe("Expense");
    expect(formatSlugLabel("pending")).toBe("Pending");
  });

  it("title-cases unknown underscore slugs", () => {
    expect(formatSlugLabel("foo_bar_baz")).toBe("Foo Bar Baz");
  });

  it("returns empty for blank input", () => {
    expect(formatSlugLabel(null)).toBe("");
    expect(formatSlugLabel("  ")).toBe("");
  });
});
