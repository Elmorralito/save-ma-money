import { afterEach, describe, expect, it } from "vitest";

import { clearCsrfToken, getCsrfToken, setCsrfToken } from "@/api/csrf";

function webStorageBlob(): string {
  return `${JSON.stringify(window.localStorage)}${JSON.stringify(window.sessionStorage)}`;
}

describe("csrf token store (PPT-056 security)", () => {
  afterEach(() => {
    clearCsrfToken();
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("keeps the CSRF token in memory only — never WebStorage", () => {
    setCsrfToken("csrf-test-token");
    expect(getCsrfToken()).toBe("csrf-test-token");
    expect(window.localStorage.length).toBe(0);
    expect(window.sessionStorage.length).toBe(0);
    expect(webStorageBlob()).not.toContain("csrf-test-token");
  });

  it("clears the in-memory token on logout-style reset", () => {
    setCsrfToken("csrf-test-token");
    clearCsrfToken();
    expect(getCsrfToken()).toBeNull();
  });
});
