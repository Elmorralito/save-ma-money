import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  getOperatingCashflowReport: vi.fn(),
  getPlannedVsActualReport: vi.fn(),
  getDebtPaydownReport: vi.fn(),
  simulateDebtPaydown: vi.fn(),
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
        fx_rate: 1,
        balance: 100,
        is_active: true,
        include_in_balance: true,
      },
    ],
    limit: 100,
    skip: 0,
    total: 1,
  });
  vi.mocked(reportsApi.getOperatingCashflowReport).mockResolvedValue({
    period: { start_date: "2026-01-01", end_date: "2026-01-31" },
    currency: "USD",
    available_currencies: ["USD", "COP"],
    multi_currency_warning: true,
    waterfall: {
      income_fixed: 1000,
      income_variable: 200,
      total_external_income: 1200,
      loans: 150,
      fixed_expenses: 350,
      variable_expenses: 100,
      unexpected_expenses: 50,
      total_operating_outflows: 650,
      operating_free_cashflow: 550,
      organic_fcf_margin_pct: 45.83,
      debt_service_to_income_pct: 12.5,
      savings: 120,
      capital_deployments: 80,
      net_allocated_surplus: 350,
      non_operating_inflows: 500,
      net_ledger_cashflow: 850,
      internal_sweeps_volume: 400,
      status_tone: "positive",
    },
    buckets: [
      {
        bucket: "income_fixed",
        label: "Fixed Income",
        group: "income",
        amount: 1000,
        share_of_income_pct: 83.33,
        transaction_count: 1,
        top_categories: [
          { category_id: "c1", category_name: "Salary", amount: 1000, transaction_count: 1 },
        ],
      },
    ],
    in_transit: { count: 1, inflows: 0, outflows: 0, total_volume: 90 },
    monthly_series: [],
    diagnostics: {
      unbucketed_category_count: 0,
      unbucketed_amount: 0,
      cashflow_only_cc_excluded_count: 0,
      cashflow_only_cc_excluded_amount: 0,
      cashflow_only_cc_account_names: [],
    },
  });
  vi.mocked(reportsApi.getPlannedVsActualReport).mockResolvedValue({
    period: { start_date: "2026-01-01", end_date: "2026-01-31" },
    currency: "USD",
    available_currencies: ["USD"],
    multi_currency_warning: false,
    summary: {
      planned_income: 1200,
      actual_income: 1200,
      planned_outflows: 600,
      actual_outflows: 650,
      planned_operating_fcf: 600,
      actual_operating_fcf: 550,
      net_fcf_variance: -50,
      adherence_pct: 91.67,
      reconciliation_flag_count: 1,
      status_tone: "warning",
    },
    bucket_rollups: [],
    template_items: [
      {
        template_id: "t1",
        template_name: "Apartment Rent",
        category_id: "c2",
        category_name: "Rent",
        bucket: "fixed_expense",
        due_date: "2026-01-05",
        planned_amount: 350,
        actual_amount: 350,
        variance_amount: 0,
        variance_pct: 0,
        is_favorable: true,
        status: "paid",
        linked_transaction_count: 1,
      },
    ],
    unplanned_items: [],
    reconciliation_flags: [
      {
        code: "unlinked_high_value",
        severity: "warning",
        message: "Unlinked posting of 100.00 matches template.",
      },
    ],
  });
  vi.mocked(reportsApi.getDebtPaydownReport).mockResolvedValue({
    currency: "USD",
    available_currencies: ["USD"],
    multi_currency_warning: false,
    summary: {
      total_debt: 5000,
      active_liability_count: 1,
      total_monthly_interest_drag: 72,
      total_annual_interest_drag: 950,
      total_monthly_contractual_payment: 300,
      weighted_average_ea_pct: 19.0,
      highest_rate_account_name: "Loan A",
      highest_rate_payoff_date: "2027-08-01",
    },
    liabilities: [
      {
        priority_rank: 1,
        account_id: "l1",
        account_name: "Loan A",
        account_kind: "loan_mortgage",
        currency: "USD",
        balance: 5000,
        effective_annual_rate_pct: 19.0,
        effective_monthly_rate_pct: 1.46,
        monthly_interest_drag: 72,
        annual_interest_drag: 950,
        monthly_contractual_payment: 300,
        monthly_extras_payment: 15,
        monthly_principal_amortization: 213,
        remaining_periods: 18,
        estimated_payoff_date: "2027-08-01",
        negative_amortization: false,
        linked_asset: null,
      },
    ],
    liquidity_context: {
      liquid_cash_total: 10000,
      baseline_monthly_burn: 2000,
      liquid_runway_months: 5,
      target_liquidity_months: 4,
      safe_lump_sum_headroom: 2000,
    },
    excluded_liabilities: null,
  });
  vi.mocked(reportsApi.simulateDebtPaydown).mockResolvedValue({
    currency: "USD",
    strategy: "avalanche",
    baseline_months_to_payoff: 18,
    accelerated_months_to_payoff: 11,
    baseline_payoff_date: "2027-08-01",
    accelerated_payoff_date: "2027-01-01",
    months_saved: 7,
    baseline_total_interest: 950,
    accelerated_total_interest: 520,
    total_interest_saved: 430,
    per_liability_impact: [],
    monthly_trajectory: [
      {
        month: "2026-03",
        baseline_total_debt: 4800,
        accelerated_total_debt: 4500,
        priority_loan_balance: 4500,
        interest_paid: 72,
        extra_applied: 250,
        events: [],
      },
    ],
    liquidity_guardrail: {
      status: "safe",
      liquid_cash_total: 10000,
      post_lump_sum_cash: 10000,
      post_lump_sum_runway_months: 5,
      target_liquidity_months: 4,
      safe_lump_sum_headroom: 2000,
      message: "Liquid cash remains above your target runway floor after planned prepayments.",
    },
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
  it("loads Operating Cashflow waterfall and KPI strip by default", async () => {
    mockHappyPath();

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <ReportsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Cashflow Waterfall")).toBeInTheDocument();
    });
    expect(screen.getByText(/Multiple currencies detected/)).toBeInTheDocument();
    expect(screen.getByText("Non-Operating & Ledger Reconciliation")).toBeInTheDocument();
    expect(reportsApi.getOperatingCashflowReport).toHaveBeenCalled();
    expect(reportsApi.getSpendingReport).not.toHaveBeenCalled();
  });

  it("switches across Planned vs Actual, Debt Paydown simulator, and Spending tabs", async () => {
    const user = userEvent.setup();
    mockHappyPath();

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <ReportsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Cashflow Waterfall")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("tab", { name: "Planned vs. Actual" }));
    await waitFor(() => {
      expect(screen.getByText("Apartment Rent")).toBeInTheDocument();
    });
    expect(screen.getByText("Reconciliation Alerts")).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Debt Paydown" }));
    await waitFor(() => {
      expect(screen.getByText("Loan A")).toBeInTheDocument();
    });
    await user.type(screen.getByLabelText(/Extra monthly prepayment/i), "250");
    await user.click(screen.getByRole("button", { name: "Simulate paydown" }));
    await waitFor(() => {
      expect(reportsApi.simulateDebtPaydown).toHaveBeenCalled();
    });
    expect(screen.getByText(/7 mo\(s\)/)).toBeInTheDocument();
    expect(screen.getByText(/remains above your target runway floor/i)).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: "Spending" }));
    await waitFor(() => {
      expect(screen.getByText("Total spending")).toBeInTheDocument();
    });
    expect(screen.getByText("food")).toBeInTheDocument();
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
    vi.mocked(reportsApi.getOperatingCashflowReport).mockRejectedValue(
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

  it("formats debt KPI using debt.currency when different from waterfall, supports ArrowRight tab navigation, and exposes aria-expanded on bucket toggle", async () => {
    const user = userEvent.setup();
    mockHappyPath();
    vi.mocked(reportsApi.getDebtPaydownReport).mockResolvedValue({
      currency: "COP",
      available_currencies: ["USD", "COP"],
      multi_currency_warning: true,
      summary: {
        total_debt: 5000000,
        active_liability_count: 1,
        total_monthly_interest_drag: 75000,
        total_annual_interest_drag: 900000,
        total_monthly_contractual_payment: 250000,
        weighted_average_ea_pct: 19.0,
        highest_rate_account_name: "Loan COP",
        highest_rate_payoff_date: "2027-08-01",
      },
      liabilities: [],
      liquidity_context: {
        liquid_cash_total: 10000000,
        baseline_monthly_burn: 2000000,
        liquid_runway_months: 5,
        target_liquidity_months: 4,
        safe_lump_sum_headroom: 2000000,
      },
      excluded_liabilities: null,
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <ReportsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Cashflow Waterfall")).toBeInTheDocument();
    });

    const toggleBtn = screen.getByRole("button", {
      name: "Show top categories for Fixed Income",
    });
    expect(toggleBtn).toHaveAttribute("aria-expanded", "false");
    await user.click(toggleBtn);
    expect(
      screen.getByRole("button", { name: "Hide top categories for Fixed Income" }),
    ).toHaveAttribute("aria-expanded", "true");

    // Debt KPI uses COP formatting rather than waterfall USD
    await waitFor(() => {
      expect(screen.getByText(/COP\s*75,000/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/\$75,000/)).not.toBeInTheDocument();

    // WAI-ARIA ArrowRight moves selection & focus from Operating Cashflow to Planned vs. Actual
    const firstTab = screen.getByRole("tab", { name: "Operating Cashflow" });
    firstTab.focus();
    await user.keyboard("{ArrowRight}");
    const secondTab = screen.getByRole("tab", { name: "Planned vs. Actual" });
    expect(secondTab).toHaveAttribute("aria-selected", "true");
    expect(secondTab).toHaveFocus();
  });
});
