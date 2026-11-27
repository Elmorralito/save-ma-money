import { afterEach, describe, expect, it, vi } from "vitest";

import * as accountsApi from "@/api/accounts";
import * as aiApi from "@/api/ai";
import * as authApi from "@/api/auth";
import * as categoriesApi from "@/api/categories";
import * as cliBridgeApi from "@/api/cliBridge";
import * as healthApi from "@/api/health";
import * as http from "@/api/http";
import * as ingestionApi from "@/api/ingestion";
import * as metaApi from "@/api/meta";
import * as projectionsApi from "@/api/projections";
import * as queries from "@/api/queries";
import * as reportsApi from "@/api/reports";
import * as settingsApi from "@/api/settings";
import * as transactionTemplatesApi from "@/api/transactionTemplates";
import * as transactionsApi from "@/api/transactions";
import { defaultLedgerSideForKind, extensionFieldForAccountKind } from "@/lib/accountKinds";
import { fetchGlobalSearch, hitHref, type GlobalSearchHit } from "@/lib/globalSearch";

vi.mock("@/api/http", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/http")>();
  return {
    ...actual,
    apiFetch: vi.fn(),
  };
});

function ok<T>(data: T) {
  return {
    data,
    status: 200,
    headers: new Headers(),
    response: new Response(),
    discovery: {
      breakingChanges: null,
      bulkMax: null,
      reportWindowMaxDays: null,
      cashFlowRefreshDefault: null,
      reportsForeignAccountStatus: null,
      errorCode: null,
      compatActive: [],
    },
  };
}

afterEach(() => {
  vi.clearAllMocks();
});

describe("API modules & globalSearch helpers", () => {
  it("calls accounts & categories endpoints with expected paths and methods", async () => {
    vi.mocked(http.apiFetch).mockResolvedValue(ok({ items: [], limit: 10, skip: 0, total: 0 }));

    await accountsApi.listAccounts({
      account_kind: "checking",
      ledger_side: "asset",
      is_active: true,
      skip: 5,
      limit: 10,
    });
    await accountsApi.listAccounts();
    await accountsApi.getAccount("acc-1");
    await accountsApi.createAccount({
      name: "Wallet",
      description: "Main wallet",
      account_kind: "checking",
      ledger_side: "asset",
      currency: "COP",
      fx_rate: 1,
      include_in_balance: true,
      initial_value: 0,
    });
    await accountsApi.updateAccount("acc-1", { name: "Updated Wallet" });
    await accountsApi.deleteAccount("acc-1");

    await categoriesApi.listCategories({
      parent_id: "p1",
      category_type: "expense",
      skip: 0,
      limit: 20,
    });
    await categoriesApi.listCategories();
    await categoriesApi.getCategory("cat-1");
    await categoriesApi.createCategory({
      name: "Food",
      description: "Food and groceries",
      category_type: "expense",
    });
    await categoriesApi.updateCategory("cat-1", { name: "Groceries" });
    await categoriesApi.deleteCategory("cat-1");

    expect(vi.mocked(http.apiFetch)).toHaveBeenCalledTimes(12);
  });

  it("calls settings, projections, ai, and globalSearch endpoints cleanly", async () => {
    vi.mocked(http.apiFetch).mockResolvedValue(ok({ ok: true }));

    await settingsApi.getUserSettings();
    await settingsApi.updateUserSettings({ display_name: "Ana" });
    await settingsApi.resetUserSettings();

    await projectionsApi.getProjectionPortfolio();
    await projectionsApi.saveAccountProjectionConfig("acc-1", { annual_rate_pct: 12 });
    await projectionsApi.computeLoanProjection({
      principal: 1000,
      annual_rate_pct: 10,
      rate_convention: "CO_EA",
      remaining_months: 12,
      monthly_insurance: 0,
      extra_monthly_payment: 0,
      extra_lump_sum: 0,
      method: "french_fixed",
      currency: "COP",
    });
    await projectionsApi.computeCreditCardProjection({
      balance: 1000,
      annual_rate_pct: 20,
      rate_convention: "CO_EA",
      monthly_payment: 200,
      monthly_new_spend: 0,
      handling_fee: 0,
      pay_in_one_installment: false,
      currency: "COP",
    });
    await projectionsApi.computeRealEstateProjection({
      current_value: 100000,
      annual_appreciation_pct: 5,
      horizon_years: 5,
      monthly_rent_income: 1000,
      occupancy_pct: 90,
      annual_rent_growth_pct: 4,
      monthly_hoa_and_maintenance: 100,
      annual_property_tax_pct: 1,
      mortgage_balance: 50000,
      mortgage_annual_rate_pct: 10,
      mortgage_rate_convention: "CO_EA",
      mortgage_remaining_months: 60,
      mortgage_monthly_insurance: 10,
      currency: "COP",
    });
    await projectionsApi.computeInvestmentProjection({
      initial_amount: 1000,
      investment_type: "hysa_co",
      expected_annual_return_pct: 9,
      rate_convention: "CO_EA",
      horizon_years: 5,
      monthly_contribution: 100,
      annual_fee_pct: 0,
      annual_inflation_pct: 4,
      tax_on_gains_pct: 7,
      annual_fx_drift_pct: 0,
      currency: "COP",
    });

    await aiApi.getAIStatus();
    await aiApi.getAIConfig();
    await aiApi.updateAIConfig({ mode: "lan_local" });
    await aiApi.fetchAIModels({ mode: "lan_local", connection: "ollama" });
    await aiApi.sendAIChat({ prompt: "hello" });

    await fetchGlobalSearch({
      q: "rent",
      kinds: ["account", "payment_due"],
      accountId: "acc-1",
      limit: 10,
    });

    const baseHit: Omit<GlobalSearchHit, "kind"> = {
      id: "1",
      title: "Rent Bill",
      subtitle: "",
      occurred_at: null,
      status: null,
      amount: null,
      currency: null,
      account_id: null,
      flags: [],
    };
    expect(hitHref({ ...baseHit, kind: "account" })).toBe("/accounts/1");
    expect(hitHref({ ...baseHit, kind: "transaction" })).toBe("/transactions?search=Rent%20Bill");
    expect(hitHref({ ...baseHit, kind: "payment_due" })).toBe("/payment-dues");
    expect(hitHref({ ...baseHit, kind: "category" })).toBe("/categories?search=Rent%20Bill");
    expect(hitHref({ ...baseHit, kind: "projection" })).toBe("/projections");
    expect(hitHref({ ...baseHit, kind: "unknown" as GlobalSearchHit["kind"] })).toBe("/dashboard");

    await reportsApi.getSpendingReport({
      start_date: "2026-01-01",
      end_date: "2026-01-31",
      group_by: "category",
      account_id: "acc-1",
    });
    await reportsApi.getOperatingCashflowReport({
      start_date: "2026-01-01",
      end_date: "2026-01-31",
      currency: "COP",
      include_monthly_series: true,
    });
    await reportsApi.getPlannedVsActualReport({
      start_date: "2026-01-01",
      end_date: "2026-01-31",
      cashflow_bucket: "VARIABLE_EXPENSE",
    });
    await reportsApi.getDebtPaydownReport({ currency: "COP", include_excluded: true });
    await reportsApi.getFinancialHealthReport({ currency: "COP", target_liquidity_months: 4 });
    await reportsApi.simulateDebtPaydown({
      extra_monthly_prepayment: 100000,
      horizon_months: 24,
      lump_sum_month_offset: 1,
      lump_sum_prepayment: 0,
      strategy: "avalanche",
      target_liquidity_months: 4,
      currency: "COP",
    });

    await healthApi.getHealth();
    await healthApi.getHealthLive();
    await metaApi.getClientContract();

    expect(extensionFieldForAccountKind("checking")).toBe("banking_details");
    expect(extensionFieldForAccountKind("investment_brokerage")).toBe("trading_details");
    expect(extensionFieldForAccountKind("real_estate")).toBe("real_estate_details");
    expect(extensionFieldForAccountKind("credit_card")).toBe("credit_card_details");
    expect(extensionFieldForAccountKind("loan_mortgage")).toBe("loan_details");
    expect(extensionFieldForAccountKind("other_asset")).toBeNull();
    expect(defaultLedgerSideForKind("credit_card")).toBe("liability");
    expect(defaultLedgerSideForKind("checking")).toBe("asset");

    await ingestionApi.getLatestIngestionRun({ connection_id: "c1" });
    await ingestionApi.listIngestionRuns({ connection_id: "c1", skip: 0, limit: 10 });
    await ingestionApi.listIngestionConnections({ skip: 0, limit: 10 });
    expect(ingestionApi.gmailOAuthStartUrl()).toBe("/api/v1/ingestion/gmail/oauth/start");
    await ingestionApi.upsertEmailIngestionConnection({
      enabled: true,
      lookback_hours: 72,
      email_senders: ["nu.com.co"],
      email_subjects: [],
      gmail_access_enabled: true,
      parsing_rules: [],
    });
    await ingestionApi.disconnectGmailConnection();
    await ingestionApi.testEmailParse({
      sender: "nu@nu.com.co",
      subject: "Pago",
      body: "Tu pago fue $100",
    });

    const ctx = {
      signal: new AbortController().signal,
      client: {} as never,
      meta: undefined,
    };
    const r1 = queries.latestIngestionRunQueryOptions();
    const r2 = queries.ingestionRunsQueryOptions();
    const r3 = queries.ingestionConnectionsQueryOptions();
    const r4 = queries.transactionTemplateDetailQueryOptions("t-1");
    const r5 = queries.upcomingDuesQueryOptions();
    await r1.queryFn?.({ ...ctx, queryKey: r1.queryKey });
    await r2.queryFn?.({ ...ctx, queryKey: r2.queryKey });
    await r3.queryFn?.({ ...ctx, queryKey: r3.queryKey });
    await r4.queryFn?.({ ...ctx, queryKey: r4.queryKey });
    await r5.queryFn?.({ ...ctx, queryKey: r5.queryKey });

    await transactionsApi.getTransaction("tx-1");
    await transactionsApi.createTransaction({
      description: "Coffee",
      transaction_type: "expense",
      amount: 10,
      currency: "USD",
      transaction_date: "2026-11-27",
      account_id: "acc-1",
      scheduled: false,
      settlement_status: "settled",
    });
    await transactionsApi.updateTransaction("tx-1", { description: "Latte" });
    await transactionsApi.deleteTransaction("tx-1");
    await transactionsApi.executeTransaction("tx-1");

    await transactionTemplatesApi.getTransactionTemplate("tmpl-1");
    await transactionTemplatesApi.createTransactionTemplate({
      name: "Rent",
      description: "Monthly",
      planned_amount: 1000,
      planned_day: 5,
      use_month_end: false,
      from_account_id: "acc-1",
      category_id: "cat-1",
    });
    await transactionTemplatesApi.updateTransactionTemplate("tmpl-1", { name: "Rent 2" });
    await transactionTemplatesApi.deleteTransactionTemplate("tmpl-1");
    await transactionTemplatesApi.markTemplatePaid("tmpl-1");
    await transactionTemplatesApi.clearTemplatePaid("tmpl-1");

    await authApi.bffRegister({ email: "a@b.com", password: "Password123!" });
    await authApi.bffResendConfirmation({ email: "a@b.com" });
    await authApi.bffRefresh();
    await authApi.bffLogout();
    expect(authApi.bffOAuthStartUrl("google", "/reports")).toContain("/api/v1/auth/oauth/google");

    const origPost = window.postMessage.bind(window);
    vi.spyOn(window, "postMessage").mockImplementation((msg: unknown) => {
      const m = msg as {
        channel?: string;
        direction?: string;
        requestId?: string;
        action?: string;
      };
      if (m?.channel === "papita-cli-bridge:v1" && m.direction === "from-page") {
        queueMicrotask(() => {
          window.dispatchEvent(
            new MessageEvent("message", {
              source: window,
              origin: window.location.origin,
              data: {
                channel: "papita-cli-bridge:v1",
                direction: "from-extension",
                requestId: m.requestId,
                ok: true,
                installed: true,
                originGranted: true,
                nativeHostReady: true,
                granted: true,
                clis: [],
                models: [{ id: "m1", label: "M1" }],
                reply: "bridge reply",
              },
            }),
          );
        });
        return;
      }
      origPost(msg, window.location.origin);
    });
    const status = await cliBridgeApi.detectCliBridge(500);
    expect(status.installed).toBe(true);
    expect((await cliBridgeApi.requestCliBridgePermission("cli:agy")).granted).toBe(true);
    expect((await cliBridgeApi.bridgeListModels("cli:agy")).models[0]?.id).toBe("m1");
    expect((await cliBridgeApi.bridgeChat({ connection: "cli:agy", userPrompt: "hi" })).reply).toBe(
      "bridge reply",
    );
    await cliBridgeApi.revokeCliBridgePermission();
  });
});
