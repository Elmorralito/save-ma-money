import { beforeEach, describe, expect, it, vi } from "vitest";

import { PapitaApiError } from "@/api/errors";
import { parseDiscoveryHeaders } from "@/api/headers";
import * as http from "@/api/http";
import { getLatestIngestionRun, listIngestionRuns } from "@/api/ingestion";

vi.mock("@/api/http", () => ({
  apiFetch: vi.fn(),
}));

describe("ingestion API client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns null when /ingestion/runs/latest replies 404", async () => {
    vi.mocked(http.apiFetch).mockRejectedValue(
      new PapitaApiError({
        status: 404,
        message: "Not found",
        code: "NOT_FOUND",
        discovery: parseDiscoveryHeaders(new Headers()),
      }),
    );

    const run = await getLatestIngestionRun();
    expect(run).toBeNull();
  });

  it("rethrows non-404 errors from /ingestion/runs/latest", async () => {
    vi.mocked(http.apiFetch).mockRejectedValue(
      new PapitaApiError({
        status: 503,
        message: "Unavailable",
        code: "SERVICE_UNAVAILABLE",
        discovery: parseDiscoveryHeaders(new Headers()),
      }),
    );

    await expect(getLatestIngestionRun()).rejects.toBeInstanceOf(PapitaApiError);
  });

  it("passes pagination params to /ingestion/runs", async () => {
    vi.mocked(http.apiFetch).mockResolvedValue({
      data: { items: [], total: 0, skip: 0, limit: 5 },
      response: new Response(null, { status: 200 }),
      discovery: parseDiscoveryHeaders(new Headers()),
    });

    await listIngestionRuns({ limit: 5, skip: 0 });
    expect(http.apiFetch).toHaveBeenCalledWith("/api/v1/ingestion/runs?skip=0&limit=5", {
      signal: undefined,
    });
  });
});
