import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as authApi from "@/api/auth";
import * as accountsApi from "@/api/accounts";
import * as ingestionApi from "@/api/ingestion";
import * as reportsApi from "@/api/reports";
import * as transactionsApi from "@/api/transactions";
import * as templatesApi from "@/api/transactionTemplates";
import { RequireAuth } from "@/auth/RequireAuth";
import { AppLayout } from "@/components/layout/AppLayout";
import { PublicLayout } from "@/components/layout/PublicLayout";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/auth", () => ({
  getBffSession: vi.fn(),
  bffLogin: vi.fn(),
  bffLogout: vi.fn(),
  bffRegister: vi.fn(),
  bffRefresh: vi.fn(),
  bffResendConfirmation: vi.fn(),
}));

vi.mock("@/api/accounts", () => ({
  listAccounts: vi.fn(),
  getAccount: vi.fn(),
  createAccount: vi.fn(),
  updateAccount: vi.fn(),
  deleteAccount: vi.fn(),
}));

vi.mock("@/api/transactions", () => ({
  listTransactions: vi.fn(),
  getTransaction: vi.fn(),
  createTransaction: vi.fn(),
  updateTransaction: vi.fn(),
  deleteTransaction: vi.fn(),
  executeTransaction: vi.fn(),
  bulkCreateTransactions: vi.fn(),
}));

vi.mock("@/api/transactionTemplates", () => ({
  listTransactionTemplates: vi.fn(),
  listUpcomingDues: vi.fn(),
  getTransactionTemplate: vi.fn(),
  createTransactionTemplate: vi.fn(),
  updateTransactionTemplate: vi.fn(),
  deleteTransactionTemplate: vi.fn(),
  markTemplatePaid: vi.fn(),
  clearTemplatePaid: vi.fn(),
}));

vi.mock("@/api/reports", () => ({
  getFinancialHealthReport: vi.fn(),
  getOperatingCashflowReport: vi.fn(),
  getDebtPaydownReport: vi.fn(),
  getPlannedVsActualReport: vi.fn(),
  getSpendingReport: vi.fn(),
  simulateDebtPaydown: vi.fn(),
}));

vi.mock("@/api/ingestion", () => ({
  getLatestIngestionRun: vi.fn(),
  listIngestionRuns: vi.fn(),
  listIngestionConnections: vi.fn(),
}));

vi.mock("@/api/health", () => ({
  getHealth: vi.fn(async () => ({
    status: "healthy",
    version: "0.0.0-test",
    timestamp: "2026-07-29T00:00:00Z",
    database: "connected",
    auth: "skipped",
    auth_detail: "auth provider is local — supabase probe skipped",
    redis: "skipped",
    redis_detail: "redis disabled",
  })),
  getHealthLive: vi.fn(async () => ({ status: "ok" })),
}));

vi.mock("@/api/meta", () => ({
  getClientContract: vi.fn(async () => ({
    contract: {
      breaking_changes: "ppt-044",
      api_version: "0.0.0-test",
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
        report_window_max_days: 366,
        docs_enabled: true,
      },
      compat: { active: [], sunset: null, flags: {} },
      error_codes: {},
      migration: {
        probe: "GET /api/v1/meta/client-contract",
        prefer_headers: [],
        client_checklist: [],
      },
    },
    discovery: {
      breakingChanges: "ppt-044",
      bulkMax: 100,
      reportWindowMaxDays: 366,
      cashFlowRefreshDefault: false,
      reportsForeignAccountStatus: 404,
      errorCode: null,
      compatActive: [],
    },
  })),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  vi.mocked(authApi.getBffSession).mockResolvedValue({
    authenticated: false,
    user: null,
    csrf_token: null,
    session_backend: "memory",
    access_expires_at: null,
  });
});

describe("auth routing", () => {
  it("redirects unauthenticated users from /dashboard to /login", async () => {
    render(
      <QueryTestProvider>
        <MemoryRouter initialEntries={["/dashboard"]}>
          <Routes>
            <Route element={<PublicLayout />}>
              <Route path="/login" element={<LoginPage />} />
            </Route>
            <Route
              element={
                <RequireAuth>
                  <AppLayout />
                </RequireAuth>
              }
            >
              <Route path="/dashboard" element={<DashboardPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1, name: "Sign in" })).toBeInTheDocument();
    });
  });

  it("renders the login page", () => {
    render(
      <QueryTestProvider>
        <MemoryRouter initialEntries={["/login"]}>
          <Routes>
            <Route element={<PublicLayout />}>
              <Route path="/login" element={<LoginPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryTestProvider>,
    );
    expect(screen.getByRole("heading", { level: 1, name: "Sign in" })).toBeInTheDocument();
  });
});

describe("DashboardPage (authenticated)", () => {
  it("renders welcome, session TTL, accounts, due soon, and pending transfers", async () => {
    const expiresAt = Math.floor(Date.now() / 1000) + 3600;
    vi.mocked(authApi.getBffSession).mockResolvedValue({
      authenticated: true,
      user: {
        id: "00000000-0000-0000-0000-000000000001",
        username: "tester",
        email: "tester@example.com",
        display_name: null,
        phone: null,
        provider: "email",
        auth_provider: "local",
        created_at: "2026-07-29T00:00:00Z",
      },
      csrf_token: "csrf-test",
      session_backend: "memory",
      access_expires_at: expiresAt,
    });
    vi.mocked(accountsApi.listAccounts).mockResolvedValue({
      items: [
        {
          id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
          name: "Checking",
          currency: "USD",
          fx_rate: 1,
          balance: 1200,
          account_kind: "bank_account",
          ledger_side: "asset",
          is_active: true,
          include_in_balance: true,
        },
      ],
      total: 1,
      skip: 0,
      limit: 5,
    });
    vi.mocked(transactionsApi.listTransactions).mockResolvedValue({
      items: [
        {
          id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
          amount: 50,
          currency: "USD",
          description: "Rent hold",
          transaction_date: "2026-08-01",
          movement_date: "2026-08-01",
          transaction_type: "transfer",
          source_account_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
          destination_account_id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
          source_account_name: "Checking",
          destination_account_name: "Landlord",
          status: "pending",
          settlement_status: "in_transit",
          is_recurring: false,
        },
      ],
      total: 1,
      skip: 0,
      limit: 5,
    });
    vi.mocked(reportsApi.getFinancialHealthReport).mockResolvedValue({
      currency: "USD",
      available_currencies: ["USD"],
      multi_currency_warning: false,
      scorecard: {
        total_assets: 100000,
        total_liabilities: 25000,
        reconciled_net_worth: 75000,
        liquid_cash_total: 15000,
        baseline_monthly_burn: 3000,
        liquid_runway_months: 5,
        target_liquidity_months: 4,
        monthly_debt_service: 1200,
        total_monthly_interest_drag: 200,
        debt_to_asset_ratio_pct: 25,
        margin_ltv_pct: 20,
        included_asset_count: 2,
        included_liability_count: 1,
        excluded_account_count: 0,
      },
    });
    vi.mocked(reportsApi.getOperatingCashflowReport).mockResolvedValue({
      period: { start_date: "2026-08-01", end_date: "2026-08-31" },
      currency: "USD",
      available_currencies: ["USD"],
      multi_currency_warning: false,
      waterfall: {
        income_fixed: 4000,
        income_variable: 500,
        total_external_income: 4500,
        loans: 1200,
        fixed_expenses: 1500,
        variable_expenses: 600,
        unexpected_expenses: 0,
        total_operating_outflows: 3300,
        operating_free_cashflow: 1200,
        savings: 500,
        capital_deployments: 0,
        net_allocated_surplus: 700,
        net_ledger_cashflow: 700,
        non_operating_inflows: 0,
        internal_sweeps_volume: 0,
        debt_service_to_income_pct: 26.7,
        organic_fcf_margin_pct: 26.7,
        status_tone: "positive",
      },
      buckets: [],
      monthly_series: [],
      diagnostics: {
        unbucketed_category_count: 0,
        unbucketed_amount: 0,
        cashflow_only_cc_excluded_count: 0,
        cashflow_only_cc_excluded_amount: 0,
      },
      in_transit: { count: 1, inflows: 0, outflows: 0, total_volume: 50 },
    });
    vi.mocked(ingestionApi.getLatestIngestionRun).mockResolvedValue({
      id: "ffffffff-ffff-ffff-ffff-ffffffffffff",
      connection_id: null,
      status: "succeeded",
      started_at: "2026-08-10T10:00:00Z",
      finished_at: "2026-08-10T10:01:00Z",
      fetched: 12,
      created: 4,
      updated: 1,
      reactivated: 0,
      failed: 0,
      dead_lettered: 0,
      acknowledged: 12,
      dry_run_skipped: 0,
      error_summary: null,
      flow_name: "email-sync",
      deployment_name: "prod",
    });
    vi.mocked(templatesApi.listUpcomingDues).mockResolvedValue({
      as_of: "2026-08-10",
      window_days: 14,
      items: [
        {
          due_date: "2026-08-15",
          remind_start: "2026-08-12",
          is_paid: false,
          paid_transaction_id: null,
          template: {
            id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
            name: "Electric bill",
            description: "",
            tags: [],
            category_id: "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee",
            planned_amount: 90,
            planned_day: 15,
            use_month_end: false,
            due_date: null,
            remind_days_before: 3,
            from_account_id: null,
            is_active: true,
          },
        },
      ],
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 1, name: /Welcome back, tester/i }),
      ).toBeInTheDocument();
    });
    expect(screen.getByTestId("session-ttl")).toHaveTextContent(/Time left to live:/i);
    expect(screen.getByRole("region", { name: "Accounts" })).toHaveTextContent("Checking");
    expect(screen.getByRole("region", { name: "Pending transfers" })).toHaveTextContent(
      "Rent hold",
    );
    expect(screen.getByRole("region", { name: "Due soon" })).toHaveTextContent("Electric bill");
    expect(screen.getByRole("region", { name: "Quick links" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Balances and account details/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Bills and payment deadlines/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /View spending report/i })).toBeInTheDocument();
  });
});
