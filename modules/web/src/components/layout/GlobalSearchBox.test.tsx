import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GlobalSearchBox } from "@/components/layout/GlobalSearchBox";
import * as globalSearchLib from "@/lib/globalSearch";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/lib/globalSearch", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/globalSearch")>();
  return {
    ...actual,
    fetchGlobalSearch: vi.fn(),
  };
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function ControlledSearch({ onPick }: { onPick: (hit: globalSearchLib.GlobalSearchHit) => void }) {
  const [val, setVal] = useState("");
  return (
    <GlobalSearchBox label="Global search" value={val} onValueChange={setVal} onPick={onPick} />
  );
}

describe("GlobalSearchBox", () => {
  it("debounces query, renders hits, and invokes onPick cleanly", async () => {
    const onPick = vi.fn();
    vi.mocked(globalSearchLib.fetchGlobalSearch).mockResolvedValue({
      q: "rent",
      kinds: ["payment_due"],
      account_id: null,
      limit: 10,
      items: [
        {
          kind: "payment_due",
          id: "due-1",
          title: "Apartment Rent",
          subtitle: "Monthly · day 5",
          occurred_at: "2026-11-05T00:00:00Z",
          status: "recurring",
          amount: 1500000,
          currency: "COP",
          account_id: null,
          flags: [],
        },
      ],
    });

    vi.spyOn(HTMLElement.prototype, "getClientRects").mockReturnValue([
      new DOMRect(0, 0, 100, 30),
    ] as unknown as DOMRectList);

    render(
      <QueryTestProvider>
        <ControlledSearch onPick={onPick} />
      </QueryTestProvider>,
    );

    const input = screen.getByRole("combobox", { name: "Global search" });
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "rent" } });

    await waitFor(
      () => {
        expect(screen.getByText("Apartment Rent")).toBeInTheDocument();
      },
      { timeout: 2000 },
    );

    fireEvent.keyDown(input, { key: "ArrowDown" });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onPick).toHaveBeenCalledWith(expect.objectContaining({ id: "due-1" }));
  });
});
