/** Parse display values without shifting calendar dates across timezones. */
function toDisplayDate(value: string | number | Date): Date | null {
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }
  if (typeof value === "number") {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  // Date-only API strings are calendar dates — parse as local Y/M/D, not UTC midnight.
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(trimmed);
  if (dateOnly) {
    const year = Number(dateOnly[1]);
    const month = Number(dateOnly[2]);
    const day = Number(dateOnly[3]);
    const local = new Date(year, month - 1, day);
    return Number.isNaN(local.getTime()) ? null : local;
  }
  const date = new Date(trimmed);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** Format a date for display (presentation only — no period math). */
export function formatDate(value: string | number | Date, locale?: string): string {
  const date = toDisplayDate(value);
  if (date === null) {
    return typeof value === "string" ? value : "";
  }
  try {
    return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(date);
  } catch {
    return date.toISOString().slice(0, 10);
  }
}

/** Format a date-time for display (presentation only). */
export function formatDateTime(value: string | number | Date, locale?: string): string {
  const date = toDisplayDate(value);
  if (date === null) {
    return typeof value === "string" ? value : "";
  }
  try {
    return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(
      date,
    );
  } catch {
    return date.toISOString();
  }
}
