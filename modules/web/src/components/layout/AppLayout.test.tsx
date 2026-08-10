import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as authApi from "@/api/auth";
import type { BffSession, BffUser } from "@/api/auth";
import { AppLayout } from "@/components/layout/AppLayout";
import { sessionUserLabel } from "@/components/layout/sessionUserLabel";
import { AccountsPage } from "@/pages/AccountsPage";
import { DashboardPage } from "@/pages/DashboardPage";
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
  listAccounts: vi.fn(async () => ({ items: [], total: 0, skip: 0, limit: 5 })),
  getAccount: vi.fn(),
  createAccount: vi.fn(),
  updateAccount: vi.fn(),
  deleteAccount: vi.fn(),
}));

vi.mock("@/api/movements", () => ({
  listMovements: vi.fn(async () => ({ items: [], total: 0, skip: 0, limit: 5 })),
  getMovement: vi.fn(),
  createMovement: vi.fn(),
  updateMovement: vi.fn(),
  executeMovement: vi.fn(),
  cancelMovement: vi.fn(),
}));

vi.mock("@/api/transactionTemplates", () => ({
  listTransactionTemplates: vi.fn(async () => ({ items: [], total: 0, skip: 0, limit: 100 })),
  listUpcomingDues: vi.fn(async () => ({
    items: [],
    as_of: "2026-08-10",
    window_days: 14,
  })),
  getTransactionTemplate: vi.fn(),
  createTransactionTemplate: vi.fn(),
  updateTransactionTemplate: vi.fn(),
  deleteTransactionTemplate: vi.fn(),
  markTemplatePaid: vi.fn(),
  clearTemplatePaid: vi.fn(),
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

const fixtureUser: BffUser = {
  id: "00000000-0000-0000-0000-000000000001",
  username: "tester",
  email: "tester@example.com",
  display_name: null,
  phone: null,
  provider: "email",
  auth_provider: "local",
  created_at: "2026-07-29T00:00:00Z",
};

const authenticatedSession: BffSession = {
  authenticated: true,
  user: fixtureUser,
  csrf_token: "csrf-test",
  session_backend: "memory",
  access_expires_at: Math.floor(Date.now() / 1000) + 3600,
};

function renderShell(initialPath = "/dashboard") {
  return render(
    <QueryTestProvider>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/accounts" element={<AccountsPage />} />
          </Route>
          <Route path="/login" element={<h1>Login</h1>} />
        </Routes>
      </MemoryRouter>
    </QueryTestProvider>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

beforeEach(() => {
  vi.mocked(authApi.getBffSession).mockResolvedValue(authenticatedSession);
  vi.mocked(authApi.bffLogout).mockResolvedValue(undefined);
});

describe("sessionUserLabel", () => {
  it("prefers display_name, then username, then email", () => {
    expect(
      sessionUserLabel({
        ...fixtureUser,
        display_name: "  Ada  ",
        username: "ada",
        email: "a@x.com",
      }),
    ).toBe("Ada");
    expect(sessionUserLabel({ ...fixtureUser, display_name: null, username: "ada" })).toBe("ada");
    expect(
      sessionUserLabel({ ...fixtureUser, display_name: " ", username: "", email: "a@x.com" }),
    ).toBe("a@x.com");
  });
});

describe("AppLayout", () => {
  beforeEach(() => {
    window.localStorage.removeItem("papita.navOpen");
  });

  it("renders nav landmarks and navigates between stub routes", async () => {
    const user = userEvent.setup();

    renderShell();

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 1, name: /Welcome back, tester/i }),
      ).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByTestId("session-user-chip")).toHaveTextContent("tester");
    });
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();

    const nav = screen.getByRole("navigation", { name: "App sections" });
    expect(within(nav).getByRole("link", { name: "Accounts" })).toBeInTheDocument();

    await user.click(within(nav).getByRole("link", { name: "Accounts" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1, name: "Accounts" })).toBeInTheDocument();
    });
  });

  it("toggles the navigation sidebar open and closed", async () => {
    const user = userEvent.setup();
    renderShell();

    await waitFor(() => {
      expect(screen.getByRole("navigation", { name: "App sections" })).toBeInTheDocument();
    });

    const hideButtons = screen.getAllByRole("button", { name: "Hide navigation" });
    await user.click(hideButtons[0]!);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Show navigation" })).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Main navigation")).toHaveAttribute("aria-hidden", "true");

    await user.click(screen.getByRole("button", { name: "Show navigation" }));

    await waitFor(() => {
      expect(screen.getByLabelText("Main navigation")).toHaveAttribute("aria-hidden", "false");
    });
  });

  it("shows display_name on the session chip when present", async () => {
    vi.mocked(authApi.getBffSession).mockResolvedValue({
      ...authenticatedSession,
      user: { ...fixtureUser, display_name: "Test User" },
    });

    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("session-user-chip")).toHaveTextContent("Test User");
    });
  });

  it("shows a pending session affordance before the probe resolves", async () => {
    let resolveSession!: (value: BffSession) => void;
    vi.mocked(authApi.getBffSession).mockImplementation(
      () =>
        new Promise<BffSession>((resolve) => {
          resolveSession = resolve;
        }),
    );

    renderShell();

    expect(screen.getByTestId("session-user-chip")).toHaveTextContent("Session…");
    expect(screen.queryByRole("button", { name: "Sign out" })).not.toBeInTheDocument();

    resolveSession(authenticatedSession);

    await waitFor(() => {
      expect(screen.getByTestId("session-user-chip")).toHaveTextContent("tester");
    });
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
  });

  it("shows session unavailable when the probe fails", async () => {
    vi.mocked(authApi.getBffSession).mockRejectedValue(new Error("network down"));

    renderShell();

    await waitFor(() => {
      expect(screen.getByTestId("session-user-chip")).toHaveTextContent("Session unavailable");
    });
    expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
  });

  it("invokes BFF logout and returns to login", async () => {
    const user = userEvent.setup();

    renderShell();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Sign out" })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Sign out" }));

    await waitFor(() => {
      expect(authApi.bffLogout).toHaveBeenCalledTimes(1);
    });
    await waitFor(() => {
      expect(screen.getByRole("heading", { level: 1, name: "Login" })).toBeInTheDocument();
    });
  });
});
