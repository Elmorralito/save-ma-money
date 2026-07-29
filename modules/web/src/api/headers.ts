/**
 * PPT-044 discovery / error header names (mirror papita_txnsapi.core.client_contract).
 */

export const HEADER_BREAKING_CHANGES = "X-Papita-Breaking-Changes";
export const HEADER_BULK_MAX = "X-Papita-Bulk-Max";
export const HEADER_REPORT_WINDOW_MAX_DAYS = "X-Papita-Report-Window-Max-Days";
export const HEADER_REFRESH_BALANCES_DEFAULT = "X-Papita-Cash-Flow-Refresh-Default";
export const HEADER_REPORTS_FOREIGN_ACCOUNT_STATUS = "X-Papita-Reports-Foreign-Account-Status";
export const HEADER_ERROR_CODE = "X-Papita-Error-Code";
export const HEADER_COMPAT_ACTIVE = "X-Papita-Compat-Active";

/** Parsed discovery headers from an `/api/v1` response. */
export type DiscoveryHeaders = {
  breakingChanges: string | null;
  bulkMax: number | null;
  reportWindowMaxDays: number | null;
  cashFlowRefreshDefault: boolean | null;
  reportsForeignAccountStatus: number | null;
  errorCode: string | null;
  compatActive: string[];
};

function headerGet(headers: Headers, name: string): string | null {
  return headers.get(name);
}

function parseIntHeader(value: string | null): number | null {
  if (value === null || value.trim() === "") {
    return null;
  }
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : null;
}

function parseBoolHeader(value: string | null): boolean | null {
  if (value === null) {
    return null;
  }
  const normalized = value.trim().toLowerCase();
  if (normalized === "true") {
    return true;
  }
  if (normalized === "false") {
    return false;
  }
  return null;
}

/** Extract PPT-044 discovery headers from a Fetch `Headers` object. */
export function parseDiscoveryHeaders(headers: Headers): DiscoveryHeaders {
  const compatRaw = headerGet(headers, HEADER_COMPAT_ACTIVE);
  return {
    breakingChanges: headerGet(headers, HEADER_BREAKING_CHANGES),
    bulkMax: parseIntHeader(headerGet(headers, HEADER_BULK_MAX)),
    reportWindowMaxDays: parseIntHeader(headerGet(headers, HEADER_REPORT_WINDOW_MAX_DAYS)),
    cashFlowRefreshDefault: parseBoolHeader(headerGet(headers, HEADER_REFRESH_BALANCES_DEFAULT)),
    reportsForeignAccountStatus: parseIntHeader(
      headerGet(headers, HEADER_REPORTS_FOREIGN_ACCOUNT_STATUS),
    ),
    errorCode: headerGet(headers, HEADER_ERROR_CODE),
    compatActive:
      compatRaw === null || compatRaw.trim() === ""
        ? []
        : compatRaw
            .split(",")
            .map((part) => part.trim())
            .filter((part) => part.length > 0),
  };
}
