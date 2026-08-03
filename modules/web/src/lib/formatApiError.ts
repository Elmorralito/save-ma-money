import { isPapitaApiError } from "@/api/errors";

/**
 * User-facing message from a failed API call (422 / X-Papita-Error-Code aware).
 *
 * Does not interpret domain rules — only surfaces server ``detail`` and discovery codes.
 */
export function formatApiError(error: unknown, fallback = "Request failed"): string {
  if (!isPapitaApiError(error)) {
    if (error instanceof TypeError) {
      return "Cannot reach the API. Start it with `make api-all`, then retry.";
    }
    return error instanceof Error ? error.message : fallback;
  }

  if (error.status === 502 || error.status === 503 || error.status === 504) {
    return "API is unreachable (proxy error). Is `make api-all` (or `make api-up`) running on :8000?";
  }

  if (error.status === 429) {
    const detail = error.message.trim();
    if (detail.length > 0 && detail.toLowerCase() !== "http 429") {
      return detail;
    }
    return "Too many requests. Wait a moment and try again.";
  }

  let message = error.message;
  if (error.body !== null && typeof error.body === "object") {
    const detail = (error.body as { detail?: unknown }).detail;
    if (Array.isArray(detail) && detail.length > 0) {
      const parts = detail
        .map((item) => {
          if (item !== null && typeof item === "object" && "msg" in item) {
            const msg = (item as { msg?: unknown }).msg;
            const loc = (item as { loc?: unknown }).loc;
            const path =
              Array.isArray(loc) && loc.length > 0
                ? loc
                    .filter((segment) => typeof segment === "string" || typeof segment === "number")
                    .join(".")
                : null;
            if (typeof msg === "string") {
              return path ? `${path}: ${msg}` : msg;
            }
          }
          return null;
        })
        .filter((part): part is string => part !== null);
      if (parts.length > 0) {
        message = parts.join("; ");
      }
    }
  }

  if (error.code) {
    return `${message} [${error.code}]`;
  }
  return message;
}

/**
 * Global seed category mutations return HTTP 404 with ``Category not found`` (G7 / FR-15).
 * Wire responses do not expose ``owner_id``, so this is the client-side signal.
 */
export function isGlobalOrMissingCategoryError(error: unknown): boolean {
  return (
    isPapitaApiError(error) &&
    error.status === 404 &&
    (error.message === "Category not found" ||
      error.message.toLowerCase().includes("category not found"))
  );
}
