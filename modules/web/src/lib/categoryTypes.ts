/** API ``category_type`` slugs (lowercase) for form selects. */
export const CATEGORY_TYPE_SLUGS = ["income", "expense"] as const;

export type CategoryTypeSlug = (typeof CATEGORY_TYPE_SLUGS)[number];
