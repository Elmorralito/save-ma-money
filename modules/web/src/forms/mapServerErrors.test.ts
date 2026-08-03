import { describe, expect, it } from "vitest";

import { PapitaApiError } from "@/api/errors";
import { ACCOUNT_SERVER_FIELD_MAP } from "@/forms/fieldMaps";
import { apiLocToPath, mapServerErrors, shouldToastMutationError } from "@/forms/mapServerErrors";

const emptyDiscovery = {
  breakingChanges: null,
  bulkMax: null,
  reportWindowMaxDays: null,
  cashFlowRefreshDefault: null,
  reportsForeignAccountStatus: null,
  errorCode: null,
  compatActive: [] as string[],
};

describe("apiLocToPath", () => {
  it("strips body prefix from FastAPI loc", () => {
    expect(apiLocToPath(["body", "name"])).toBe("name");
    expect(apiLocToPath(["body", "banking_details", "entity"])).toBe("banking_details.entity");
  });
});

describe("mapServerErrors", () => {
  it("maps 422 detail locs onto form fields via fieldMap", () => {
    const error = new PapitaApiError({
      message: "Request validation failed",
      status: 422,
      discovery: emptyDiscovery,
      body: {
        detail: [
          { loc: ["body", "name"], msg: "Field required", type: "missing" },
          {
            loc: ["body", "banking_details", "entity"],
            msg: "Entity required",
            type: "missing",
          },
        ],
      },
    });

    const mapped = mapServerErrors(error, ACCOUNT_SERVER_FIELD_MAP);
    expect(mapped.fields).toEqual([
      { name: "name", message: "Field required" },
      { name: "banking_entity", message: "Entity required" },
    ]);
    expect(mapped.root).toBeNull();
  });

  it("puts unmapped nested locs on root", () => {
    const error = new PapitaApiError({
      message: "Request validation failed",
      status: 422,
      discovery: emptyDiscovery,
      body: {
        detail: [{ loc: ["body", "unknown_block", "x"], msg: "bad", type: "value_error" }],
      },
    });
    const mapped = mapServerErrors(error, ACCOUNT_SERVER_FIELD_MAP);
    expect(mapped.fields).toEqual([]);
    expect(mapped.root).toBe("unknown_block.x: bad");
  });

  it("surfaces X-Papita-Error-Code on root when there are no field details", () => {
    const error = new PapitaApiError({
      message: "bulk too large",
      status: 400,
      code: "bulk_too_large",
      discovery: { ...emptyDiscovery, errorCode: "bulk_too_large" },
    });
    const mapped = mapServerErrors(error);
    expect(mapped.fields).toEqual([]);
    expect(mapped.root).toBe("bulk too large [bulk_too_large]");
  });
});

describe("shouldToastMutationError", () => {
  it("toasts 429 and network failures", () => {
    expect(
      shouldToastMutationError(
        new PapitaApiError({
          message: "rate limited",
          status: 429,
          discovery: emptyDiscovery,
          retryAfter: 30,
        }),
      ),
    ).toBe(true);
    expect(shouldToastMutationError(new TypeError("Failed to fetch"))).toBe(true);
  });

  it("does not toast field-mapped 422 by status alone", () => {
    expect(
      shouldToastMutationError(
        new PapitaApiError({
          message: "Request validation failed",
          status: 422,
          discovery: emptyDiscovery,
        }),
      ),
    ).toBe(false);
  });
});
