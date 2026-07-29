/**
 * Resolve the API base URL for browser calls.
 *
 * Empty / unset uses same-origin paths so the Vite `/api` proxy (dev) or
 * nginx `/api` reverse proxy (prod) handles routing. Set `VITE_API_BASE_URL`
 * only when calling the API cross-origin (then CORS `ALLOWED_ORIGINS` must
 * include the web origin).
 */
export function resolveApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim();
  if (configured === undefined || configured === "") {
    return "";
  }
  return configured.replace(/\/+$/, "");
}

/** Join base URL with an absolute API path (must start with `/`). */
export function buildApiUrl(path: string): string {
  if (!path.startsWith("/")) {
    throw new Error(`API path must be absolute (got ${path})`);
  }
  return `${resolveApiBaseUrl()}${path}`;
}
