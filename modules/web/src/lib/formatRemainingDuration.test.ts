import { describe, expect, it } from "vitest";

import { formatRemainingDuration, secondsUntil } from "@/lib/formatRemainingDuration";

describe("formatRemainingDuration", () => {
  it("formats hours, minutes, and seconds", () => {
    expect(formatRemainingDuration(3661)).toBe("1h 01m 01s");
  });

  it("formats minutes and seconds", () => {
    expect(formatRemainingDuration(125)).toBe("2m 05s");
  });

  it("formats seconds only", () => {
    expect(formatRemainingDuration(9)).toBe("9s");
  });

  it("returns expired for non-positive values", () => {
    expect(formatRemainingDuration(0)).toBe("expired");
    expect(formatRemainingDuration(-3)).toBe("expired");
  });
});

describe("secondsUntil", () => {
  it("returns remaining whole seconds", () => {
    expect(secondsUntil(1_700_000_100, 1_700_000_000_000)).toBe(100);
  });

  it("clamps at zero when past expiry", () => {
    expect(secondsUntil(1_700_000_000, 1_700_000_500_000)).toBe(0);
  });
});
