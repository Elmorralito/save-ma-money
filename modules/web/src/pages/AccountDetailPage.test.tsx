import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as accountsApi from "@/api/accounts";
import { AccountDetailPage } from "@/pages/AccountDetailPage";
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

const accountId = "11111111-1111-1111-1111-111111111111";

describe("AccountDetailPage", () => {
  it("loads account detail and soft-deletes via the API", async () => {
    const user = userEvent.setup();
    vi.mocked(accountsApi.getAccount).mockResolvedValue({
      id: accountId,
      name: "Checking",
      account_kind: "checking",
      ledger_side: "asset",
      currency: "USD",
      balance: 10,
      is_active: true,
      banking_details: { entity: "Bank", account_number: null },
    });
    vi.mocked(accountsApi.deleteAccount).mockResolvedValue(undefined);

    render(
      <QueryTestProvider>
        <MemoryRouter initialEntries={[`/accounts/${accountId}`]}>
          <Routes>
            <Route path="/accounts/:accountId" element={<AccountDetailPage />} />
            <Route path="/accounts" element={<h1>Accounts</h1>} />
          </Routes>
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Checking" })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Delete" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(accountsApi.deleteAccount).toHaveBeenCalledWith(accountId);
    });
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Accounts" })).toBeInTheDocument();
    });
  });
});
