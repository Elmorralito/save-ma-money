import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as accountsApi from "@/api/accounts";
import { PapitaApiError } from "@/api/errors";
import * as categoriesApi from "@/api/categories";
import * as metaApi from "@/api/meta";
import * as transactionsApi from "@/api/transactions";
import { TransactionsPage } from "@/pages/TransactionsPage";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/transactions", () => ({
  listTransactions: vi.fn(),
  getTransaction: vi.fn(),
  createTransaction: vi.fn(),
  updateTransaction: vi.fn(),
  deleteTransaction: vi.fn(),
  bulkCreateTransactions: vi.fn(),
}));

vi.mock("@/api/accounts", () => ({
  listAccounts: vi.fn(),
  getAccount: vi.fn(),
  createAccount: vi.fn(),
  updateAccount: vi.fn(),
  deleteAccount: vi.fn(),
}));

vi.mock("@/api/categories", () => ({
  listCategories: vi.fn(),
  getCategory: vi.fn(),
  createCategory: vi.fn(),
  updateCategory: vi.fn(),
  deleteCategory: vi.fn(),
}));

vi.mock("@/api/meta", () => ({
  getClientContract: vi.fn(),
}));

const emptyDiscovery = {
  breakingChanges: null,
  bulkMax: null,
  reportWindowMaxDays: null,
  cashFlowRefreshDefault: null,
  reportsForeignAccountStatus: null,
  errorCode: null,
  compatActive: [] as string[],
};

function mockPickers() {
  vi.mocked(accountsApi.listAccounts).mockResolvedValue({
    items: [
      {
        id: "11111111-1111-1111-1111-111111111111",
        name: "Checking",
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
  vi.mocked(categoriesApi.listCategories).mockResolvedValue({
    items: [
      {
        id: "33333333-3333-3333-3333-333333333333",
        name: "Food",
        category_type: "expense",
        is_active: true,
      },
    ],
    limit: 100,
    skip: 0,
    total: 1,
  });
  vi.mocked(metaApi.getClientContract).mockResolvedValue({
    contract: {
      breaking_changes: "ppt-044",
      api_version: "v1",
      secure_defaults: {
        reports_foreign_account_status: 404,
        cash_flow_refresh_balances_default: false,
        bulk_max_transactions: 100,
        report_window_max_days: 366,
        docs_require_debug_or_docs_enabled: true,
        cors_wildcard_forbidden_when_not_debug: true,
      },
      effective: {
        reports_foreign_account_status: 404,
        cash_flow_refresh_balances_default: false,
        bulk_max_transactions: 2,
        report_window_max_days: 366,
        docs_enabled: true,
      },
      compat: { active: [], sunset: null, flags: {} },
      error_codes: { bulk_too_large: "bulk exceeds max" },
      migration: {
        probe: "/api/v1/meta/client-contract",
        prefer_headers: [],
        client_checklist: [],
      },
    },
    discovery: emptyDiscovery,
  });
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("TransactionsPage", () => {
  it("renders loading then transaction rows", async () => {
    mockPickers();
    vi.mocked(transactionsApi.listTransactions).mockResolvedValue({
      items: [
        {
          id: "22222222-2222-2222-2222-222222222222",
          account_id: "11111111-1111-1111-1111-111111111111",
          account_name: "Checking",
          category_id: "33333333-3333-3333-3333-333333333333",
          category_name: "Food",
          amount: 12.5,
          currency: "USD",
          description: "Lunch",
          status: "completed",
          transaction_date: "2026-08-01",
          transaction_type: "expense",
          is_recurring: false,
        },
      ],
      limit: 100,
      skip: 0,
      total: 1,
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <TransactionsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    expect(screen.getByRole("status")).toHaveTextContent("Loading");

    await waitFor(() => {
      expect(screen.getByText("Lunch")).toBeInTheDocument();
    });
    expect(screen.getAllByText("Expense").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/\$12\.50/)).toBeInTheDocument();
  });

  it("shows empty state when the API returns no items", async () => {
    mockPickers();
    vi.mocked(transactionsApi.listTransactions).mockResolvedValue({
      items: [],
      limit: 100,
      skip: 0,
      total: 0,
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <TransactionsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("No transactions yet")).toBeInTheDocument();
    });
  });

  it("surfaces API errors with retry", async () => {
    mockPickers();
    const user = userEvent.setup();
    vi.mocked(transactionsApi.listTransactions)
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce({ items: [], limit: 100, skip: 0, total: 0 });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <TransactionsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("boom");
    });

    await user.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => {
      expect(screen.getByText("No transactions yet")).toBeInTheDocument();
    });
  });

  it("creates a transaction through the dialog", async () => {
    mockPickers();
    const user = userEvent.setup();
    vi.mocked(transactionsApi.listTransactions)
      .mockResolvedValueOnce({ items: [], limit: 100, skip: 0, total: 0 })
      .mockResolvedValueOnce({
        items: [
          {
            id: "22222222-2222-2222-2222-222222222222",
            account_id: "11111111-1111-1111-1111-111111111111",
            account_name: "Checking",
            category_id: "33333333-3333-3333-3333-333333333333",
            category_name: "Food",
            amount: 9,
            currency: "USD",
            description: "Coffee",
            status: "completed",
            transaction_date: "2026-08-01",
            transaction_type: "expense",
            is_recurring: false,
          },
        ],
        limit: 100,
        skip: 0,
        total: 1,
      });
    vi.mocked(transactionsApi.createTransaction).mockResolvedValue({
      id: "22222222-2222-2222-2222-222222222222",
      account_id: "11111111-1111-1111-1111-111111111111",
      category_id: "33333333-3333-3333-3333-333333333333",
      amount: 9,
      currency: "USD",
      description: "Coffee",
      status: "completed",
      transaction_date: "2026-08-01",
      transaction_type: "expense",
      is_recurring: false,
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <TransactionsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("No transactions yet")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "New transaction" }));
    const dialog = await screen.findByRole("dialog");
    await user.selectOptions(within(dialog).getByLabelText("Account"), [
      "11111111-1111-1111-1111-111111111111",
    ]);
    await user.selectOptions(within(dialog).getByLabelText("Category"), [
      "33333333-3333-3333-3333-333333333333",
    ]);
    await user.clear(within(dialog).getByLabelText("Amount"));
    await user.type(within(dialog).getByLabelText("Amount"), "9");
    await user.clear(within(dialog).getByLabelText("Description"));
    await user.type(within(dialog).getByLabelText("Description"), "Coffee");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(transactionsApi.createTransaction).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText("Coffee")).toBeInTheDocument();
    });
  });

  it("surfaces bulk_too_large from the bulk dialog", async () => {
    mockPickers();
    const user = userEvent.setup();
    vi.mocked(transactionsApi.listTransactions).mockResolvedValue({
      items: [],
      limit: 100,
      skip: 0,
      total: 0,
    });
    vi.mocked(transactionsApi.bulkCreateTransactions).mockRejectedValue(
      new PapitaApiError({
        message: "Bulk create exceeds max",
        status: 422,
        code: "bulk_too_large",
        discovery: { ...emptyDiscovery, errorCode: "bulk_too_large", bulkMax: 2 },
      }),
    );

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <TransactionsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("No transactions yet")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Bulk create" }));
    const dialog = await screen.findByRole("dialog");
    await user.selectOptions(within(dialog).getByLabelText("Account"), [
      "11111111-1111-1111-1111-111111111111",
    ]);
    await user.selectOptions(within(dialog).getByLabelText("Category"), [
      "33333333-3333-3333-3333-333333333333",
    ]);
    await user.clear(within(dialog).getByLabelText("Amount"));
    await user.type(within(dialog).getByLabelText("Amount"), "5");
    await user.click(within(dialog).getByRole("button", { name: "Bulk create" }));

    await waitFor(() => {
      expect(within(dialog).getByRole("alert")).toHaveTextContent(/bulk_too_large/);
    });
  });
});
