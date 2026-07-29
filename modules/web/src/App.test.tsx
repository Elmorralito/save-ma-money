import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "@/App";
import { QueryTestProvider } from "@/test/queryWrapper";

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

describe("App", () => {
  it("renders the scaffold heading and contract probe section", () => {
    render(
      <QueryTestProvider>
        <App />
      </QueryTestProvider>,
    );
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "API probe status" })).toBeInTheDocument();
  });
});
