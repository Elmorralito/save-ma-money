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
  });
});
