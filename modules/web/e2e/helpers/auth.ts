import type { Page } from "@playwright/test";

import type { E2ESeed } from "../fixtures";

/** Sign in through the SPA BFF cookie path (PPT-049 / PPT-060 confirmed-user assumption). */
export async function loginWithSeed(page: Page, seed: E2ESeed): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(seed.email);
  await page.getByLabel("Password", { exact: true }).fill(seed.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/(dashboard)?$/);
  // Dashboard h1 is "Welcome back, …" once session user loads; "Dashboard" only while pending.
  await page.getByRole("heading", { name: /^(Dashboard|Welcome back,)/ }).waitFor();
}

/** Assert no JWT-shaped values leaked into WebStorage after auth. */
export async function assertNoJwtInWebStorage(page: Page): Promise<void> {
  const leak = await page.evaluate(() => {
    const blob = `${JSON.stringify(localStorage)}${JSON.stringify(sessionStorage)}`;
    const jwtLike = /eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/;
    return jwtLike.test(blob) ? blob : null;
  });
  if (leak) {
    throw new Error(`JWT-like value found in WebStorage: ${leak.slice(0, 120)}`);
  }
}
