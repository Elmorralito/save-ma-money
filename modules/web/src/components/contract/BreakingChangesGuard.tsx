import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { evaluateBreakingChangesGuard } from "@/api/contract";
import { clientContractQueryOptions } from "@/api/queries";
import { BreakingChangesBanner } from "@/components/contract/BreakingChangesBanner";
import { logBreakingChangesMismatch } from "@/components/contract/breakingChangesLog";

/**
 * Probe client-contract once at app root; surface PPT-064 mismatch via console + banner.
 *
 * Features should use {@link evaluateBreakingChangesGuard} — do not read discovery headers ad hoc.
 */
export function BreakingChangesGuard() {
  const contractQuery = useQuery(clientContractQueryOptions());
  const result = evaluateBreakingChangesGuard({ contract: contractQuery.data });
  const { status, expected, observed } = result;

  useEffect(() => {
    logBreakingChangesMismatch({ status, expected, observed });
  }, [status, expected, observed]);

  if (status !== "mismatch" || observed === null) {
    return null;
  }

  return <BreakingChangesBanner expected={expected} observed={observed} />;
}
