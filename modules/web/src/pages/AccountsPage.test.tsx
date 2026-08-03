import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as accountsApi from "@/api/accounts";
import { AccountsPage } from "@/pages/AccountsPage";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/accounts", () => ({
  listAccounts: vi.fn(),
  getAccount: vi.fn(),
  createAccount: vi.fn(),
  updateAccount: vi.fn(),
  deleteAccount: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("AccountsPage", () => {
  it("renders loading then account rows from the API", async () => {
    vi.mocked(accountsApi.listAccounts).mockResolvedValue({
      items: [
        {
          id: "11111111-1111-1111-1111-111111111111",
          name: "Checking",
          account_kind: "checking",
          ledger_side: "asset",
          currency: "USD",
          balance: 42.5,
          is_active: true,
        },
      ],
      limit: 100,
      skip: 0,
      total: 1,
    });

    render(
      <QueryTestProvider>
        <MemoryRouter initialEntries={["/accounts"]}>
          <Routes>
            <Route path="/accounts" element={<AccountsPage />} />
          </Routes>
        </MemoryRouter>
      </QueryTestProvider>,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Loading");

    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Checking" })).toBeInTheDocument();
    });
    expect(screen.getByText("checking")).toBeInTheDocument();
    expect(screen.getByText(/\$42\.50/)).toBeInTheDocument();
  });

  it("shows empty state when the API returns no items", async () => {
    vi.mocked(accountsApi.listAccounts).mockResolvedValue({
      items: [],
      limit: 100,
      skip: 0,
      total: 0,
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <AccountsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("No accounts yet")).toBeInTheDocument();
    });
  });

  it("surfaces API errors with retry", async () => {
    const user = userEvent.setup();
    vi.mocked(accountsApi.listAccounts)
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce({ items: [], limit: 100, skip: 0, total: 0 });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <AccountsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("boom");
    });

    await user.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => {
      expect(screen.getByText("No accounts yet")).toBeInTheDocument();
    });
  });

  it("creates an account through the dialog and refreshes the list", async () => {
    const user = userEvent.setup();
    vi.mocked(accountsApi.listAccounts)
      .mockResolvedValueOnce({ items: [], limit: 100, skip: 0, total: 0 })
      .mockResolvedValueOnce({
        items: [
          {
            id: "11111111-1111-1111-1111-111111111111",
            name: "Everyday",
            account_kind: "checking",
            ledger_side: "asset",
            currency: "USD",
            balance: 100,
            is_active: true,
          },
        ],
        limit: 100,
        skip: 0,
        total: 1,
      });
    vi.mocked(accountsApi.createAccount).mockResolvedValue({
      id: "11111111-1111-1111-1111-111111111111",
      name: "Everyday",
      account_kind: "checking",
      ledger_side: "asset",
      currency: "USD",
      balance: 100,
      is_active: true,
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <AccountsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("No accounts yet")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "New account" }));
    await user.type(screen.getByLabelText("Name"), "Everyday");
    await user.type(screen.getByLabelText("Entity"), "Local Bank");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(accountsApi.createAccount).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Everyday" })).toBeInTheDocument();
    });
  });
});
