import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as authApi from "@/api/auth";
import { AppLayout } from "@/components/layout/AppLayout";
import { AccountsPage } from "@/pages/AccountsPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/auth", () => ({
  getBffSession: vi.fn(),
  bffLogin: vi.fn(),
  bffLogout: vi.fn(),
  bffRegister: vi.fn(),
  bffRefresh: vi.fn(),
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
  });
});

describe("AppLayout", () => {
  it("renders nav landmarks and navigates between stub routes", async () => {
    const user = userEvent.setup();

    render(
      <QueryTestProvider>
        <MemoryRouter initialEntries={["/dashboard"]}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/accounts" element={<AccountsPage />} />
            </Route>
          </Routes>
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1, name: "Dashboard" })).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getAllByText("tester@example.com").length).toBeGreaterThan(0);
    });
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();

    const nav = screen.getByRole("navigation", { name: "App sections" });
    expect(within(nav).getByRole("link", { name: "Accounts" })).toBeInTheDocument();

    await user.click(within(nav).getByRole("link", { name: "Accounts" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1, name: "Accounts" })).toBeInTheDocument();
    });
  });
});
