import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as accountsApi from "@/api/accounts";
import * as movementsApi from "@/api/movements";
import { MovementsPage } from "@/pages/MovementsPage";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/movements", () => ({
  listMovements: vi.fn(),
  getMovement: vi.fn(),
  createMovement: vi.fn(),
  updateMovement: vi.fn(),
  cancelMovement: vi.fn(),
  executeMovement: vi.fn(),
}));

vi.mock("@/api/accounts", () => ({
  listAccounts: vi.fn(),
  getAccount: vi.fn(),
  createAccount: vi.fn(),
  updateAccount: vi.fn(),
  deleteAccount: vi.fn(),
}));

function mockAccounts() {
  vi.mocked(accountsApi.listAccounts).mockResolvedValue({
    items: [
      {
        id: "11111111-1111-1111-1111-111111111111",
        name: "Checking",
        account_kind: "checking",
        ledger_side: "asset",
        currency: "USD",
        balance: 200,
        is_active: true,
      },
      {
        id: "22222222-2222-2222-2222-222222222222",
        name: "Savings",
        account_kind: "savings",
        ledger_side: "asset",
        currency: "USD",
        balance: 50,
        is_active: true,
      },
    ],
    limit: 100,
    skip: 0,
    total: 2,
  });
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("MovementsPage", () => {
  it("renders pending movements with execute and cancel actions", async () => {
    mockAccounts();
    vi.mocked(movementsApi.listMovements).mockResolvedValue({
      items: [
        {
          id: "44444444-4444-4444-4444-444444444444",
          source_account_id: "11111111-1111-1111-1111-111111111111",
          source_account_name: "Checking",
          destination_account_id: "22222222-2222-2222-2222-222222222222",
          destination_account_name: "Savings",
          amount: 25,
          currency: "USD",
          description: "Move cash",
          movement_date: "2026-08-01",
          status: "pending",
        },
      ],
      limit: 100,
      skip: 0,
      total: 1,
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <MovementsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Move cash")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Execute" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  it("hides execute/cancel for completed movements", async () => {
    mockAccounts();
    vi.mocked(movementsApi.listMovements).mockResolvedValue({
      items: [
        {
          id: "44444444-4444-4444-4444-444444444444",
          source_account_id: "11111111-1111-1111-1111-111111111111",
          destination_account_id: "22222222-2222-2222-2222-222222222222",
          amount: 25,
          currency: "USD",
          description: "Done transfer",
          movement_date: "2026-08-01",
          status: "completed",
        },
      ],
      limit: 100,
      skip: 0,
      total: 1,
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <MovementsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Done transfer")).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: "Execute" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });

  it("executes a pending movement", async () => {
    mockAccounts();
    const user = userEvent.setup();
    vi.mocked(movementsApi.listMovements)
      .mockResolvedValueOnce({
        items: [
          {
            id: "44444444-4444-4444-4444-444444444444",
            source_account_id: "11111111-1111-1111-1111-111111111111",
            destination_account_id: "22222222-2222-2222-2222-222222222222",
            amount: 25,
            currency: "USD",
            description: "Pending move",
            movement_date: "2026-08-01",
            status: "pending",
          },
        ],
        limit: 100,
        skip: 0,
        total: 1,
      })
      .mockResolvedValueOnce({
        items: [
          {
            id: "44444444-4444-4444-4444-444444444444",
            source_account_id: "11111111-1111-1111-1111-111111111111",
            destination_account_id: "22222222-2222-2222-2222-222222222222",
            amount: 25,
            currency: "USD",
            description: "Pending move",
            movement_date: "2026-08-01",
            status: "completed",
          },
        ],
        limit: 100,
        skip: 0,
        total: 1,
      });
    vi.mocked(movementsApi.executeMovement).mockResolvedValue({
      id: "44444444-4444-4444-4444-444444444444",
      status: "completed",
      executed_at: "2026-08-01T12:00:00Z",
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <MovementsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Execute" })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Execute" }));

    await waitFor(() => {
      expect(movementsApi.executeMovement).toHaveBeenCalledWith(
        "44444444-4444-4444-4444-444444444444",
      );
    });
  });

  it("creates a movement through the dialog", async () => {
    mockAccounts();
    const user = userEvent.setup();
    vi.mocked(movementsApi.listMovements)
      .mockResolvedValueOnce({ items: [], limit: 100, skip: 0, total: 0 })
      .mockResolvedValueOnce({
        items: [
          {
            id: "44444444-4444-4444-4444-444444444444",
            source_account_id: "11111111-1111-1111-1111-111111111111",
            destination_account_id: "22222222-2222-2222-2222-222222222222",
            amount: 15,
            currency: "USD",
            description: "New transfer",
            movement_date: "2026-08-01",
            status: "completed",
          },
        ],
        limit: 100,
        skip: 0,
        total: 1,
      });
    vi.mocked(movementsApi.createMovement).mockResolvedValue({
      id: "44444444-4444-4444-4444-444444444444",
      source_account_id: "11111111-1111-1111-1111-111111111111",
      destination_account_id: "22222222-2222-2222-2222-222222222222",
      amount: 15,
      currency: "USD",
      description: "New transfer",
      movement_date: "2026-08-01",
      status: "completed",
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <MovementsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("No movements yet")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "New movement" }));
    const dialog = await screen.findByRole("dialog");
    await user.selectOptions(within(dialog).getByLabelText("Source account"), [
      "11111111-1111-1111-1111-111111111111",
    ]);
    await user.selectOptions(within(dialog).getByLabelText("Destination account"), [
      "22222222-2222-2222-2222-222222222222",
    ]);
    await user.clear(within(dialog).getByLabelText("Amount"));
    await user.type(within(dialog).getByLabelText("Amount"), "15");
    await user.clear(within(dialog).getByLabelText("Description"));
    await user.type(within(dialog).getByLabelText("Description"), "New transfer");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(movementsApi.createMovement).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText("New transfer")).toBeInTheDocument();
    });
  });
});
