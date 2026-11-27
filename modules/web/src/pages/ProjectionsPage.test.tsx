import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as aiApi from "@/api/ai";
import * as projectionsApi from "@/api/projections";
import { ProjectionsPage } from "@/pages/ProjectionsPage";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/ai", () => ({
  getAIStatus: vi.fn(),
  getAIConfig: vi.fn(),
  updateAIConfig: vi.fn(),
  fetchAIModels: vi.fn(),
  sendAIChat: vi.fn(),
}));

vi.mock("@/api/projections", () => ({
  getProjectionPortfolio: vi.fn(),
  saveAccountProjectionConfig: vi.fn(),
  computeLoanProjection: vi.fn(),
  computeCreditCardProjection: vi.fn(),
  computeRealEstateProjection: vi.fn(),
  computeInvestmentProjection: vi.fn(),
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
  vi.mocked(projectionsApi.getProjectionPortfolio).mockResolvedValue({
    debts: [
      {
        id: "d1",
        name: "Mortgage Loan",
        account_kind: "mortgage",
        group: "debt",
        currency: "COP",
        balance: 100000000,
        config: { annual_rate_pct: 12.0, rate_convention: "CO_EA", remaining_months: 60 },
      },
    ],
    credit_cards: [
      {
        id: "cc1",
        name: "Visa Infinite",
        account_kind: "credit_card",
        group: "credit_card",
        currency: "COP",
        balance: 2000000,
        config: { annual_rate_pct: 25.0, rate_convention: "CO_EA", monthly_payment: 500000 },
      },
    ],
    real_estate: [
      {
        id: "re1",
        name: "Bogota Apt",
        account_kind: "real_estate",
        group: "real_estate",
        currency: "COP",
        balance: 400000000,
        config: { annual_appreciation_pct: 8.0, horizon_years: 10, linked_mortgage_id: "d1" },
      },
    ],
    investments: [
      {
        id: "inv1",
        name: "IBKR ETF",
        account_kind: "trading",
        group: "investment",
        currency: "USD",
        balance: 15000,
        config: { investment_type: "us_equity_etf", annual_rate_pct: 9.0, horizon_years: 10 },
      },
    ],
  });
  vi.mocked(projectionsApi.computeLoanProjection).mockResolvedValue({
    currency: "COP",
    rate_convention: "CO_EA",
    annual_rate_pct: 12.0,
    monthly_rate_pct: 0.95,
    effective_annual_rate_pct: 12.0,
    scheduled_monthly_payment: 2200000,
    total_monthly_outflow: 2220000,
    payoff_months: 60,
    total_interest: 32000000,
    total_insurance: 1200000,
    total_paid: 133200000,
    interest_saved_vs_baseline: 0,
    months_saved_vs_baseline: 0,
    schedule: [
      {
        month: 1,
        payment_date: "2026-12-27",
        opening_balance: 100000000,
        scheduled_payment: 2200000,
        principal_paid: 1250000,
        interest_paid: 950000,
        insurance_paid: 20000,
        extra_paid: 0,
        total_outflow: 2220000,
        closing_balance: 98750000,
        cumulative_interest: 950000,
      },
    ],
  });
  vi.mocked(projectionsApi.computeCreditCardProjection).mockResolvedValue({
    currency: "COP",
    rate_convention: "CO_EA",
    monthly_rate_pct: 1.88,
    effective_annual_rate_pct: 25.0,
    months_to_payoff: 5,
    total_interest: 120000,
    total_fees: 0,
    total_paid: 2120000,
    warning: null,
    schedule: [],
  });
  vi.mocked(projectionsApi.computeRealEstateProjection).mockResolvedValue({
    currency: "COP",
    current_net_equity: 300000000,
    projected_property_value: 863570000,
    projected_mortgage_balance: 0,
    projected_net_equity: 863570000,
    cumulative_net_cashflow: 220000000,
    gross_rental_yield_pct: 10.5,
    cap_rate_pct: 7.5,
    schedule: [],
  });
  vi.mocked(projectionsApi.computeInvestmentProjection).mockResolvedValue({
    currency: "USD",
    investment_type: "us_equity_etf",
    rate_convention: "CO_EA",
    effective_net_annual_pct: 8.0,
    total_contributed: 15000,
    final_gross_value: 35510,
    final_real_value: 20000,
    estimated_tax: 3110,
    final_after_tax_value: 32400,
    total_net_gain: 17400,
    schedule: [],
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ProjectionsPage", () => {
  it("hydrates portfolio and calculates projections across all four tabs", async () => {
    const user = userEvent.setup();

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <ProjectionsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText(/Mortgage Loan/)).toBeInTheDocument();
    });

    const exerciseActiveTabControls = () => {
      for (const inp of screen.getAllByRole("spinbutton")) {
        fireEvent.change(inp, { target: { value: "12" } });
      }
      for (const sel of screen.getAllByRole("combobox")) {
        const opts = sel.querySelectorAll("option");
        const lastVal = opts[opts.length - 1]?.getAttribute("value");
        if (lastVal) fireEvent.change(sel, { target: { value: lastVal } });
      }
      for (const cb of screen.queryAllByRole("checkbox")) {
        fireEvent.click(cb);
      }
    };

    exerciseActiveTabControls();
    await user.click(screen.getByRole("button", { name: /Run projection/i }));
    await waitFor(() => {
      expect(projectionsApi.computeLoanProjection).toHaveBeenCalledTimes(1);
    });
    await user.click(screen.getByRole("button", { name: /Save assumptions/i }));
    await waitFor(() => {
      expect(projectionsApi.saveAccountProjectionConfig).toHaveBeenCalled();
    });

    const tabs = screen.getAllByRole("tab");
    const ccTab = tabs[1];
    const reTab = tabs[2];
    const invTab = tabs[3];
    if (!ccTab || !reTab || !invTab) throw new Error("Missing projection tabs");
    await user.click(ccTab);
    await waitFor(() => {
      expect(screen.getByText(/Visa Infinite/)).toBeInTheDocument();
    });
    exerciseActiveTabControls();
    await user.click(screen.getByRole("button", { name: /Run projection/i }));
    await waitFor(() => {
      expect(projectionsApi.computeCreditCardProjection).toHaveBeenCalledTimes(1);
    });

    await user.click(reTab);
    await waitFor(() => {
      expect(screen.getByText(/Bogota Apt/)).toBeInTheDocument();
    });
    exerciseActiveTabControls();
    await user.click(screen.getByRole("button", { name: /Run projection/i }));
    await waitFor(() => {
      expect(projectionsApi.computeRealEstateProjection).toHaveBeenCalledTimes(1);
    });

    await user.click(invTab);
    await waitFor(() => {
      expect(screen.getByText(/IBKR ETF/)).toBeInTheDocument();
    });
    exerciseActiveTabControls();
    await user.click(screen.getByRole("button", { name: /Run projection/i }));
    await waitFor(() => {
      expect(projectionsApi.computeInvestmentProjection).toHaveBeenCalledTimes(1);
    });
  }, 15_000);
});
