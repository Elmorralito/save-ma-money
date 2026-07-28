/**
 * Thin re-exports of OpenAPI schema component types.
 *
 * Domain business rules stay in ``papita_txnsmodel`` / ``papita_txnsapi``.
 * Prefer these aliases over hand-rolled DTO shapes (PPT-048 / #114).
 */
import type { components } from "./api";

/** OpenAPI ``components.schemas`` map from the committed artifact. */
export type ApiSchemas = components["schemas"];
