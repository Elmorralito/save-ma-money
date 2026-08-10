import { describe, expect, it } from "vitest";

import { queryKeys } from "@/api/queryKeys";

describe("queryKeys", () => {
  it("keeps hierarchical prefixes stable", () => {
    expect(queryKeys.all).toEqual(["papita"]);
    expect(queryKeys.auth.all).toEqual(["papita", "auth"]);
    expect(queryKeys.meta.all).toEqual(["papita", "meta"]);
    expect(queryKeys.health.all).toEqual(["papita", "health"]);
    expect(queryKeys.accounts.all).toEqual(["papita", "accounts"]);
    expect(queryKeys.categories.all).toEqual(["papita", "categories"]);
    expect(queryKeys.transactions.all).toEqual(["papita", "transactions"]);
    expect(queryKeys.movements.all).toEqual(["papita", "movements"]);
    expect(queryKeys.reports.all).toEqual(["papita", "reports"]);
    expect(queryKeys.transactionTemplates.all).toEqual(["papita", "transactionTemplates"]);
  });

  it("builds distinct leaf keys for meta, health, auth, and feature resources", () => {
    expect(queryKeys.meta.clientContract()).toEqual(["papita", "meta", "client-contract"]);
    expect(queryKeys.health.root()).toEqual(["papita", "health", "root"]);
    expect(queryKeys.health.live()).toEqual(["papita", "health", "live"]);
    expect(queryKeys.auth.session()).toEqual(["papita", "auth", "session"]);
    expect(queryKeys.accounts.list({ limit: 100 })).toEqual([
      "papita",
      "accounts",
      "list",
      { limit: 100 },
    ]);
    expect(queryKeys.accounts.detail("abc")).toEqual(["papita", "accounts", "detail", "abc"]);
    expect(queryKeys.categories.list({ skip: 0 })).toEqual([
      "papita",
      "categories",
      "list",
      { skip: 0 },
    ]);
    expect(queryKeys.transactions.list({ limit: 100 })).toEqual([
      "papita",
      "transactions",
      "list",
      { limit: 100 },
    ]);
    expect(queryKeys.transactions.detail("txn-1")).toEqual([
      "papita",
      "transactions",
      "detail",
      "txn-1",
    ]);
    expect(queryKeys.movements.list({ status: "pending" })).toEqual([
      "papita",
      "movements",
      "list",
      { status: "pending" },
    ]);
    expect(queryKeys.movements.detail("mov-1")).toEqual(["papita", "movements", "detail", "mov-1"]);
    expect(queryKeys.meta.clientContract()).not.toEqual(queryKeys.health.root());
    expect(
      queryKeys.reports.spending({ start_date: "2026-01-01", end_date: "2026-01-31" }),
    ).toEqual([
      "papita",
      "reports",
      "spending",
      { start_date: "2026-01-01", end_date: "2026-01-31" },
    ]);
    expect(queryKeys.transactionTemplates.list({ limit: 100 })).toEqual([
      "papita",
      "transactionTemplates",
      "list",
      { limit: 100 },
    ]);
    expect(queryKeys.transactionTemplates.detail("tmpl-1")).toEqual([
      "papita",
      "transactionTemplates",
      "detail",
      "tmpl-1",
    ]);
    expect(queryKeys.transactionTemplates.upcomingDues({ window_days: 14 })).toEqual([
      "papita",
      "transactionTemplates",
      "upcomingDues",
      { window_days: 14 },
    ]);
  });
});
