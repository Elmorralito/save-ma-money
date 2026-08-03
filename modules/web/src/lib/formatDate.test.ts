import { describe, expect, it } from "vitest";

import { formatDate, formatDateTime } from "@/lib/formatDate";

describe("formatDate", () => {
  it("formats a valid ISO date with Intl", () => {
    const formatted = formatDate("2026-01-15T12:00:00.000Z", "en-US");
    expect(formatted).toMatch(/Jan/);
    expect(formatted).toMatch(/15/);
    expect(formatted).toMatch(/2026/);
  });

  it("returns the original string for invalid dates", () => {
    expect(formatDate("not-a-date")).toBe("not-a-date");
  });
});

describe("formatDateTime", () => {
  it("includes a time component for valid values", () => {
    const formatted = formatDateTime("2026-01-15T15:30:00.000Z", "en-US");
    expect(formatted).toMatch(/2026/);
    expect(formatted.length).toBeGreaterThan("Jan 15, 2026".length);
  });

  it("returns empty string for invalid non-string values", () => {
    expect(formatDateTime(Number.NaN)).toBe("");
  });
});
