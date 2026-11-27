import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as accountsApi from "@/api/accounts";
import * as aiApi from "@/api/ai";
import * as categoriesApi from "@/api/categories";
import * as ingestionApi from "@/api/ingestion";
import { EmailIngestionPage } from "@/pages/EmailIngestionPage";
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
        name: "Nu Cuenta",
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
        name: "Food",
        category_type: "expense",
        is_active: true,
      },
    ],
    limit: 100,
    skip: 0,
    total: 1,
  });
  vi.mocked(ingestionApi.listIngestionConnections).mockResolvedValue({
    items: [],
    limit: 20,
    skip: 0,
    total: 0,
  });
  vi.mocked(ingestionApi.testEmailParse).mockResolvedValue({
    matched: true,
    matched_rule_name: "Nu default",
    parser_used: "nu-email",
    transaction_type: "transfer",
    amount: 1975723,
    currency: "COP",
    description: "Pago tarjeta Nu",
    default_account_id: "11111111-1111-1111-1111-111111111111",
    default_category_id: "22222222-2222-2222-2222-222222222222",
    error: null,
  });
  vi.mocked(ingestionApi.upsertEmailIngestionConnection).mockResolvedValue({
    id: "99999999-9999-9999-9999-999999999999",
    provider: "email",
    flow_name: "papita-email-ingestion",
    enabled: true,
    lookback_hours: 72,
    email_senders: ["notificacionesbancolombia.com"],
    email_subjects: [],
    email_source_label: "INBOX",
    email_query: null,
    parsing_rules: [],
    gmail_connected_email: null,
    gmail_access_enabled: false,
    gmail_connected: false,
    created_at: null,
    updated_at: null,
  });
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("EmailIngestionPage", () => {
  it("renders parser sandbox, switches bank samples, runs dry-run parse test, and adds sender", async () => {
    const user = userEvent.setup();

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <EmailIngestionPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Live Parser Sandbox")).toBeInTheDocument();
    });

    const bancolombiaBtns = screen.getAllByRole("button", { name: /Bancolombia/i });
    const firstBtn = bancolombiaBtns[0];
    const lastBtn = bancolombiaBtns[bancolombiaBtns.length - 1];
    if (!firstBtn || !lastBtn) throw new Error("Missing Bancolombia buttons");
    await user.click(firstBtn);
    await user.click(lastBtn);
    await user.click(screen.getByRole("button", { name: /Run test/i }));

    await waitFor(() => {
      expect(ingestionApi.testEmailParse).toHaveBeenCalledTimes(1);
    });
    expect(screen.getByText(/Pago tarjeta Nu/i)).toBeInTheDocument();

    for (const cb of screen.queryAllByRole("checkbox")) {
      fireEvent.click(cb);
    }
    for (const tb of screen.queryAllByRole("textbox")) {
      fireEvent.change(tb, { target: { value: "alerts.example.com" } });
    }
    for (const sb of screen.queryAllByRole("spinbutton")) {
      fireEvent.change(sb, { target: { value: "48" } });
    }
    for (const btn of screen.getAllByRole("button", { name: /^Add$/i })) {
      await user.click(btn);
    }
    const saveBtn = screen.queryByRole("button", { name: /Save email settings|Save changes/i });
    if (saveBtn) {
      await user.click(saveBtn);
    }
  });
});
