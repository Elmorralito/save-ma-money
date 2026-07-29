import { describe, expect, it } from "vitest";

import {
  isClientHttpError,
  isPapitaApiError,
  PapitaApiError,
  papitaApiErrorFromResponse,
} from "@/api/errors";
import { HEADER_BULK_MAX, HEADER_ERROR_CODE } from "@/api/headers";

describe("PapitaApiError", () => {
  it("exposes status, code, and discovery headers", () => {
    const error = new PapitaApiError({
      message: "too many",
      status: 400,
      code: "bulk_too_large",
      discovery: {
        breakingChanges: "ppt-044",
        bulkMax: 100,
        reportWindowMaxDays: 366,
        cashFlowRefreshDefault: false,
        reportsForeignAccountStatus: 404,
        errorCode: "bulk_too_large",
        compatActive: [],
      },
    });

    expect(isPapitaApiError(error)).toBe(true);
    expect(isClientHttpError(error)).toBe(true);
    expect(error.code).toBe("bulk_too_large");
    expect(error.discovery.bulkMax).toBe(100);
  });

  it("does not treat 5xx as client HTTP errors", () => {
    const error = new PapitaApiError({
      message: "boom",
      status: 500,
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
    expect(isClientHttpError(error)).toBe(false);
  });

  it("maps X-Papita-Error-Code from a failed Response", async () => {
    const response = new Response(JSON.stringify({ detail: "Bulk create exceeds max" }), {
      status: 400,
      headers: {
        "content-type": "application/json",
        [HEADER_ERROR_CODE]: "bulk_too_large",
        [HEADER_BULK_MAX]: "100",
      },
    });

    const error = await papitaApiErrorFromResponse(response);
    expect(error.message).toBe("Bulk create exceeds max");
    expect(error.code).toBe("bulk_too_large");
    expect(error.discovery.bulkMax).toBe(100);
  });
});
