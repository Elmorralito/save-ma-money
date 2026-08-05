/** Format remaining seconds as a compact countdown (e.g. ``12m 05s``). */
export function formatRemainingDuration(totalSeconds: number): string {
  if (!Number.isFinite(totalSeconds) || totalSeconds <= 0) {
    return "expired";
  }
  const whole = Math.floor(totalSeconds);
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const seconds = whole % 60;
  if (hours > 0) {
    return `${String(hours)}h ${String(minutes).padStart(2, "0")}m ${String(seconds).padStart(2, "0")}s`;
  }
  if (minutes > 0) {
    return `${String(minutes)}m ${String(seconds).padStart(2, "0")}s`;
  }
  return `${String(seconds)}s`;
}

/** Seconds remaining until a Unix expiry timestamp (clamped at 0). */
export function secondsUntil(expiresAtUnix: number, nowMs: number = Date.now()): number {
  if (!Number.isFinite(expiresAtUnix)) {
    return 0;
  }
  return Math.max(0, Math.floor(expiresAtUnix - nowMs / 1000));
}
