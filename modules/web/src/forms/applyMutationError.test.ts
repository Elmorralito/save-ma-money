import { beforeEach, describe, expect, it, vi } from "vitest";

import { PapitaApiError } from "@/api/errors";
import { applyMutationError } from "@/forms/applyMutationError";

const emptyDiscovery = {
  breakingChanges: null,
  bulkMax: null,
  reportWindowMaxDays: null,
  cashFlowRefreshDefault: null,
  reportsForeignAccountStatus: null,
  errorCode: null,
  compatActive: [] as string[],
};

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

import { toast } from "sonner";

describe("applyMutationError", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("maps 422 field errors inline without toast", () => {
    const setError = vi.fn();
    const error = new PapitaApiError({
      message: "Validation failed",
      status: 422,
      discovery: emptyDiscovery,
      body: {
        detail: [{ loc: ["body", "name"], msg: "required", type: "value_error" }],
      },
    });

    applyMutationError(error, { setError, fieldMap: { name: "name" } });

    expect(setError).toHaveBeenCalledWith("name", {
      type: "server",
      message: "required",
    });
    expect(toast.error).not.toHaveBeenCalled();
  });

  it("toasts and sets root on 429", () => {
    const setError = vi.fn();
    const error = new PapitaApiError({
      message: "Too many requests",
      status: 429,
      discovery: emptyDiscovery,
      retryAfter: 30,
    });

    applyMutationError(error, { setError });

    expect(toast.error).toHaveBeenCalled();
    expect(setError).toHaveBeenCalledWith("root", {
      type: "server",
      message: expect.stringMatching(/Too many requests|30/),
    });
  });
});
