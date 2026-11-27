import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as accountsApi from "@/api/accounts";
import * as aiApi from "@/api/ai";
import * as categoriesApi from "@/api/categories";
import * as ingestionApi from "@/api/ingestion";
import * as settingsApi from "@/api/settings";
import { SettingsPage } from "@/pages/SettingsPage";
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

vi.mock("@/api/ingestion", () => ({
  getLatestIngestionRun: vi.fn(),
  listIngestionRuns: vi.fn(),
  listIngestionConnections: vi.fn(),
  gmailOAuthStartUrl: vi.fn(() => "/api/v1/ingestion/gmail/oauth/start"),
  upsertEmailIngestionConnection: vi.fn(),
  disconnectGmailConnection: vi.fn(),
  testEmailParse: vi.fn(),
}));

vi.mock("@/api/settings", () => ({
  getUserSettings: vi.fn(),
  updateUserSettings: vi.fn(),
  resetUserSettings: vi.fn(),
}));

const sampleSettings: settingsApi.UserSettings = {
  id: "00000000-0000-0000-0000-000000000001",
  username: "tester",
  email: "tester@example.com",
  display_name: "Test User",
  phone: "+573001112233",
  auth_provider: "local",
  provider_type: "email",
  updated_at: null,
  preferences: {
    base_currency: "COP",
    locale: "en-US",
    timezone: "America/Bogota",
    date_format: "YYYY-MM-DD",
    default_page_size: 25,
    hide_balances_by_default: false,
    default_account_id: null,
    default_income_category_id: null,
    default_expense_category_id: null,
    credit_card_cashflow_only: true,
    auto_refresh_balances: true,
    fiscal_month_start_day: 1,
    payment_due_reminder_days: 5,
    low_runway_months_threshold: 3,
    high_utilization_pct_threshold: 30,
    large_transaction_alert_amount: null,
    redact_card_numbers: true,
    require_dkim_spf_for_email_ingestion: true,
    session_idle_timeout_minutes: 120,
  },
};

beforeEach(() => {
  vi.mocked(settingsApi.getUserSettings).mockResolvedValue(sampleSettings);
  vi.mocked(settingsApi.updateUserSettings).mockResolvedValue(sampleSettings);
  vi.mocked(settingsApi.resetUserSettings).mockResolvedValue(sampleSettings);
  vi.mocked(accountsApi.listAccounts).mockResolvedValue({
    items: [],
    limit: 100,
    skip: 0,
    total: 0,
  });
  vi.mocked(categoriesApi.listCategories).mockResolvedValue({
    items: [],
    limit: 100,
    skip: 0,
    total: 0,
  });
  vi.mocked(ingestionApi.listIngestionConnections).mockResolvedValue({
    items: [],
    limit: 20,
    skip: 0,
    total: 0,
  });
  vi.mocked(aiApi.getAIStatus).mockResolvedValue({
    enabled: true,
    available: true,
    provider: "cli:agy",
    model: "agy",
    default_connection: "cli:agy",
    connections: [{ id: "cli:agy", kind: "cli", provider: "cli:agy", model: "agy", ready: true }],
    single_owner_enforced: true,
  });
  vi.mocked(aiApi.getAIConfig).mockResolvedValue({
    enabled: true,
    mode: "sidecar",
    default_connection: "cli:agy",
    model: null,
    base_url: null,
    include_financial_context_by_default: true,
    reports_ai_enabled: true,
    payment_dues_ai_enabled: true,
    cli_permission_granted: false,
    lan_permission_granted: false,
    api_permission_granted: false,
    has_api_key: false,
    api_key_hint: null,
  });
  vi.mocked(aiApi.fetchAIModels).mockResolvedValue({
    connection: "cli:agy",
    mode: "sidecar",
    ready: true,
    source: "live",
    models: [],
    default_model: null,
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("SettingsPage", () => {
  it("loads user settings, switches sections, saves, and resets defaults", async () => {
    const user = userEvent.setup();

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <SettingsPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByDisplayValue("Test User")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Save changes/i }));
    await waitFor(() => {
      expect(settingsApi.updateUserSettings).toHaveBeenCalledTimes(1);
    });

    await user.click(screen.getByRole("button", { name: /AI & LLM/i }));
    await waitFor(() => {
      expect(screen.getByText(/Built-in Model/i)).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Show all sections/i }));
    await waitFor(() => {
      expect(screen.getByText("Currency & Display")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Reset/i }));
    await waitFor(() => {
      expect(settingsApi.resetUserSettings).toHaveBeenCalledTimes(1);
    });

    await user.selectOptions(screen.getByLabelText(/Base currency/i), "USD");
    await user.selectOptions(screen.getByLabelText(/Number & language locale/i), "en-US");
    await user.click(screen.getByRole("checkbox", { name: /Autosave/i }));

    // Exercise interactive form controls across all visible settings sections
    for (const cb of screen.queryAllByRole("checkbox")) {
      fireEvent.click(cb);
    }
    for (const num of screen.queryAllByRole("spinbutton")) {
      fireEvent.change(num, { target: { value: "5" } });
    }
    for (const sel of screen.queryAllByRole("combobox")) {
      const opts = sel.querySelectorAll("option");
      const lastVal = opts[opts.length - 1]?.getAttribute("value");
      if (lastVal) fireEvent.change(sel, { target: { value: lastVal } });
    }
    fireEvent.change(screen.getByDisplayValue("Test User"), {
      target: { value: "Updated User" },
    });
  }, 15_000);
});
