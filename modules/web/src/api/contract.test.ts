import { describe, expect, it } from "vitest";

import {
  bulkMaxTransactions,
  DEFAULT_BREAKING_CHANGES_ID,
  evaluateBreakingChangesGuard,
  observedBreakingChangesId,
  reportWindowMaxDays,
  reportsForeignAccountStatus,
  resolveExpectedBreakingChangesId,
} from "@/api/contract";
import type { DiscoveryHeaders } from "@/api/headers";
import type { ClientContract } from "@/types/domain";

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
    bulk_max_transactions: 50,
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
} satisfies ClientContract;

const sampleDiscovery: DiscoveryHeaders = {
  breakingChanges: "ppt-044",
  bulkMax: 25,
  reportWindowMaxDays: 30,
  cashFlowRefreshDefault: false,
  reportsForeignAccountStatus: 400,
  errorCode: null,
  compatActive: [],
};

describe("contract helpers", () => {
  it("prefers effective body values over discovery headers", () => {
    expect(bulkMaxTransactions(sampleContract, sampleDiscovery)).toBe(50);
    expect(reportWindowMaxDays(sampleContract, sampleDiscovery)).toBe(90);
    expect(reportsForeignAccountStatus(sampleContract, sampleDiscovery)).toBe(404);
  });

  it("falls back to discovery headers when body is absent", () => {
    expect(bulkMaxTransactions(null, sampleDiscovery)).toBe(25);
    expect(reportWindowMaxDays(undefined, sampleDiscovery)).toBe(30);
    expect(reportsForeignAccountStatus(null, sampleDiscovery)).toBe(400);
  });

  it("returns null when neither body nor headers provide a value", () => {
    expect(bulkMaxTransactions(null, null)).toBeNull();
    expect(reportWindowMaxDays(null, null)).toBeNull();
  });
});

describe("breaking-changes guard", () => {
  it("defaults expected id to ppt-044 when env is unset or blank", () => {
    expect(resolveExpectedBreakingChangesId(undefined)).toBe(DEFAULT_BREAKING_CHANGES_ID);
    expect(resolveExpectedBreakingChangesId("")).toBe(DEFAULT_BREAKING_CHANGES_ID);
    expect(resolveExpectedBreakingChangesId("  ")).toBe(DEFAULT_BREAKING_CHANGES_ID);
  });

  it("trims a configured expected id", () => {
    expect(resolveExpectedBreakingChangesId(" ppt-099 ")).toBe("ppt-099");
  });

  it("prefers body breaking_changes over discovery header", () => {
    const discovery: DiscoveryHeaders = { ...sampleDiscovery, breakingChanges: "ppt-header" };
    expect(observedBreakingChangesId(sampleContract, discovery)).toBe("ppt-044");
  });

  it("falls back to discovery header when body is absent", () => {
    expect(observedBreakingChangesId(null, sampleDiscovery)).toBe("ppt-044");
  });

  it("returns unknown when neither body nor header provides an id", () => {
    expect(
      evaluateBreakingChangesGuard({ contract: null, discovery: null, expected: "ppt-044" }),
    ).toEqual({
      status: "unknown",
      expected: "ppt-044",
      observed: null,
    });
  });

  it("matches when expected equals observed body id", () => {
    expect(
      evaluateBreakingChangesGuard({
        contract: sampleContract,
        discovery: sampleDiscovery,
        expected: "ppt-044",
      }),
    ).toEqual({ status: "match", expected: "ppt-044", observed: "ppt-044" });
  });

  it("mismatches when expected differs from observed", () => {
    expect(
      evaluateBreakingChangesGuard({
        contract: sampleContract,
        discovery: sampleDiscovery,
        expected: "ppt-099",
      }),
    ).toEqual({ status: "mismatch", expected: "ppt-099", observed: "ppt-044" });
  });

  it("uses header when evaluating without a contract body", () => {
    expect(
      evaluateBreakingChangesGuard({
        contract: null,
        discovery: { ...sampleDiscovery, breakingChanges: "ppt-header" },
        expected: "ppt-044",
      }),
    ).toEqual({ status: "mismatch", expected: "ppt-044", observed: "ppt-header" });
  });
});
