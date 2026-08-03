/** Header name for FastAPI transaction create/bulk idempotency (PPT-053). */
export const IDEMPOTENCY_KEY_HEADER = "Idempotency-Key";

/**
 * Generate a fresh Idempotency-Key value.
 *
 * Always send on create/bulk; the API bypasses replay when Redis is unavailable.
 */
export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}
