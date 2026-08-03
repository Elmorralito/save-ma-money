import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as metaApi from "@/api/meta";
import { resetBreakingChangesMismatchLogForTests } from "@/components/contract/breakingChangesLog";
import { BreakingChangesGuard } from "@/components/contract/BreakingChangesGuard";
import { QueryTestProvider } from "@/test/queryWrapper";
import type { ClientContract } from "@/types/domain";

vi.mock("@/api/meta", () => ({
  getClientContract: vi.fn(),
}));

const baseContract = {
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
} satisfies ClientContract;

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  resetBreakingChangesMismatchLogForTests();
});

beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => undefined);
  vi.spyOn(console, "warn").mockImplementation(() => undefined);
});

describe("BreakingChangesGuard", () => {
  it("renders no banner when contract matches expected id", async () => {
    vi.mocked(metaApi.getClientContract).mockResolvedValue({
      contract: baseContract,
      discovery: {
        breakingChanges: "ppt-044",
        bulkMax: 100,
        reportWindowMaxDays: 366,
        cashFlowRefreshDefault: false,
        reportsForeignAccountStatus: 404,
        errorCode: null,
        compatActive: [],
      },
    });

    render(
      <QueryTestProvider>
        <BreakingChangesGuard />
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(metaApi.getClientContract).toHaveBeenCalled();
    });
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("renders banner and logs on mismatch", async () => {
    vi.mocked(metaApi.getClientContract).mockResolvedValue({
      contract: { ...baseContract, breaking_changes: "ppt-099" },
      discovery: {
        breakingChanges: "ppt-099",
        bulkMax: 100,
        reportWindowMaxDays: 366,
        cashFlowRefreshDefault: false,
        reportsForeignAccountStatus: 404,
        errorCode: null,
        compatActive: [],
      },
    });

    render(
      <QueryTestProvider>
        <BreakingChangesGuard />
      </QueryTestProvider>,
    );

    expect(await screen.findByRole("alert")).toHaveTextContent("ppt-099");
    await waitFor(() => {
      expect(console.error).toHaveBeenCalled();
    });
  });
});
