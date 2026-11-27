import { afterEach, describe, expect, it, vi } from "vitest";

import { bffLogin, getBffSession } from "@/api/auth";
import { clearAuthTokens, getAccessToken, isPapitaApiError, setAuthTokens } from "@/api/http";

function webStorageBlob(): string {
  return `${JSON.stringify(window.localStorage)}${JSON.stringify(window.sessionStorage)}`;
}

describe("Stateless Bearer auth storage posture (PPT-100 security)", () => {
  afterEach(() => {
    clearAuthTokens();
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("holds access token in memory only and never persists JWTs in WebStorage", async () => {
    const accessToken = "eyJhbGciOiJIUzI1NiJ9.e30.signature";
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async (input) => {
        const url = String(input);
        if (url.includes("/api/v1/auth/login")) {
          return Response.json(
            {
              access_token: accessToken,
              token_type: "bearer",
              expires_in: 3600,
              refresh_token: null,
            },
            { status: 200 },
          );
        }
        return Response.json(
          {
            id: "11111111-1111-1111-1111-111111111111",
            username: "owner",
            email: "owner@example.local",
            display_name: null,
            phone: null,
            provider_type: "email",
            auth_provider: "local",
            created_at: "2026-08-01T00:00:00Z",
          },
          { status: 200 },
        );
      }),
    );

    const session = await bffLogin({ email: "owner@example.local", password: "SecurePass1!" });

    expect(session.authenticated).toBe(true);
    expect(getAccessToken()).toBe(accessToken);
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    expect(webStorageBlob()).not.toContain(accessToken);
  });

  it("restores session via HttpOnly cookie probe on reload without WebStorage", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      Response.json(
        {
          id: "11111111-1111-1111-1111-111111111111",
          username: "owner",
          email: "owner@example.local",
          display_name: null,
          phone: null,
          provider_type: "email",
          auth_provider: "local",
          created_at: "2026-08-01T00:00:00Z",
        },
        { status: 200 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const session = await getBffSession();

    expect(session.authenticated).toBe(true);
    expect(session.session_backend).toBe("cookie");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/auth/me",
      expect.objectContaining({ credentials: "include" }),
    );
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });

  it("returns anonymous session when neither memory token nor HttpOnly cookie is present", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      Response.json({ detail: "Could not validate credentials" }, { status: 401 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const session = await getBffSession();

    expect(session.authenticated).toBe(false);
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
  });

  it("rethrows 429 rate-limit errors without clearing memory tokens or looping to login", async () => {
    setAuthTokens({ accessToken: "in-memory-token", expiresIn: 3600 });
    vi.stubGlobal(
      "fetch",
      vi.fn<typeof fetch>(async () =>
        Response.json(
          { detail: "API rate limit exceeded for your plan. Try again later." },
          { status: 429 },
        ),
      ),
    );

    let caught: unknown;
    try {
      await getBffSession();
    } catch (error) {
      caught = error;
    }

    expect(isPapitaApiError(caught)).toBe(true);
    expect((caught as { status: number }).status).toBe(429);
    expect(getAccessToken()).toBe("in-memory-token");
  });
});
