import { afterEach, describe, expect, it, vi } from "vitest";

import { cancelMovement, createMovement, executeMovement, listMovements } from "@/api/movements";

describe("movements API helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("lists with status filter", async () => {
    const fetchMock = vi.fn<typeof fetch>(async () =>
      Response.json({ items: [], limit: 100, skip: 0, total: 0 }, { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await listMovements({ status: "pending", limit: 100 });

    const url = String(fetchMock.mock.calls[0]?.[0]);
    expect(url).toContain("/api/v1/movements?");
    expect(url).toContain("status=pending");
    expect(fetchMock.mock.calls[0]?.[1]).toEqual(
      expect.objectContaining({ credentials: "include", method: "GET" }),
    );
  });

  it("posts create and execute; deletes for cancel", async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(
        Response.json(
          {
            id: "44444444-4444-4444-4444-444444444444",
            amount: 50,
            currency: "USD",
            description: "Transfer",
            destination_account_id: "22222222-2222-2222-2222-222222222222",
            movement_date: "2026-08-01",
            source_account_id: "11111111-1111-1111-1111-111111111111",
            status: "pending",
          },
          { status: 201 },
        ),
      )
      .mockResolvedValueOnce(
        Response.json(
          {
            id: "44444444-4444-4444-4444-444444444444",
            status: "completed",
            executed_at: "2026-08-01T12:00:00Z",
          },
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }));

    vi.stubGlobal("fetch", fetchMock);

    await createMovement({
      source_account_id: "11111111-1111-1111-1111-111111111111",
      destination_account_id: "22222222-2222-2222-2222-222222222222",
      amount: 50,
      currency: "USD",
      description: "Transfer",
      movement_date: "2026-08-01",
      scheduled: true,
    });
    await executeMovement("44444444-4444-4444-4444-444444444444");
    await cancelMovement("44444444-4444-4444-4444-444444444444");

    expect(fetchMock.mock.calls[0]?.[1]).toEqual(
      expect.objectContaining({ method: "POST", credentials: "include" }),
    );
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain("/execute");
    expect(fetchMock.mock.calls[1]?.[1]).toEqual(expect.objectContaining({ method: "POST" }));
    expect(fetchMock.mock.calls[2]?.[1]).toEqual(expect.objectContaining({ method: "DELETE" }));
  });
});
