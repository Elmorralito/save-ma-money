import { describe, expect, it, vi } from "vitest";

import { invalidateAfterLedgerWrite, invalidateAfterTemplateWrite } from "@/api/invalidateLedger";
import { queryKeys } from "@/api/queryKeys";

describe("invalidateLedger report invalidation", () => {
  it("invalidates reports queries on ledger writes", async () => {
    const invalidateQueries = vi.fn().mockResolvedValue(undefined);
    const removeQueries = vi.fn();
    await invalidateAfterLedgerWrite({ invalidateQueries, removeQueries } as never);
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: queryKeys.reports.all });
  });

  it("invalidates reports queries on template writes", async () => {
    const invalidateQueries = vi.fn().mockResolvedValue(undefined);
    const removeQueries = vi.fn();
    await invalidateAfterTemplateWrite({ invalidateQueries, removeQueries } as never);
    expect(invalidateQueries).toHaveBeenCalledWith({ queryKey: queryKeys.reports.all });
  });
});
