import { z } from "zod";

import { CATEGORY_TYPE_SLUGS } from "@/lib/categoryTypes";

/** UX schema for {@link CategoryFormState} — OpenAPI-aligned shape checks only. */
export const categoryFormSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(255),
  description: z.string(),
  category_type: z.enum(CATEGORY_TYPE_SLUGS),
  parent_id: z.string(),
  icon: z.string().max(64, "Icon must be at most 64 characters"),
  color: z
    .string()
    .max(7, "Color must be at most 7 characters")
    .refine((value) => value.trim() === "" || /^#[0-9A-Fa-f]{6}$/.test(value.trim()), {
      message: "Color must be #RRGGBB",
    }),
  is_active: z.boolean(),
});

export type CategoryFormSchema = z.infer<typeof categoryFormSchema>;
