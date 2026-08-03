import { parseDiscoveryHeaders, type DiscoveryHeaders } from "@/api/headers";

/** Structured client error for papita_txnsapi responses (no domain rules). */
export class PapitaApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly discovery: DiscoveryHeaders;
  readonly body: unknown;
  /** Seconds from ``Retry-After`` when present (typically on HTTP 429). */
  readonly retryAfter: number | null;

  constructor(options: {
    message: string;
    status: number;
    code?: string | null;
    discovery: DiscoveryHeaders;
    body?: unknown;
    retryAfter?: number | null;
  }) {
    super(options.message);
    this.name = "PapitaApiError";
    this.status = options.status;
    this.code = options.code ?? options.discovery.errorCode;
    this.discovery = options.discovery;
    this.body = options.body;
    this.retryAfter = options.retryAfter ?? null;
  }
}

/** True when `error` is a {@link PapitaApiError}. */
export function isPapitaApiError(error: unknown): error is PapitaApiError {
  return error instanceof PapitaApiError;
}

/** HTTP status is a client error (do not retry in TanStack Query). */
export function isClientHttpError(error: unknown): boolean {
  return isPapitaApiError(error) && error.status >= 400 && error.status < 500;
}

function extractErrorMessage(body: unknown, fallback: string): string {
  if (typeof body === "string" && body.trim() !== "") {
    return body;
  }
  if (body !== null && typeof body === "object") {
    const record = body as Record<string, unknown>;
    const detail = record["detail"];
    if (typeof detail === "string" && detail.trim() !== "") {
      return detail;
    }
    if (Array.isArray(detail) && detail.length > 0) {
      return "Request validation failed";
    }
    const message = record["message"];
    if (typeof message === "string" && message.trim() !== "") {
      return message;
    }
  }
  return fallback;
}

function parseRetryAfterSeconds(headers: Headers): number | null {
  const raw = headers.get("Retry-After");
  if (raw === null || raw.trim() === "") {
    return null;
  }
  const asInt = Number.parseInt(raw, 10);
  if (Number.isFinite(asInt) && asInt >= 0) {
    return asInt;
  }
  const asDate = Date.parse(raw);
  if (Number.isFinite(asDate)) {
    const seconds = Math.ceil((asDate - Date.now()) / 1000);
    return seconds > 0 ? seconds : 0;
  }
  return null;
}

/** Build a {@link PapitaApiError} from a failed Fetch response. */
export async function papitaApiErrorFromResponse(response: Response): Promise<PapitaApiError> {
  const discovery = parseDiscoveryHeaders(response.headers);
  const retryAfter = parseRetryAfterSeconds(response.headers);
  let body: unknown;
  const contentType = response.headers.get("content-type") ?? "";
  try {
    if (contentType.includes("application/json")) {
      body = await response.json();
    } else {
      const text = await response.text();
      body = text === "" ? undefined : text;
    }
  } catch {
    body = undefined;
  }

  return new PapitaApiError({
    message: extractErrorMessage(body, `HTTP ${String(response.status)}`),
    status: response.status,
    code: discovery.errorCode,
    discovery,
    body,
    retryAfter,
  });
}
