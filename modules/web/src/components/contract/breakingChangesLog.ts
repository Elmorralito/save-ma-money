import type { BreakingChangesGuardResult } from "@/api/contract";

const loggedMismatchKeys = new Set<string>();

/** Log a breaking-changes mismatch once per expected|observed pair (dev error / prod warn). */
export function logBreakingChangesMismatch(result: BreakingChangesGuardResult): void {
  if (result.status !== "mismatch" || result.observed === null) {
    return;
  }
  const key = `${result.expected}|${result.observed}`;
  if (loggedMismatchKeys.has(key)) {
    return;
  }
  loggedMismatchKeys.add(key);
  const message =
    `Papita API breaking-changes id mismatch: expected "${result.expected}", ` +
    `observed "${result.observed}". Sync the SPA / VITE_PAPITA_BREAKING_CHANGES_ID with ` +
    `GET /api/v1/meta/client-contract.`;
  if (import.meta.env.DEV) {
    console.error(message);
  } else {
    console.warn(message);
  }
}

/** Test helper to clear once-per-session log dedupe. */
export function resetBreakingChangesMismatchLogForTests(): void {
  loggedMismatchKeys.clear();
}
