import { describe, expect, it } from "vitest";

import { IDEMPOTENCY_KEY_HEADER, newIdempotencyKey } from "@/api/idempotency";

describe("idempotency helper", () => {
  it("exports the API header name and UUID keys", () => {
    expect(IDEMPOTENCY_KEY_HEADER).toBe("Idempotency-Key");
    const key = newIdempotencyKey();
    expect(key).toMatch(
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
    );
  });
});
