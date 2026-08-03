import path from "node:path";
import { fileURLToPath } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const rootDir = path.dirname(fileURLToPath(import.meta.url));

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(rootDir, "src"),
    },
  },
  server: {
    // Same-origin `/api` in local dev — avoids CORS against papita_txnsapi (:8000).
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: true,
    // Playwright lives under e2e/ — keep Vitest on src unit/integration only.
    exclude: ["**/node_modules/**", "**/dist/**", "**/e2e/**"],
    // PPT-056: pragmatic ~70% on presentation src (exclude shadcn chrome + entry).
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov", "html"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/main.tsx",
        "src/types/**",
        "src/components/ui/**",
        "src/test/**",
        "src/pages/StubPage.tsx",
        // Heavy dialog shells are exercised via page tests + Playwright; keep the
        // Vitest gate on services/forms/lib + page orchestration (~70% pragmatic).
        "src/components/**/*FormDialog.tsx",
        "src/components/**/*FormFields.tsx",
        "src/components/transactions/BulkTransactionsDialog.tsx",
        "**/*.test.{ts,tsx}",
        "**/*.d.ts",
      ],
      // Pragmatic floor (PPT-056 ~70% intent). Dialog shells + StubPage excluded;
      // ledger page mutation branches are covered by Playwright critical path.
      thresholds: {
        lines: 65,
        functions: 60,
        branches: 55,
        statements: 65,
      },
    },
  },
});
