/** True when the bulk row count exceeds the effective API bulk max. */
export function isBulkOverCap(rowCount: number, bulkMax: number): boolean {
  return rowCount > bulkMax;
}
