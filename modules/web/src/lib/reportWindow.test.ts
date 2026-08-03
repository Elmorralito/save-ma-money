import { describe, expect, it } from "vitest";

import { parseIsoDate, validateReportWindow } from "@/lib/reportWindow";

describe("parseIsoDate", () => {
  it("accepts valid calendar dates", () => {
    const parsed = parseIsoDate("2026-01-15");
    expect(parsed).not.toBeNull();
    expect(parsed?.getUTCFullYear()).toBe(2026);
    expect(parsed?.getUTCMonth()).toBe(0);
    expect(parsed?.getUTCDate()).toBe(15);
  });

  it("rejects malformed and impossible dates", () => {
    expect(parseIsoDate("2026-13-01")).toBeNull();
    expect(parseIsoDate("2026-02-30")).toBeNull();
    expect(parseIsoDate("not-a-date")).toBeNull();
    expect(parseIsoDate("")).toBeNull();
  });
});

describe("validateReportWindow", () => {
  it("accepts ordered windows within max days (API delta semantics)", () => {
    const result = validateReportWindow("2026-01-01", "2026-01-31", 366);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.spanDays).toBe(30);
    }
  });

  it("rejects inverted windows", () => {
    const result = validateReportWindow("2026-02-01", "2026-01-01", 366);
    expect(result).toEqual({
      ok: false,
      reason: "inverted",
      message: "Start date must be on or before end date.",
    });
  });

  it("rejects windows larger than maxDays using (end - start).days", () => {
    // 367-day delta with max 366 → too large (mirrors API _validate_report_window).
    const result = validateReportWindow("2025-01-01", "2026-01-03", 366);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe("too_large");
      expect(result.message).toContain("366");
    }
  });

  it("allows spanDays === maxDays (boundary)", () => {
    const result = validateReportWindow("2025-01-01", "2026-01-02", 366);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.spanDays).toBe(366);
    }
  });

  it("skips max-days check when contract max is unknown", () => {
    const result = validateReportWindow("2020-01-01", "2026-01-01", null);
    expect(result.ok).toBe(true);
  });

  it("rejects invalid date strings", () => {
    const result = validateReportWindow("bad", "2026-01-01", 90);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe("invalid_date");
    }
  });
});
