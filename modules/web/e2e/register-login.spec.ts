import { expect, test } from "@playwright/test";

import { assertNoJwtInWebStorage } from "./helpers/auth";

/**
 * Optional live register → login when the IdP allows unconfirmed-free signup
 * (AUTH_PROVIDER=local, or Supabase Confirm email OFF / Admin auto-confirm).
 *
 * Skipped unless E2E_LIVE_REGISTER=1 — default CI critical path uses seed login
 * (PPT-060 / #125 + PPT-061 / #126).
 */
test.describe("live register → login", () => {
  test.skip(
    process.env.E2E_LIVE_REGISTER !== "1",
    "Set E2E_LIVE_REGISTER=1 to exercise SPA register against a confirm-N/A IdP",
  );

  test("register then sign in via BFF cookies", async ({ page }) => {
    const stamp = Date.now().toString(36);
    const email = `e2e.live.${stamp}@example.local`;
    const password = "SecurePass1!";

    await page.goto("/register");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Display name").fill(`E2E Live ${stamp}`);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByLabel("Confirm password").fill(password);
    await page.getByRole("button", { name: "Register" }).click();
    await page.waitForURL(/\/login/);
    await expect(page.getByRole("status")).toContainText("Account created");

    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.waitForURL(/\/(dashboard)?$/);
    await expect(page.getByRole("heading", { name: /^(Dashboard|Welcome back,)/ })).toBeVisible();
    await assertNoJwtInWebStorage(page);
  });
});
