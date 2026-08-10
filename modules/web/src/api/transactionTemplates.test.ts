import { afterEach, describe, expect, it, vi } from "vitest";

import {
  listTransactionTemplates,
  listUpcomingDues,
  markTemplatePaid,
} from "@/api/transactionTemplates";

describe("transactionTemplates API helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("lists templates with query filters and credentials include", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      Response.json({ items: [], limit: 100, skip: 0, total: 0 }, { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await listTransactionTemplates({
      category_id: "11111111-1111-1111-1111-111111111111",
      is_active: true,
      limit: 100,
      skip: 0,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/transaction-templates?"),
      expect.objectContaining({ credentials: "include", method: "GET" }),
    );
    const url = String(fetchMock.mock.calls[0]?.[0]);
    expect(url).toContain("category_id=11111111-1111-1111-1111-111111111111");
    expect(url).toContain("is_active=true");
    expect(url).toContain("limit=100");
  });

  it("lists upcoming dues with window params", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      Response.json({ items: [], as_of: "2026-08-10", window_days: 14 }, { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await listUpcomingDues({ window_days: 14, include_paid: false });

    const url = String(fetchMock.mock.calls[0]?.[0]);
    expect(url).toContain("/api/v1/transaction-templates/upcoming-dues?");
    expect(url).toContain("window_days=14");
    expect(url).toContain("include_paid=false");
  });

  it("posts mark-paid with JSON body", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      Response.json(
        {
          id: "22222222-2222-2222-2222-222222222222",
          amount: 50,
          currency: "USD",
          description: "Rent",
          status: "completed",
          transaction_date: "2026-08-01",
          transaction_type: "expense",
          is_recurring: false,
        },
        { status: 201 },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await markTemplatePaid("33333333-3333-3333-3333-333333333333", { amount: 50 });

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain(
      "/api/v1/transaction-templates/33333333-3333-3333-3333-333333333333/mark-paid",
    );
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ amount: 50 });
  });
});
