type BreakingChangesBannerProps = {
  expected: string;
  observed: string;
};

/** Non-blocking banner when SPA expected breaking-changes id drifts from the API. */
export function BreakingChangesBanner({ expected, observed }: BreakingChangesBannerProps) {
  return (
    <div
      role="alert"
      className="border-b border-destructive/40 bg-destructive/10 px-4 py-2 text-sm text-destructive"
    >
      API contract drift: expected breaking-changes id <code className="font-mono">{expected}</code>
      , API reports <code className="font-mono">{observed}</code>. Update the SPA or{" "}
      <code className="font-mono">VITE_PAPITA_BREAKING_CHANGES_ID</code>.
    </div>
  );
}
