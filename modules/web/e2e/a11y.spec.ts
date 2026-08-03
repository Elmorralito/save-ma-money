import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { loadSeed } from "./fixtures";
import { loginWithSeed } from "./helpers/auth";

/** Core MVP routes for WCAG 2.1 AA intent (PPT-056). */
const AUTHED_ROUTES = [
  "/dashboard",
  "/accounts",
  "/categories",
  "/transactions",
  "/movements",
  "/reports",
] as const;

async function expectNoCriticalAxeViolations(page: Page, route: string): Promise<void> {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  const blocking = results.violations.filter(
    (v) => v.impact === "critical" || v.impact === "serious",
  );
  expect(
    blocking,
    `axe critical/serious on ${route}: ${JSON.stringify(blocking, null, 2)}`,
  ).toEqual([]);
}

test.describe("axe a11y (MVP routes)", () => {
  test("public auth routes have no critical/serious violations", async ({ page }) => {
    for (const route of ["/login", "/register"] as const) {
      await page.goto(route);
      await page.getByRole("heading").first().waitFor();
      await expectNoCriticalAxeViolations(page, route);
    }
  });

  test("authenticated MVP routes have no critical/serious violations", async ({ page }) => {
    const seed = loadSeed();
    await loginWithSeed(page, seed);

    for (const route of AUTHED_ROUTES) {
      await page.goto(route);
      await page.getByRole("heading").first().waitFor();
      await expectNoCriticalAxeViolations(page, route);
    }
  });
});
