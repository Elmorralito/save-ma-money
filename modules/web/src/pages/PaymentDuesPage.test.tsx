import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as accountsApi from "@/api/accounts";
import * as aiApi from "@/api/ai";
import * as categoriesApi from "@/api/categories";
import * as templatesApi from "@/api/transactionTemplates";
import * as transactionsApi from "@/api/transactions";
import { PaymentDuesPage } from "@/pages/PaymentDuesPage";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/ai", () => ({
  getAIStatus: vi.fn(),
  getAIConfig: vi.fn(),
  updateAIConfig: vi.fn(),
  fetchAIModels: vi.fn(),
  sendAIChat: vi.fn(),
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

vi.mock("@/api/transactionTemplates", () => ({
  listTransactionTemplates: vi.fn(),
  getTransactionTemplate: vi.fn(),
  createTransactionTemplate: vi.fn(),
  updateTransactionTemplate: vi.fn(),
  deleteTransactionTemplate: vi.fn(),
  markTemplatePaid: vi.fn(),
  clearTemplatePaid: vi.fn(),
}));

vi.mock("@/api/transactions", () => ({
  listTransactions: vi.fn(),
  getTransaction: vi.fn(),
  createTransaction: vi.fn(),
  updateTransaction: vi.fn(),
  deleteTransaction: vi.fn(),
  bulkCreateTransactions: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(aiApi.getAIConfig).mockResolvedValue({
    enabled: true,
    mode: "sidecar",
    default_connection: "cli:agy",
    model: null,
    base_url: null,
    include_financial_context_by_default: true,
    reports_ai_enabled: true,
    payment_dues_ai_enabled: true,
    cli_permission_granted: true,
    lan_permission_granted: true,
    api_permission_granted: true,
    has_api_key: false,
    api_key_hint: null,
  });
  vi.mocked(accountsApi.listAccounts).mockResolvedValue({
    items: [
      {
        id: "11111111-1111-1111-1111-111111111111",
        name: "Checking",
        account_kind: "checking",
        ledger_side: "asset",
        currency: "COP",
        fx_rate: 1,
        balance: 500000,
        is_active: true,
        include_in_balance: true,
      },
    ],
    limit: 100,
    skip: 0,
    total: 1,
  });
  vi.mocked(categoriesApi.listCategories).mockResolvedValue({
    items: [
      {
        id: "22222222-2222-2222-2222-222222222222",
        name: "Housing",
        category_type: "expense",
        is_active: true,
      },
    ],
    limit: 100,
    skip: 0,
    total: 1,
  });
  vi.mocked(transactionsApi.listTransactions).mockResolvedValue({
    items: [],
    limit: 100,
    skip: 0,
    total: 0,
  });
  vi.mocked(templatesApi.listTransactionTemplates).mockResolvedValue({
    items: [
      {
        id: "33333333-3333-3333-3333-333333333333",
        name: "Apartment Rent",
        description: "Monthly lease",
        planned_amount: 1500000,
        planned_day: 5,
        due_date: null,
        use_month_end: false,
        remind_days_before: 3,
        is_active: true,
        from_account_id: "11111111-1111-1111-1111-111111111111",
        category_id: "22222222-2222-2222-2222-222222222222",
        tags: [],
      },
      {
        id: "44444444-4444-4444-4444-444444444444",
        name: "Internet Bill",
        description: "Fiber",
        planned_amount: 120000,
        planned_day: 20,
        due_date: "2026-11-28",
        use_month_end: false,
        remind_days_before: 2,
        is_active: true,
        from_account_id: "11111111-1111-1111-1111-111111111111",
        category_id: "22222222-2222-2222-2222-222222222222",
        tags: [],
      },
    ],
    limit: 25,
    skip: 0,
    total: 2,
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("PaymentDuesPage", () => {
  it("renders dues list, filters search, and supports create dialog open", async () => {
    const user = userEvent.setup();

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <PaymentDuesPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Apartment Rent")).toBeInTheDocument();
    });
    expect(screen.getByText("Internet Bill")).toBeInTheDocument();

    const searchInput = screen.getByPlaceholderText("Filter by name or description");
    await user.type(searchInput, "Rent");
    expect(screen.getByText("Apartment Rent")).toBeInTheDocument();
    expect(screen.queryByText("Internet Bill")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^Clear$/i }));
    await waitFor(() => {
      expect(screen.getByText("Internet Bill")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "New payment due" }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    for (const closeBtn of screen.queryAllByRole("button", { name: /Cancel|Close/i })) {
      fireEvent.click(closeBtn);
    }
    for (const sel of screen.queryAllByRole("combobox")) {
      const opts = sel.querySelectorAll("option");
      const lastVal = opts[opts.length - 1]?.getAttribute("value");
      if (lastVal) fireEvent.change(sel, { target: { value: lastVal } });
    }
    for (const thBtn of document.querySelectorAll("thead button")) {
      fireEvent.click(thBtn);
    }
  }, 15_000);
});
