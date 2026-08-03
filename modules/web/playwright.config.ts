import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig, devices } from "@playwright/test";

const webRoot = path.dirname(fileURLToPath(import.meta.url));
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:5173";

/**
 * Playwright config for PPT-056 / #121.
 *
 * Prerequisites: `make api-all` (Compose API). globalSetup runs `make web-e2e-seed`
 * (PPT-061 / #126). Vite is started via webServer for local/CI convenience.
 */
export default defineConfig({
  testDir: path.join(webRoot, "e2e"),
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  globalSetup: path.join(webRoot, "e2e", "global-setup.ts"),
  timeout: 90_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "pnpm exec vite --host 127.0.0.1 --port 5173",
    cwd: webRoot,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
