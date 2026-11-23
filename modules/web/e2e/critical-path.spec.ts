import { expect, test } from "@playwright/test";

import { loadSeed } from "./fixtures";
import { assertNoJwtInWebStorage, loginWithSeed } from "./helpers/auth";

/**
 * Critical BFF cookie journey (PPT-056 / #121).
 *
 * Auth assumptions (PPT-060 / #125): confirmed (or confirm-N/A) user.
 * Fixture SSOT (PPT-061 / #126): seed via globalSetup → `make web-e2e-seed`.
 * SPA path starts at BFF login (seed already registered via Bearer API).
 */
test.describe("critical path", () => {
  test("login → create account → expense → transfer → spending report", async ({ page }) => {
    const seed = loadSeed();
    const stamp = Date.now().toString(36);
    const newAccountName = `E2E UI Acct ${stamp}`;
    const expenseDesc = `E2E UI expense ${stamp}`;
    const transferDesc = `E2E UI transfer ${stamp}`;
    const today = new Date().toISOString().slice(0, 10);

    await loginWithSeed(page, seed);
    await assertNoJwtInWebStorage(page);

    // Automation-first Home (PPT-088 / #181): Financial Health Scorecard + Live Pulse
    const scorecard = page.locator('section[aria-label="Financial Health Scorecard"]');
    await expect(
      scorecard.getByRole("heading", { name: "Financial Health Scorecard" }),
    ).toBeVisible({
      timeout: 15_000,
    });
    await expect(scorecard.getByText("Reconciled Net Worth")).toBeVisible({ timeout: 15_000 });
    await expect(scorecard.getByText("Liquid Cash Runway")).toBeVisible();
    await expect(scorecard.getByText("Monthly Debt Service")).toBeVisible();
    await expect(scorecard.getByText("Debt-to-Asset / LTV")).toBeVisible();

    const ingestion = page.locator('section[aria-label="Ingestion status"]');
    await expect(ingestion.getByRole("heading", { name: "Ingestion status" })).toBeVisible();
    await expect(ingestion.getByText("Loading ingestion status…")).toHaveCount(0, {
      timeout: 15_000,
    });
    await expect(ingestion.getByText(/Could not load ingestion status/i)).toHaveCount(0);

    const operatingFcf = page.locator('section[aria-label="Operating Free Cashflow"]');
    await expect(operatingFcf.getByText(/Monthly Operating FCF/i)).toBeVisible({
      timeout: 15_000,
    });

    await expect(
      page.locator('section[aria-label="In-transit transfers"]').getByRole("heading", {
        name: "In-transit transfers",
      }),
    ).toBeVisible();
    await expect(
      page.locator('section[aria-label="Due soon"]').getByRole("heading", { name: "Due soon" }),
    ).toBeVisible();

    // Automation-first Home (PPT-088 / #181): Financial Health Scorecard + Live Pulse
    const scorecard = page.locator('section[aria-label="Financial Health Scorecard"]');
    await expect(scorecard.getByRole("heading", { name: "Financial Health Scorecard" })).toBeVisible({
      timeout: 15_000,
    });
    await expect(scorecard.getByText("Reconciled Net Worth")).toBeVisible({ timeout: 15_000 });
    await expect(scorecard.getByText("Liquid Cash Runway")).toBeVisible();
    await expect(scorecard.getByText("Monthly Debt Service")).toBeVisible();
    await expect(scorecard.getByText("Debt-to-Asset / LTV")).toBeVisible();

    const ingestion = page.locator('section[aria-label="Ingestion status"]');
    await expect(ingestion.getByRole("heading", { name: "Ingestion status" })).toBeVisible();
    await expect(ingestion.getByText("Loading ingestion status…")).toHaveCount(0, {
      timeout: 15_000,
    });
    await expect(ingestion.getByText(/Could not load ingestion status/i)).toHaveCount(0);

    const operatingFcf = page.locator('section[aria-label="Operating Free Cashflow"]');
    await expect(operatingFcf.getByText(/Monthly Operating FCF/i)).toBeVisible({
      timeout: 15_000,
    });

    await expect(
      page.locator('section[aria-label="In-transit transfers"]').getByRole("heading", {
        name: "In-transit transfers",
      }),
    ).toBeVisible();
    await expect(
      page.locator('section[aria-label="Due soon"]').getByRole("heading", { name: "Due soon" }),
    ).toBeVisible();

    // Create account (exact: avoid dashboard quick-link cards matching nav labels)
    await page.getByRole("link", { name: "Accounts", exact: true }).click();
    await page.getByRole("heading", { name: "Accounts" }).waitFor();
    await page.getByRole("button", { name: "New account" }).click();
    const accountDialog = page.getByRole("dialog");
    await expect(accountDialog.getByRole("heading", { name: "Create account" })).toBeVisible();
    await accountDialog.locator("#acct-create-name").fill(newAccountName);
    await accountDialog.locator("#acct-create-entity").fill("E2E Bank");
    await accountDialog.locator("#acct-create-initial").fill("0");
    await accountDialog.getByRole("button", { name: "Save" }).click();
    await expect(page.getByRole("link", { name: newAccountName })).toBeVisible({ timeout: 15_000 });

    // Create expense (seed category + new account)
    await page.getByRole("link", { name: "Transactions", exact: true }).click();
    await page.getByRole("heading", { name: "Transactions" }).waitFor();
    await page.getByRole("button", { name: "New transaction" }).click();
    const txnDialog = page.getByRole("dialog");
    await expect(txnDialog.getByRole("heading", { name: "Create transaction" })).toBeVisible();
    await txnDialog.locator("#txn-create-date").fill(today);
    await txnDialog.locator("#txn-create-account").selectOption({ label: newAccountName });
    await txnDialog
      .locator("#txn-create-category")
      .selectOption({ label: seed.categoryNames.expense });
    await txnDialog.locator("#txn-create-amount").fill("12.34");
    await txnDialog.locator("#txn-create-description").fill(expenseDesc);
    await txnDialog.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText(expenseDesc)).toBeVisible({ timeout: 15_000 });

    // Transfer between seed accounts (unified Transactions ledger, PPT-099)
    await page.getByRole("button", { name: "New transaction" }).click();
    const transferDialog = page.getByRole("dialog");
    await expect(transferDialog.getByRole("heading", { name: "Create transaction" })).toBeVisible();
    await transferDialog.locator("#txn-create-type").selectOption("transfer");
    await transferDialog.locator("#txn-create-date").fill(today);
    await transferDialog
      .locator("#txn-create-source-account")
      .selectOption({ label: seed.accountNames.checking });
    await transferDialog
      .locator("#txn-create-dest-account")
      .selectOption({ label: seed.accountNames.savings });
    await transferDialog.locator("#txn-create-amount").fill("5.00");
    await transferDialog.locator("#txn-create-description").fill(transferDesc);
    await transferDialog.getByRole("button", { name: "Save" }).click();
    await page.locator("#txn-filter-type").selectOption("transfer");
    await expect(page.getByText(transferDesc)).toBeVisible({ timeout: 15_000 });

    // Operating cashflow waterfall renders on Reports by default, then switch to Spending.
    // Local Compose may 429 under burst traffic — CI disables API rate limits.
    await page.getByRole("link", { name: "Reports", exact: true }).click();
    await page.getByRole("heading", { name: "Reports" }).waitFor();
    await page.locator("#report-start-date").fill("2026-01-01");
    await page.locator("#report-end-date").fill(today);
    await page.getByRole("button", { name: "Run report" }).click();
    await expect(page.getByRole("heading", { name: "Cashflow Waterfall" })).toBeVisible({
      timeout: 15_000,
    });

    await page.getByRole("tab", { name: "Spending" }).click();
    const spending = page.locator('section[aria-label="Spending report"]');
    let reportReady = false;
    for (let attempt = 0; attempt < 6; attempt += 1) {
      await page.getByRole("button", { name: "Run report" }).click();
      await expect(spending.getByRole("heading", { name: "Spending" })).toBeVisible({
        timeout: 15_000,
      });
      if (
        await spending
          .getByText("Total spending")
          .isVisible()
          .catch(() => false)
      ) {
        reportReady = true;
        break;
      }
      const alert = spending.getByRole("alert");
      if (await alert.isVisible().catch(() => false)) {
        const detail = (await alert.textContent()) ?? "";
        if (/rate limit/i.test(detail)) {
          await page.waitForTimeout(5_000);
          const retry = spending.getByRole("button", { name: "Retry" });
          if (await retry.isVisible().catch(() => false)) {
            await retry.click();
          }
          continue;
        }
        throw new Error(`Spending report failed: ${detail}`);
      }
      await page.waitForTimeout(1_000);
    }
    expect(reportReady, "Spending report did not load after retries").toBe(true);
    // API spending breakdown keys categories by id (name resolution is presentation-follow-on).
    await expect(spending.getByText(seed.categoryIds.expense)).toBeVisible();
    await expect(spending.getByText("Total spending")).toBeVisible();
    await expect(spending.getByText(expenseDesc)).toHaveCount(0); // aggregates only
    await expect(spending.locator("tbody tr").first()).toBeVisible();

    await assertNoJwtInWebStorage(page);
  });
});
