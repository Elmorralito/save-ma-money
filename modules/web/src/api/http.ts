import { buildApiUrl } from "@/api/config";
import { papitaApiErrorFromResponse } from "@/api/errors";
import { parseDiscoveryHeaders, type DiscoveryHeaders } from "@/api/headers";

export type ApiFetchOptions = {
  method?: string;
  signal?: AbortSignal;
  headers?: HeadersInit;
  body?: BodyInit | null;
  /** Override default JSON Accept header. */
  accept?: string;
};

export type ApiFetchResult<T> = {
  data: T;
  response: Response;
  discovery: DiscoveryHeaders;
};

/**
 * Thin Fetch wrapper for papita_txnsapi / BFF.
 *
 * - Uses same-origin `/api/...` by default (Vite proxy / nginx).
 * - Always sends `credentials: 'include'` for future BFF cookie sessions (#115).
 * - Does **not** attach `Authorization` — JWTs stay server-side after BFF lands.
 */
export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<ApiFetchResult<T>> {
  const headers = new Headers(options.headers);
  if (!headers.has("Accept")) {
    headers.set("Accept", options.accept ?? "application/json");
  }

  const response = await fetch(buildApiUrl(path), {
    method: options.method ?? "GET",
    signal: options.signal,
    credentials: "include",
    headers,
    body: options.body,
  });

  if (!response.ok) {
    throw await papitaApiErrorFromResponse(response);
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
