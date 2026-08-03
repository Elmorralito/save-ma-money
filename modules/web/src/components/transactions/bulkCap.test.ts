import { describe, expect, it } from "vitest";

import { isBulkOverCap } from "@/components/transactions/bulkCap";

describe("isBulkOverCap", () => {
  it("flags counts above the contract max", () => {
    expect(isBulkOverCap(100, 100)).toBe(false);
    expect(isBulkOverCap(101, 100)).toBe(true);
  });
});
