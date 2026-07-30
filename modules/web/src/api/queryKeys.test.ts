import { describe, expect, it } from "vitest";

import { queryKeys } from "@/api/queryKeys";

describe("queryKeys", () => {
  it("keeps hierarchical prefixes stable", () => {
    expect(queryKeys.all).toEqual(["papita"]);
    expect(queryKeys.auth.all).toEqual(["papita", "auth"]);
    expect(queryKeys.meta.all).toEqual(["papita", "meta"]);
    expect(queryKeys.health.all).toEqual(["papita", "health"]);
  });

  it("builds distinct leaf keys for meta, health, and auth probes", () => {
    expect(queryKeys.meta.clientContract()).toEqual(["papita", "meta", "client-contract"]);
    expect(queryKeys.health.root()).toEqual(["papita", "health", "root"]);
    expect(queryKeys.health.live()).toEqual(["papita", "health", "live"]);
    expect(queryKeys.auth.session()).toEqual(["papita", "auth", "session"]);
    expect(queryKeys.meta.clientContract()).not.toEqual(queryKeys.health.root());
  });
});
