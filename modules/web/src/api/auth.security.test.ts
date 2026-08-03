import { afterEach, describe, expect, it, vi } from "vitest";

import { bffLogin, getBffSession } from "@/api/auth";
import { clearCsrfToken, getCsrfToken } from "@/api/csrf";

function webStorageBlob(): string {
  return `${JSON.stringify(window.localStorage)}${JSON.stringify(window.sessionStorage)}`;
}

describe("BFF auth storage posture (PPT-056 security)", () => {
  afterEach(() => {
    clearCsrfToken();
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("does not persist JWTs or access tokens in WebStorage after login", async () => {
    const accessToken = "eyJhbGciOiJIUzI1NiJ9.e30.signature";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        Response.json(
          {
            authenticated: true,
            user: {
              id: "11111111-1111-1111-1111-111111111111",
              username: "owner",
              email: "owner@example.local",
              display_name: null,
              phone: null,
              provider: "local",
              auth_provider: "local",
              created_at: "2026-08-01T00:00:00Z",
            },
            csrf_token: "csrf-from-login",
            session_backend: "memory",
            // Deliberately include a token-shaped field — SPA must ignore persistence.
            access_token: accessToken,
          },
          { status: 200 },
        ),
      ),
    );

    const session = await bffLogin({ email: "owner@example.local", password: "SecurePass1!" });

    expect(session.authenticated).toBe(true);
    expect(getCsrfToken()).toBe("csrf-from-login");
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    const storageBlob = webStorageBlob();
    expect(storageBlob).not.toContain(accessToken);
    expect(storageBlob).not.toContain("csrf-from-login");
  });

  it("bootstrap session uses credentials include and leaves storage empty when anonymous", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      Response.json(
        {
          authenticated: false,
          user: null,
          csrf_token: null,
          session_backend: null,
        },
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const session = await getBffSession();

    expect(session.authenticated).toBe(false);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/bff/auth/session",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });
});
