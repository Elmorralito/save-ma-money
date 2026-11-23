import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as accountsApi from "@/api/accounts";
import * as authApi from "@/api/auth";
import * as ingestionApi from "@/api/ingestion";
import * as reportsApi from "@/api/reports";
import * as transactionsApi from "@/api/transactions";
import * as templatesApi from "@/api/transactionTemplates";
import { DashboardPage } from "@/pages/DashboardPage";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/auth", () => ({
  getBffSession: vi.fn(),
}));
vi.mock("@/api/accounts", () => ({
  listAccounts: vi.fn(),
}));
vi.mock("@/api/transactions", () => ({
  listTransactions: vi.fn(),
}));
vi.mock("@/api/transactionTemplates", () => ({
  listUpcomingDues: vi.fn(),
  markTemplatePaid: vi.fn(),
}));
vi.mock("@/api/reports", () => ({
  getFinancialHealthReport: vi.fn(),
  getOperatingCashflowReport: vi.fn(),
}));
vi.mock("@/api/ingestion", () => ({
  getLatestIngestionRun: vi.fn(),
}));

describe("DashboardPage (PPT-088 Automation-first Home)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(authApi.getBffSession).mockResolvedValue({
      authenticated: true,
      user: {
        id: "00000000-0000-0000-0000-000000000001",
        username: "papita",
        email: "papita@example.com",
        display_name: "Papita Owner",
        phone: null,
        provider: "email",
        auth_provider: "local",
        created_at: "2026-07-29T00:00:00Z",
      },
      csrf_token: "csrf-test",
      session_backend: "memory",
      access_expires_at: Math.floor(Date.now() / 1000) + 3600,
    });
    vi.mocked(accountsApi.listAccounts).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 5,
    });
    vi.mocked(templatesApi.listUpcomingDues).mockResolvedValue({
      as_of: "2026-11-23",
      window_days: 14,
      items: [],
    });
  });

  afterEach(() => {
    cleanup();
  });

  it("renders Financial Health Scorecard and Live Pulse from API responses", async () => {
    vi.mocked(reportsApi.getFinancialHealthReport).mockResolvedValue({
      currency: "USD",
      available_currencies: ["USD"],
      multi_currency_warning: false,
      scorecard: {
        total_assets: 112000,
        total_liabilities: 30000,
        reconciled_net_worth: 82000,
        liquid_cash_total: 12000,
        baseline_monthly_burn: 3000,
        liquid_runway_months: 4.0,
        target_liquidity_months: 4.0,
        monthly_debt_service: 1500,
        total_monthly_interest_drag: 250,
        debt_to_asset_ratio_pct: 26.8,
        margin_ltv_pct: 30.0,
        included_asset_count: 2,
        included_liability_count: 1,
        excluded_account_count: 0,
      },
    });
    vi.mocked(reportsApi.getOperatingCashflowReport).mockResolvedValue({
      period: { start_date: "2026-11-01", end_date: "2026-11-30" },
      currency: "USD",
      available_currencies: ["USD"],
      multi_currency_warning: false,
      waterfall: {
        income_fixed: 5000,
        income_variable: 0,
        total_external_income: 5000,
        loans: 1500,
        fixed_expenses: 1800,
        variable_expenses: 500,
        unexpected_expenses: 0,
        total_operating_outflows: 3800,
        operating_free_cashflow: 1200,
        savings: 400,
        capital_deployments: 0,
        net_allocated_surplus: 800,
        net_ledger_cashflow: 800,
        non_operating_inflows: 0,
        internal_sweeps_volume: 0,
        debt_service_to_income_pct: 30.0,
        organic_fcf_margin_pct: 24.0,
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
      in_transit: { count: 1, inflows: 0, outflows: 0, total_volume: 1250 },
    });
    vi.mocked(ingestionApi.getLatestIngestionRun).mockResolvedValue({
      id: "11111111-1111-1111-1111-111111111111",
      connection_id: null,
      status: "succeeded",
      started_at: "2026-11-23T10:00:00Z",
      finished_at: "2026-11-23T10:01:00Z",
      fetched: 18,
      created: 6,
      updated: 2,
      reactivated: 0,
      failed: 0,
      dead_lettered: 0,
      acknowledged: 18,
      dry_run_skipped: 0,
      error_summary: null,
      flow_name: "imap-bank-sync",
      deployment_name: "prod",
    });
    vi.mocked(transactionsApi.listTransactions).mockImplementation(async (params) => {
      if (params?.settlement_status === "in_transit") {
        return {
          items: [
            {
              id: "22222222-2222-2222-2222-222222222222",
              amount: 1250,
              currency: "USD",
              description: "Cross-border wire",
              transaction_date: "2026-11-22",
              movement_date: "2026-11-22",
              transaction_type: "transfer",
              source_account_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
              destination_account_id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
              source_account_name: "US Checking",
              destination_account_name: "COP Savings",
              status: "completed",
              settlement_status: "in_transit",
              is_recurring: false,
            },
          ],
          total: 1,
          skip: 0,
          limit: 5,
        };
      }
      return { items: [], total: 0, skip: 0, limit: 5 };
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole("region", { name: "Financial Health Scorecard" })).toHaveTextContent(
        "$82,000.00",
      );
    });

    const scorecard = screen.getByRole("region", { name: "Financial Health Scorecard" });
    expect(scorecard).toHaveTextContent("4.0 mos");
    expect(scorecard).toHaveTextContent("$1,500.00");
    expect(scorecard).toHaveTextContent("26.8%");
    expect(scorecard).toHaveTextContent("Margin LTV 30.0%");

    const ingestion = screen.getByRole("region", { name: "Ingestion status" });
    expect(ingestion).toHaveTextContent("imap-bank-sync");
    expect(ingestion).toHaveTextContent("succeeded");

    const cashflow = screen.getByRole("region", { name: "Operating Free Cashflow" });
    expect(cashflow).toHaveTextContent("$1,200.00");
    expect(cashflow).toHaveTextContent("Organic margin 24.0%");

    const inTransit = screen.getByRole("region", { name: "In-transit transfers" });
    expect(inTransit).toHaveTextContent("Cross-border wire");
  });

  it("renders graceful empty ingestion state when no runs exist", async () => {
    vi.mocked(reportsApi.getFinancialHealthReport).mockResolvedValue({
      currency: "USD",
      available_currencies: ["USD"],
      multi_currency_warning: false,
      scorecard: {
        total_assets: 0,
        total_liabilities: 0,
        reconciled_net_worth: 0,
        liquid_cash_total: 0,
        baseline_monthly_burn: 0,
        liquid_runway_months: null,
        target_liquidity_months: 4,
        monthly_debt_service: 0,
        total_monthly_interest_drag: 0,
        debt_to_asset_ratio_pct: null,
        margin_ltv_pct: null,
        included_asset_count: 0,
        included_liability_count: 0,
        excluded_account_count: 0,
      },
    });
    vi.mocked(reportsApi.getOperatingCashflowReport).mockResolvedValue({
      period: { start_date: "2026-11-01", end_date: "2026-11-30" },
      currency: "USD",
      available_currencies: ["USD"],
      multi_currency_warning: false,
      waterfall: {
        income_fixed: 0,
        income_variable: 0,
        total_external_income: 0,
        loans: 0,
        fixed_expenses: 0,
        variable_expenses: 0,
        unexpected_expenses: 0,
        total_operating_outflows: 0,
        operating_free_cashflow: 0,
        savings: 0,
        capital_deployments: 0,
        net_allocated_surplus: 0,
        net_ledger_cashflow: 0,
        non_operating_inflows: 0,
        internal_sweeps_volume: 0,
        debt_service_to_income_pct: 0,
        organic_fcf_margin_pct: 0,
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
      in_transit: { count: 0, inflows: 0, outflows: 0, total_volume: 0 },
    });
    vi.mocked(ingestionApi.getLatestIngestionRun).mockResolvedValue(null);
    vi.mocked(transactionsApi.listTransactions).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 5,
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole("region", { name: "Ingestion status" })).toHaveTextContent(
        "No ingestion runs recorded yet",
      );
    });
    expect(screen.getByRole("region", { name: "Financial Health Scorecard" })).toHaveTextContent(
      "N/A",
    );
  });

  it("switches currency across both scorecard and operating cashflow when multi-currency", async () => {
    vi.mocked(reportsApi.getFinancialHealthReport).mockImplementation(async (params) => {
      const currency = params?.currency ?? "USD";
      return {
        currency,
        available_currencies: ["USD", "COP"],
        multi_currency_warning: true,
        scorecard: {
          total_assets: currency === "COP" ? 40000000 : 10000,
          total_liabilities: 0,
          reconciled_net_worth: currency === "COP" ? 40000000 : 10000,
          liquid_cash_total: currency === "COP" ? 10000000 : 5000,
          baseline_monthly_burn: 1000,
          liquid_runway_months: 5,
          target_liquidity_months: 4,
          monthly_debt_service: 0,
          total_monthly_interest_drag: 0,
          debt_to_asset_ratio_pct: 0,
          margin_ltv_pct: null,
          included_asset_count: 1,
          included_liability_count: 0,
          excluded_account_count: 0,
        },
      };
    });
    vi.mocked(reportsApi.getOperatingCashflowReport).mockResolvedValue({
      period: { start_date: "2026-11-01", end_date: "2026-11-30" },
      currency: "USD",
      available_currencies: ["USD", "COP"],
      multi_currency_warning: true,
      waterfall: {
        income_fixed: 0,
        income_variable: 0,
        total_external_income: 0,
        loans: 0,
        fixed_expenses: 0,
        variable_expenses: 0,
        unexpected_expenses: 0,
        total_operating_outflows: 0,
        operating_free_cashflow: 0,
        savings: 0,
        capital_deployments: 0,
        net_allocated_surplus: 0,
        net_ledger_cashflow: 0,
        non_operating_inflows: 0,
        internal_sweeps_volume: 0,
        debt_service_to_income_pct: 0,
        organic_fcf_margin_pct: 0,
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
      in_transit: { count: 0, inflows: 0, outflows: 0, total_volume: 0 },
    });
    vi.mocked(ingestionApi.getLatestIngestionRun).mockResolvedValue(null);
    vi.mocked(transactionsApi.listTransactions).mockResolvedValue({
      items: [],
      total: 0,
      skip: 0,
      limit: 5,
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <DashboardPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    const copButton = await screen.findByRole("button", { name: "COP" });
    fireEvent.click(copButton);

    await waitFor(() => {
      expect(reportsApi.getFinancialHealthReport).toHaveBeenCalledWith(
        expect.objectContaining({ currency: "COP" }),
      );
      expect(reportsApi.getOperatingCashflowReport).toHaveBeenCalledWith(
        expect.objectContaining({ currency: "COP" }),
      );
    });
  });
});
