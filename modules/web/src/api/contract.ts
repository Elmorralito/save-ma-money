import type { DiscoveryHeaders } from "@/api/headers";
import type { ClientContract } from "@/types/domain";

/** Default expected PPT-044 discovery id when `VITE_PAPITA_BREAKING_CHANGES_ID` is unset. */
export const DEFAULT_BREAKING_CHANGES_ID = "ppt-044";

export type BreakingChangesGuardStatus = "match" | "mismatch" | "unknown";

export type BreakingChangesGuardResult = {
  status: BreakingChangesGuardStatus;
  expected: string;
  observed: string | null;
};

/**
 * Resolve the SPA-expected breaking-changes id from public Vite env.
 *
 * Args:
 *   envValue: Optional override (defaults to `import.meta.env.VITE_PAPITA_BREAKING_CHANGES_ID`).
 *
 * Returns:
 *   Trimmed env value, or {@link DEFAULT_BREAKING_CHANGES_ID} when unset/empty.
 */
export function resolveExpectedBreakingChangesId(
  envValue: string | undefined = import.meta.env.VITE_PAPITA_BREAKING_CHANGES_ID,
): string {
  const trimmed = envValue?.trim();
  if (trimmed === undefined || trimmed === "") {
    return DEFAULT_BREAKING_CHANGES_ID;
  }
  return trimmed;
}

/**
 * Observed breaking-changes id from contract body (preferred) or discovery header.
 *
 * Returns:
 *   Non-empty id string, or `null` when neither source provides a value.
 */
export function observedBreakingChangesId(
  contract?: ClientContract | null,
  discovery?: DiscoveryHeaders | null,
): string | null {
  const fromBody = contract?.breaking_changes?.trim();
  if (fromBody !== undefined && fromBody !== "") {
    return fromBody;
  }
  const fromHeader = discovery?.breakingChanges?.trim();
  if (fromHeader !== undefined && fromHeader !== "") {
    return fromHeader;
  }
  return null;
}

/**
 * Compare expected SPA breaking-changes id against PPT-044 discovery signals.
 *
 * Prefer `contract.breaking_changes` over `X-Papita-Breaking-Changes`. When neither
 * is present, status is `unknown` (no banner — avoids false alarms when offline).
 */
export function evaluateBreakingChangesGuard(input: {
  contract?: ClientContract | null;
  discovery?: DiscoveryHeaders | null;
  expected?: string;
}): BreakingChangesGuardResult {
  const expected = input.expected ?? resolveExpectedBreakingChangesId();
  const observed = observedBreakingChangesId(input.contract, input.discovery);
  if (observed === null) {
    return { status: "unknown", expected, observed: null };
  }
  if (observed === expected) {
    return { status: "match", expected, observed };
  }
  return { status: "mismatch", expected, observed };
}

/** Bulk create cap from contract JSON body (preferred) or discovery headers. */
export function bulkMaxTransactions(
  contract: ClientContract | null | undefined,
  discovery?: DiscoveryHeaders | null,
): number | null {
  const fromBody = contract?.effective?.bulk_max_transactions;
  if (typeof fromBody === "number" && Number.isFinite(fromBody)) {
    return fromBody;
  }
  return discovery?.bulkMax ?? null;
}

/** Report window max days from contract JSON body or discovery headers. */
export function reportWindowMaxDays(
  contract: ClientContract | null | undefined,
  discovery?: DiscoveryHeaders | null,
): number | null {
  const fromBody = contract?.effective?.report_window_max_days;
  if (typeof fromBody === "number" && Number.isFinite(fromBody)) {
    return fromBody;
  }
  return discovery?.reportWindowMaxDays ?? null;
}

/** Foreign report `account_id` HTTP status (404 secure default; 400 when compat). */
export function reportsForeignAccountStatus(
  contract: ClientContract | null | undefined,
  discovery?: DiscoveryHeaders | null,
): number | null {
  const fromBody = contract?.effective?.reports_foreign_account_status;
  if (typeof fromBody === "number" && Number.isFinite(fromBody)) {
    return fromBody;
  }
  return discovery?.reportsForeignAccountStatus ?? null;
}
