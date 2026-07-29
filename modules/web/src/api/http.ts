import { buildApiUrl } from "@/api/config";
import { getCsrfToken, setCsrfToken } from "@/api/csrf";
import { isPapitaApiError, papitaApiErrorFromResponse } from "@/api/errors";
import { parseDiscoveryHeaders, type DiscoveryHeaders } from "@/api/headers";

export type ApiFetchOptions = {
  method?: string;
  signal?: AbortSignal;
  headers?: HeadersInit;
  body?: BodyInit | null;
  /** Override default JSON Accept header. */
  accept?: string;
  /** Skip one-shot BFF refresh + retry on 401 (auth endpoints). */
  skipAuthRefresh?: boolean;
};

export type ApiFetchResult<T> = {
  data: T;
  response: Response;
  discovery: DiscoveryHeaders;
};

const CSRF_HEADER = "X-Papita-CSRF";
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

type AuthRedirectHandler = () => void;

let onUnauthorized: AuthRedirectHandler | null = null;
let refreshInFlight: Promise<boolean> | null = null;

/** Register SPA navigation when BFF refresh cannot restore the session. */
export function setUnauthorizedHandler(handler: AuthRedirectHandler | null): void {
  onUnauthorized = handler;
}

async function tryBffRefresh(): Promise<boolean> {
  if (refreshInFlight) {
    return refreshInFlight;
  }
  refreshInFlight = (async () => {
    try {
      const response = await fetch(buildApiUrl("/api/v1/bff/auth/refresh"), {
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
          ...(getCsrfToken() ? { [CSRF_HEADER]: getCsrfToken() as string } : {}),
        },
      });
      if (!response.ok) {
        return false;
      }
      const body = (await response.json()) as { csrf_token?: string | null };
      if (typeof body.csrf_token === "string" && body.csrf_token.length > 0) {
        setCsrfToken(body.csrf_token);
      }
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

/**
 * Thin Fetch wrapper for papita_txnsapi / BFF.
 *
 * - Uses same-origin `/api/...` by default (Vite proxy / nginx).
 * - Always sends `credentials: 'include'` for BFF cookie sessions (#115).
 * - Attaches `X-Papita-CSRF` on unsafe methods when a CSRF token is known.
 * - Does **not** attach `Authorization` — JWTs stay server-side.
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
  if (UNSAFE_METHODS.has(method) && !headers.has(CSRF_HEADER)) {
    const csrf = getCsrfToken();
    if (csrf) {
      headers.set(CSRF_HEADER, csrf);
    }
  }

  const execute = async (): Promise<Response> =>
    fetch(buildApiUrl(path), {
      method,
      signal: options.signal,
      credentials: "include",
      headers,
      body: options.body,
    });

  let response = await execute();

  if (response.status === 401 && !options.skipAuthRefresh) {
    const refreshed = await tryBffRefresh();
    if (refreshed) {
      response = await execute();
    } else {
      onUnauthorized?.();
    }
  }

  if (!response.ok) {
    const error = await papitaApiErrorFromResponse(response);
    if (error.status === 401 && !options.skipAuthRefresh) {
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

/** Re-export for callers that branch on auth failures. */
export { isPapitaApiError };
