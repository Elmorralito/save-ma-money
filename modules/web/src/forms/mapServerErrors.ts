import { isPapitaApiError } from "@/api/errors";

export type MappedFieldError = {
  /** RHF field name (after fieldMap), or a top-level form key. */
  name: string;
  message: string;
};

export type MappedServerErrors = {
  fields: MappedFieldError[];
  /** Unmapped / form-level message. */
  root: string | null;
};

type FastApiDetailItem = {
  loc?: unknown;
  msg?: unknown;
};

function isDetailItem(value: unknown): value is FastApiDetailItem {
  return value !== null && typeof value === "object";
}

/** Strip body/query/path prefixes from FastAPI ``loc`` and join remaining segments. */
export function apiLocToPath(loc: unknown): string | null {
  if (!Array.isArray(loc) || loc.length === 0) {
    return null;
  }
  const parts = loc
    .filter(
      (segment): segment is string | number =>
        typeof segment === "string" || typeof segment === "number",
    )
    .map(String);
  if (parts.length === 0) {
    return null;
  }
  const first = parts[0];
  const start = first === "body" || first === "query" || first === "path" ? 1 : 0;
  const rest = parts.slice(start);
  if (rest.length === 0) {
    return null;
  }
  return rest.join(".");
}

function resolveFormFieldName(apiPath: string, fieldMap: Record<string, string>): string | null {
  if (fieldMap[apiPath]) {
    return fieldMap[apiPath];
  }
  // Top-level OpenAPI body keys match flat form state when unmapped.
  if (!apiPath.includes(".")) {
    return apiPath;
  }
  return null;
}

/**
 * Map a failed API error into RHF field paths.
 *
 * ``fieldMap`` remaps OpenAPI body paths (e.g. ``banking_details.entity``) onto flat form keys.
 * Unmapped nested locs contribute to ``root``.
 */
export function mapServerErrors(
  error: unknown,
  fieldMap: Record<string, string> = {},
): MappedServerErrors {
  if (!isPapitaApiError(error)) {
    return { fields: [], root: null };
  }

  const fields: MappedFieldError[] = [];
  const unmapped: string[] = [];

  if (error.body !== null && typeof error.body === "object") {
    const detail = (error.body as { detail?: unknown }).detail;
    if (Array.isArray(detail)) {
      for (const item of detail) {
        if (!isDetailItem(item)) {
          continue;
        }
        const msg = typeof item.msg === "string" ? item.msg : null;
        if (msg === null) {
          continue;
        }
        const apiPath = apiLocToPath(item.loc);
        if (apiPath === null) {
          unmapped.push(msg);
          continue;
        }
        const target = resolveFormFieldName(apiPath, fieldMap);
        if (target) {
          fields.push({ name: target, message: msg });
        } else {
          unmapped.push(`${apiPath}: ${msg}`);
        }
      }
    }
  }

  let root: string | null = null;
  if (fields.length === 0) {
    if (unmapped.length > 0) {
      root = unmapped.join("; ");
    } else if (error.code) {
      root = `${error.message} [${error.code}]`;
    } else {
      root = error.message;
    }
  } else if (unmapped.length > 0) {
    root = unmapped.join("; ");
  }

  return { fields, root };
}

/** True when the error should surface primarily as a toast (429 / network / 5xx). */
export function shouldToastMutationError(error: unknown): boolean {
  if (error instanceof TypeError) {
    return true;
  }
  if (!isPapitaApiError(error)) {
    return true;
  }
  if (error.status === 429 || error.status >= 500) {
    return true;
  }
  // Field-mapped 422 stays inline-only; other statuses toast.
  return error.status !== 422;
}
