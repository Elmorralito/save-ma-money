import type { DiscoveryHeaders } from "@/api/headers";
import type { ClientContract } from "@/types/domain";

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
