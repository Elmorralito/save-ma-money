import { afterEach, describe, expect, it, vi } from "vitest";

import { PapitaApiError } from "@/api/errors";
import { HEADER_ERROR_CODE } from "@/api/headers";
import { apiFetch } from "@/api/http";

describe("apiFetch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("sends credentials include and forwards AbortSignal", async () => {
    const signal = new AbortController().signal;
    const fetchMock = vi.fn<typeof fetch>(async () =>
      Response.json({ status: "healthy" }, { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await apiFetch<{ status: string }>("/api/v1/health", { signal });

    expect(result.data.status).toBe("healthy");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/health",
      expect.objectContaining({
        credentials: "include",
        signal,
        method: "GET",
      }),
    );
  });

  it("throws PapitaApiError with error code on non-OK responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        Response.json(
          { detail: "nope" },
          {
            status: 404,
            headers: { [HEADER_ERROR_CODE]: "report_account_not_found" },
          },
        ),
      ),
    );

    await expect(apiFetch("/api/v1/meta/client-contract")).rejects.toBeInstanceOf(PapitaApiError);

    try {
      await apiFetch("/api/v1/meta/client-contract");
      expect.fail("expected apiFetch to throw");
    } catch (error) {
      expect(error).toBeInstanceOf(PapitaApiError);
      if (error instanceof PapitaApiError) {
        expect(error.status).toBe(404);
        expect(error.code).toBe("report_account_not_found");
      }
    }
  });
});
