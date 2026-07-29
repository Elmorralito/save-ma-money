import { describe, expect, it } from "vitest";

import { PapitaApiError } from "@/api/errors";
import { createAppQueryClient } from "@/api/queryClient";

describe("createAppQueryClient", () => {
  it("does not retry 4xx PapitaApiError", () => {
    const client = createAppQueryClient();
    const retry = client.getDefaultOptions().queries?.retry;
    expect(typeof retry).toBe("function");
    if (typeof retry !== "function") {
      return;
    }

    const clientError = new PapitaApiError({
      message: "bad",
      status: 400,
      discovery: {
        breakingChanges: null,
        bulkMax: null,
        reportWindowMaxDays: null,
        cashFlowRefreshDefault: null,
        reportsForeignAccountStatus: null,
        errorCode: null,
        compatActive: [],
      },
    });

    expect(retry(0, clientError)).toBe(false);
    expect(retry(0, new Error("network"))).toBe(true);
    expect(retry(2, new Error("network"))).toBe(false);
  });
});
