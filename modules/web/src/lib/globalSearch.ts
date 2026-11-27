import { apiFetch } from "@/api/http";

export type GlobalSearchKind =
  "account" | "transaction" | "payment_due" | "category" | "projection";

export type GlobalSearchHit = {
  kind: GlobalSearchKind;
  id: string;
  title: string;
  subtitle: string;
  occurred_at: string | null;
  status: string | null;
  amount: number | null;
  currency: string | null;
  account_id: string | null;
  flags: string[];
};

export type GlobalSearchResponse = {
  q: string;
  kinds: GlobalSearchKind[];
  account_id: string | null;
  limit: number;
  items: GlobalSearchHit[];
};

/** Where a hit navigates when opened. */
export function hitHref(hit: GlobalSearchHit): string {
  switch (hit.kind) {
    case "account":
      return `/accounts/${encodeURIComponent(hit.id)}`;
    case "transaction":
      return `/transactions?search=${encodeURIComponent(hit.title)}`;
    case "payment_due":
      return "/payment-dues";
    case "category":
      return `/categories?search=${encodeURIComponent(hit.title)}`;
    case "projection":
      return "/projections";
    default:
      return "/dashboard";
  }
}

export const KIND_LABEL: Record<GlobalSearchKind, string> = {
  account: "Account",
  transaction: "Transaction",
  payment_due: "Payment due",
  category: "Category",
  projection: "Projection",
};

export const KIND_BADGE: Record<GlobalSearchKind, string> = {
  account: "bg-emerald-500/12 text-emerald-700 border-emerald-500/25 dark:text-emerald-300",
  transaction: "bg-sky-500/12 text-sky-700 border-sky-500/25 dark:text-sky-300",
  payment_due: "bg-violet-500/12 text-violet-700 border-violet-500/25 dark:text-violet-300",
  category: "bg-amber-500/12 text-amber-700 border-amber-500/25 dark:text-amber-300",
  projection: "bg-indigo-500/12 text-indigo-700 border-indigo-500/25 dark:text-indigo-300",
};

export type FetchGlobalSearchParams = {
  q: string;
  kinds?: GlobalSearchKind[];
  accountId?: string | null;
  limit?: number;
  signal?: AbortSignal;
};

export async function fetchGlobalSearch({
  q,
  kinds,
  accountId,
  limit = 20,
  signal,
}: FetchGlobalSearchParams): Promise<GlobalSearchResponse> {
  const qs = new URLSearchParams();
  qs.set("q", q);
  qs.set("limit", String(limit));
  if (accountId) qs.set("account_id", accountId);
  for (const k of kinds ?? []) {
    qs.append("kinds", k);
  }
  const { data } = await apiFetch<GlobalSearchResponse>(`/api/v1/search?${qs.toString()}`, {
    method: "GET",
    signal,
  });
  return data;
}
