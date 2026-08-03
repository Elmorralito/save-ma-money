/** Format a currency amount for display (presentation only — no ledger math). */
export function formatMoney(balance: number, currency: string): string {
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(balance);
  } catch {
    return `${balance.toFixed(2)} ${currency}`;
  }
}
