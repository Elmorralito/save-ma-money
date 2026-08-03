import { afterEach, describe, expect, it, vi } from "vitest";

import { IDEMPOTENCY_KEY_HEADER } from "@/api/idempotency";
import { bulkCreateTransactions, createTransaction, listTransactions } from "@/api/transactions";

describe("transactions API helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("lists with query filters and credentials include", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      Response.json({ items: [], limit: 100, skip: 0, total: 0 }, { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await listTransactions({
      account_id: "11111111-1111-1111-1111-111111111111",
      transaction_type: "expense",
      limit: 100,
      skip: 0,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/transactions?"),
      expect.objectContaining({ credentials: "include", method: "GET" }),
    );
    const url = String(fetchMock.mock.calls[0]?.[0]);
    expect(url).toContain("account_id=11111111-1111-1111-1111-111111111111");
    expect(url).toContain("transaction_type=expense");
    expect(url).toContain("limit=100");
  });

  it("sends Idempotency-Key on create", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      Response.json(
        {
          id: "22222222-2222-2222-2222-222222222222",
          amount: 10,
          currency: "USD",
          description: "Coffee",
          status: "completed",
          transaction_date: "2026-08-01",
          transaction_type: "expense",
          is_recurring: false,
        },
        { status: 201 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await createTransaction(
      {
        account_id: "11111111-1111-1111-1111-111111111111",
        category_id: "33333333-3333-3333-3333-333333333333",
        amount: 10,
        currency: "USD",
        description: "Coffee",
        transaction_date: "2026-08-01",
        transaction_type: "expense",
      },
      { idempotencyKey: "test-key-1" },
    );

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(headers.get(IDEMPOTENCY_KEY_HEADER)).toBe("test-key-1");
    expect(init.method).toBe("POST");
  });

  it("sends Idempotency-Key on bulk create", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      Response.json({ created: 1, failed: 0, transactions: [] }, { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await bulkCreateTransactions(
      {
        transactions: [
          {
            account_id: "11111111-1111-1111-1111-111111111111",
            category_id: "33333333-3333-3333-3333-333333333333",
            amount: 5,
            currency: "USD",
            description: "A",
            transaction_date: "2026-08-01",
            transaction_type: "income",
          },
        ],
      },
      { idempotencyKey: "bulk-key-1" },
    );

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("/api/v1/transactions/bulk");
    expect(headers.get(IDEMPOTENCY_KEY_HEADER)).toBe("bulk-key-1");
  });
});
