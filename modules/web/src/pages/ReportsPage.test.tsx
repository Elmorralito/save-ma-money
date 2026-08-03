import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as accountsApi from "@/api/accounts";
import { PapitaApiError } from "@/api/errors";
import * as metaApi from "@/api/meta";
import * as reportsApi from "@/api/reports";
import { ReportsPage } from "@/pages/ReportsPage";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/accounts", () => ({
  listAccounts: vi.fn(),
  getAccount: vi.fn(),
  createAccount: vi.fn(),
  updateAccount: vi.fn(),
  deleteAccount: vi.fn(),
}));

vi.mock("@/api/reports", () => ({
  getSpendingReport: vi.fn(),
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

const sampleContract = {
  breaking_changes: "ppt-044",
  api_version: "1.0.0",
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
    bulk_max_transactions: 100,
    report_window_max_days: 90,
    docs_enabled: true,
  },
  compat: { active: [], sunset: null, flags: {} },
  error_codes: {},
  migration: {
    probe: "GET /api/v1/meta/client-contract",
    prefer_headers: [],
    client_checklist: [],
  },
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function mockHappyPath(): void {
  vi.mocked(metaApi.getClientContract).mockResolvedValue({
    contract: sampleContract,
    discovery: {
      ...emptyDiscovery,
      reportWindowMaxDays: 90,
      reportsForeignAccountStatus: 404,
    },
  });
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
  vi.mocked(reportsApi.getSpendingReport).mockResolvedValue({
    period: { start_date: "2026-01-01", end_date: "2026-01-31" },
    total_spending: 50,
    total_income: 120,
    net_savings: 70,
    group_by: "category",
    breakdown: [{ category: "food", amount: 50, percentage: 100, transaction_count: 0 }],
    trend: [],
  });
}

describe("ReportsPage", () => {
  it("loads spending totals from the API on mount", async () => {
    mockHappyPath();

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <ReportsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Total spending")).toBeInTheDocument();
    });
    expect(screen.getAllByText(/\$50\.00/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("food")).toBeInTheDocument();
    expect(screen.getByText(/\$120\.00/)).toBeInTheDocument();
    expect(reportsApi.getSpendingReport).toHaveBeenCalled();
  });

  it("blocks Run report when the draft window exceeds the contract max", async () => {
    mockHappyPath();

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <ReportsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Start date")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Start date"), { target: { value: "2024-01-01" } });
    fireEvent.change(screen.getByLabelText("End date"), { target: { value: "2026-01-01" } });

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/at most 90 days/i);
    });
    expect(screen.getByRole("button", { name: "Run report" })).toBeDisabled();
  });

  it("surfaces report_account_not_found with a clear message", async () => {
    mockHappyPath();
    vi.mocked(reportsApi.getSpendingReport).mockRejectedValue(
      new PapitaApiError({
        message: "Account not found",
        status: 404,
        code: "report_account_not_found",
        discovery: { ...emptyDiscovery, errorCode: "report_account_not_found" },
      }),
    );

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <ReportsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("report_account_not_found");
    });
    expect(screen.getByRole("alert")).toHaveTextContent(/not found for your tenant/i);
  });
});
