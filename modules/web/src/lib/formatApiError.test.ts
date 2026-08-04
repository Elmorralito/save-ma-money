import { describe, expect, it } from "vitest";

import { PapitaApiError } from "@/api/errors";
import { formatApiError, isGlobalOrMissingCategoryError } from "@/lib/formatApiError";

const emptyDiscovery = {
  breakingChanges: null,
  bulkMax: null,
  reportWindowMaxDays: null,
  cashFlowRefreshDefault: null,
  reportsForeignAccountStatus: null,
  errorCode: null,
  compatActive: [] as string[],
};

describe("formatApiError", () => {
  it("explains proxy 502 when the API is down", () => {
    const error = new PapitaApiError({
      message: "HTTP 502",
      status: 502,
      discovery: emptyDiscovery,
    });
    expect(formatApiError(error)).toMatch(/make api-all|make api-up/);
  });

  it("surfaces API 429 detail when present", () => {
    const error = new PapitaApiError({
      message: "Email rate limit exceeded. Wait a few minutes, or use local Admin register.",
      status: 429,
      discovery: emptyDiscovery,
    });
    expect(formatApiError(error)).toMatch(/rate limit/i);
  });

  it("appends Retry-After seconds on 429 when present", () => {
    const error = new PapitaApiError({
      message: "API rate limit exceeded for your plan. Try again later.",
      status: 429,
      discovery: emptyDiscovery,
      retryAfter: 45,
    });
    expect(formatApiError(error)).toMatch(/Retry after 45s/);
  });

  it("includes X-Papita-Error-Code when present", () => {
    const error = new PapitaApiError({
      message: "validation failed",
      status: 422,
      code: "validation_error",
      discovery: { ...emptyDiscovery, errorCode: "validation_error" },
    });
    expect(formatApiError(error)).toBe("validation failed [validation_error]");
  });

  it("maps report_window_too_large to a friendly message", () => {
    const error = new PapitaApiError({
      message: "report window must be at most 366 days",
      status: 400,
      code: "report_window_too_large",
      discovery: { ...emptyDiscovery, errorCode: "report_window_too_large" },
    });
    expect(formatApiError(error)).toBe(
      "Report date range exceeds the allowed maximum. Shorten the window and try again. [report_window_too_large]",
    );
  });

  it("flattens FastAPI 422 detail arrays", () => {
    const error = new PapitaApiError({
      message: "Request validation failed",
      status: 422,
      discovery: emptyDiscovery,
      body: {
        detail: [{ loc: ["body", "name"], msg: "Field required", type: "missing" }],
      },
    });
    expect(formatApiError(error)).toContain("body.name: Field required");
  });

  it("remaps Email not confirmed to clearer sign-in copy", () => {
    const error = new PapitaApiError({
      message: "Email not confirmed",
      status: 401,
      discovery: emptyDiscovery,
    });
    expect(formatApiError(error)).toMatch(/Confirm your email/i);
    expect(formatApiError(error)).toMatch(/inbox/i);
  });

  it("remaps email_not_confirmed error code without appending [code]", () => {
    const error = new PapitaApiError({
      message: "Email not confirmed",
      status: 401,
      code: "email_not_confirmed",
      discovery: emptyDiscovery,
    });
    expect(formatApiError(error)).toMatch(/Confirm your email/i);
    expect(formatApiError(error)).not.toContain("[email_not_confirmed]");
  });
});

describe("isGlobalOrMissingCategoryError", () => {
  it("detects API 404 Category not found", () => {
    const error = new PapitaApiError({
      message: "Category not found",
      status: 404,
      discovery: emptyDiscovery,
    });
    expect(isGlobalOrMissingCategoryError(error)).toBe(true);
  });
});
