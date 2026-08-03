import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { toast } from "sonner";

import { isPapitaApiError } from "@/api/errors";
import { mapServerErrors, shouldToastMutationError } from "@/forms/mapServerErrors";
import { formatApiError } from "@/lib/formatApiError";

type ApplyMutationErrorOptions<TFieldValues extends FieldValues> = {
  setError: UseFormSetError<TFieldValues>;
  /** OpenAPI body path → form field name (flat RHF keys). */
  fieldMap?: Record<string, string>;
  /** Override toast decision; default uses {@link shouldToastMutationError}. */
  toast?: boolean;
};

/**
 * Apply a mutation failure to RHF + toast per PPT-055 policy:
 *
 * - 422 with mappable field locs → inline ``setError`` only
 * - 429 / network / 5xx → toast (+ root form error)
 * - other errors → toast + root
 */
export function applyMutationError<TFieldValues extends FieldValues>(
  error: unknown,
  options: ApplyMutationErrorOptions<TFieldValues>,
): void {
  const summary = formatApiError(error);
  const mapped = mapServerErrors(error, options.fieldMap ?? {});
  const isField422 = isPapitaApiError(error) && error.status === 422 && mapped.fields.length > 0;

  if (isField422) {
    for (const field of mapped.fields) {
      options.setError(field.name as Path<TFieldValues>, {
        type: "server",
        message: field.message,
      });
    }
    if (mapped.root) {
      options.setError("root" as Path<TFieldValues>, {
        type: "server",
        message: mapped.root,
      });
    }
    return;
  }

  const useToast = options.toast ?? shouldToastMutationError(error);
  if (useToast) {
    toast.error(summary);
  }

  options.setError("root" as Path<TFieldValues>, {
    type: "server",
    message: summary,
  });
}
