import { buildApiUrl } from "@/api/config";
import { isPapitaApiError, papitaApiErrorFromResponse } from "@/api/errors";
import { parseDiscoveryHeaders, type DiscoveryHeaders } from "@/api/headers";

export type ApiFetchOptions = {
  method?: string;
  signal?: AbortSignal;
  headers?: HeadersInit;
  body?: BodyInit | null;
  /** Override default JSON Accept header. */
  accept?: string;
  /** Skip one-shot Bearer refresh + retry on 401 (auth endpoints). */
  skipAuthRefresh?: boolean;
};

export type ApiFetchResult<T> = {
  data: T;
  response: Response;
  discovery: DiscoveryHeaders;
};

type AuthRedirectHandler = () => void;

let accessToken: string | null = null;
let refreshToken: string | null = null;
let accessExpiresAt: number | null = null;
let onUnauthorized: AuthRedirectHandler | null = null;
let refreshInFlight: Promise<boolean> | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRefreshToken(): string | null {
  return refreshToken;
}

export function getAccessExpiresAt(): number | null {
  return accessExpiresAt;
}

export function setAuthTokens(input: {
  accessToken: string;
  refreshToken?: string | null;
  expiresIn?: number | null;
}): void {
  accessToken = input.accessToken;
  if (input.refreshToken !== undefined) {
    refreshToken = input.refreshToken;
  }
  const ttl = typeof input.expiresIn === "number" && input.expiresIn > 0 ? input.expiresIn : 3600;
  accessExpiresAt = Math.floor(Date.now() / 1000) + ttl;
}

export function clearAuthTokens(): void {
  accessToken = null;
  refreshToken = null;
  accessExpiresAt = null;
}

/** Register SPA navigation when Bearer refresh cannot restore the session. */
export function setUnauthorizedHandler(handler: AuthRedirectHandler | null): void {
  onUnauthorized = handler;
}

async function tryTokenRefresh(): Promise<boolean> {
  if (!refreshToken) {
    return false;
  }
  if (refreshInFlight) {
    return refreshInFlight;
  }
  refreshInFlight = (async () => {
    try {
      const response = await fetch(buildApiUrl("/api/v1/auth/refresh"), {
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) {
        clearAuthTokens();
        return false;
      }
      const body = (await response.json()) as {
        access_token?: string;
        refresh_token?: string | null;
        expires_in?: number | null;
      };
      if (typeof body.access_token === "string" && body.access_token.length > 0) {
        setAuthTokens({
          accessToken: body.access_token,
          refreshToken: body.refresh_token ?? refreshToken,
          expiresIn: body.expires_in ?? 3600,
        });
        return true;
      }
      clearAuthTokens();
      return false;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

/**
 * Thin Fetch wrapper for papita_txnsapi (Stateless Bearer JWT — PPT-100).
 */
export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<ApiFetchResult<T>> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", options.accept ?? "application/json");
  }
  if (accessToken && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const execute = async (): Promise<Response> => {
    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }
    return fetch(buildApiUrl(path), {
      method,
      signal: options.signal,
      credentials: "include",
      headers,
      body: options.body,
    });
  };

  let response = await execute();

  if (response.status === 401 && !options.skipAuthRefresh) {
    const refreshed = await tryTokenRefresh();
    if (refreshed) {
      response = await execute();
    } else {
      clearAuthTokens();
      onUnauthorized?.();
    }
  }

  if (!response.ok) {
    const error = await papitaApiErrorFromResponse(response);
    if (error.status === 401 && !options.skipAuthRefresh) {
      clearAuthTokens();
      onUnauthorized?.();
    }
    throw error;
  }

  const discovery = parseDiscoveryHeaders(response.headers);
  const contentType = response.headers.get("content-type") ?? "";
  if (response.status === 204 || contentType === "") {
    return { data: undefined as T, response, discovery };
  }

  if (contentType.includes("application/json")) {
    const data = (await response.json()) as T;
    return { data, response, discovery };
  }

  const text = (await response.text()) as T;
  return { data: text, response, discovery };
}

export { isPapitaApiError };
