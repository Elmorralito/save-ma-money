/**
 * Playwright globalSetup (PPT-056 / #121).
 *
 * Invokes the PPT-061 seed SSOT only — do not invent a second SQL seed.
 * Requires a healthy Compose API (`make api-all`).
 */
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const e2eDir = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(e2eDir, "..");
const repoRoot = path.resolve(webRoot, "../..");

const MAX_ATTEMPTS = 3;

export default function globalSetup(): void {
  let lastError: unknown;
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    try {
      console.log(
        `[e2e] seeding fixtures via make web-e2e-seed (attempt ${attempt}/${MAX_ATTEMPTS}, cwd=${repoRoot})`,
      );
      execFileSync("make", ["web-e2e-seed"], {
        cwd: repoRoot,
        stdio: "inherit",
        env: process.env,
      });
      return;
    } catch (error) {
      lastError = error;
      if (attempt < MAX_ATTEMPTS) {
        // Supabase/local Auth can briefly 401 under burst login from prior e2e runs.
        Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 2000 * attempt);
      }
    }
  }
  throw lastError;
}
