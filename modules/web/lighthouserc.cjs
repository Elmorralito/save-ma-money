/**
 * Lighthouse CI budgets (PPT-056 / #121) — lab Core Web Vitals + a11y/perf scores.
 *
 * Run against a production build preview after `pnpm web:build`:
 *   pnpm --filter @papita/web lhci
 *
 * Lab budgets (issue AC): a11y ≥ 0.95; perf ≥ 0.9; LCP ≤ 2.5s; INP ≤ 200ms; CLS ≤ 0.1.
 * Note: Lighthouse lab reports TBT as the interactive latency proxy; INP is field-only
 * in many LH versions — see modules/web/README.md § Quality / CWV for the waiver note.
 */
module.exports = {
  ci: {
    collect: {
      startServerCommand: "pnpm exec vite preview --host 127.0.0.1 --port 4173",
      startServerReadyPattern: "Local:",
      url: ["http://127.0.0.1:4173/login"],
      numberOfRuns: 1,
      settings: {
        preset: "desktop",
      },
    },
    assert: {
      assertions: {
        "categories:accessibility": ["error", { minScore: 0.95 }],
        "categories:performance": ["warn", { minScore: 0.9 }],
        "largest-contentful-paint": ["warn", { maxNumericValue: 2500 }],
        "cumulative-layout-shift": ["error", { maxNumericValue: 0.1 }],
        "total-blocking-time": ["warn", { maxNumericValue: 200 }],
      },
    },
    upload: {
      target: "filesystem",
      outputDir: ".lighthouseci",
    },
  },
};
