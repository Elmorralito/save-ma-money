/**
 * Client-side report date-window checks (PPT-054 / PPT-044).
 *
 * Mirrors ``papita_txnsapi.schemas.query_params._validate_report_window``:
 * ``(end - start).days > max_days`` is rejected. Does not reimplement report
 * aggregation — only presentation-side preflight against client-contract limits.
 */

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

export type ReportWindowOk = {
  ok: true;
  startDate: string;
  endDate: string;
  /** Delta days matching Python ``(end - start).days``. */
  spanDays: number;
};

export type ReportWindowError = {
  ok: false;
  reason: "invalid_date" | "inverted" | "too_large";
  message: string;
};

export type ReportWindowResult = ReportWindowOk | ReportWindowError;

/** Parse ``YYYY-MM-DD`` as a UTC calendar date (stable day deltas). */
export function parseIsoDate(value: string): Date | null {
  const match = ISO_DATE.exec(value.trim());
  if (!match) {
    return null;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) {
    return null;
  }
  if (month < 1 || month > 12 || day < 1 || day > 31) {
    return null;
  }
  const parsed = new Date(Date.UTC(year, month - 1, day));
  if (
    parsed.getUTCFullYear() !== year ||
    parsed.getUTCMonth() !== month - 1 ||
    parsed.getUTCDate() !== day
  ) {
    return null;
  }
  return parsed;
}

/** Format a ``Date`` as local ``YYYY-MM-DD`` for ``<input type="date">``. */
export function toIsoDateLocal(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/** Default ~30-day window ending today (local calendar). */
export function defaultReportWindowDates(): { startDate: string; endDate: string } {
  const end = new Date();
  const start = new Date(end);
  start.setDate(start.getDate() - 29);
  return { startDate: toIsoDateLocal(start), endDate: toIsoDateLocal(end) };
}

/**
 * Validate a report window against an optional client-contract max.
 *
 * When ``maxDays`` is ``null``/``undefined``, only date parse + order are checked
 * (server still enforces the real limit).
 */
export function validateReportWindow(
  startDate: string,
  endDate: string,
  maxDays: number | null | undefined,
): ReportWindowResult {
  const start = parseIsoDate(startDate);
  const end = parseIsoDate(endDate);
  if (start === null || end === null) {
    return {
      ok: false,
      reason: "invalid_date",
      message: "Start and end dates must be valid YYYY-MM-DD values.",
    };
  }

  const spanDays = Math.round((end.getTime() - start.getTime()) / 86_400_000);
  if (spanDays < 0) {
    return {
      ok: false,
      reason: "inverted",
      message: "Start date must be on or before end date.",
    };
  }

  if (typeof maxDays === "number" && Number.isFinite(maxDays) && spanDays > maxDays) {
    return {
      ok: false,
      reason: "too_large",
      message: `Report window must be at most ${String(maxDays)} days.`,
    };
  }

  return {
    ok: true,
    startDate: startDate.trim(),
    endDate: endDate.trim(),
    spanDays,
  };
}
