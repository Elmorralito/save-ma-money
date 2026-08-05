/**
 * Presentation labels for API slug enums (account kinds, sides, types, statuses).
 * Maps known slugs; otherwise title-cases underscore-separated tokens.
 */
const KNOWN_SLUG_LABELS: Record<string, string> = {
  checking: "Checking",
  savings: "Savings",
  cash: "Cash",
  investment_brokerage: "Investment brokerage",
  real_estate: "Real estate",
  credit_card: "Credit card",
  loan_mortgage: "Loan / mortgage",
  other_asset: "Other asset",
  other_liability: "Other liability",
  asset: "Asset",
  liability: "Liability",
  income: "Income",
  expense: "Expense",
  pending: "Pending",
  completed: "Completed",
  cancelled: "Cancelled",
  canceled: "Cancelled",
  posted: "Posted",
  failed: "Failed",
};

export function formatSlugLabel(slug: string | null | undefined): string {
  if (slug == null) {
    return "";
  }
  const trimmed = slug.trim();
  if (!trimmed) {
    return "";
  }
  const known = KNOWN_SLUG_LABELS[trimmed.toLowerCase()];
  if (known) {
    return known;
  }
  return trimmed
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}
