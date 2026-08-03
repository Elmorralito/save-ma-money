import type { CategoryTypeSlug } from "@/lib/categoryTypes";
import type { CategoryCreate, CategoryResponse, CategoryUpdate } from "@/types/domain";

export type CategoryFormState = {
  name: string;
  description: string;
  category_type: CategoryTypeSlug;
  parent_id: string;
  icon: string;
  color: string;
  is_active: boolean;
};

export function emptyCategoryFormState(
  overrides: Partial<CategoryFormState> = {},
): CategoryFormState {
  return {
    name: "",
    description: "",
    category_type: "expense",
    parent_id: "",
    icon: "",
    color: "",
    is_active: true,
    ...overrides,
  };
}

export function categoryFormFromResponse(category: CategoryResponse): CategoryFormState {
  return emptyCategoryFormState({
    name: category.name,
    description: "",
    category_type: category.category_type as CategoryTypeSlug,
    parent_id: category.parent_id ?? "",
    icon: category.icon ?? "",
    color: category.color ?? "",
    is_active: category.is_active,
  });
}

export function toCategoryCreate(state: CategoryFormState): CategoryCreate {
  return {
    name: state.name.trim(),
    description: state.description,
    category_type: state.category_type,
    parent_id: state.parent_id.trim() || null,
    icon: state.icon.trim() || null,
    color: state.color.trim() || null,
  };
}

export function toCategoryUpdate(state: CategoryFormState): CategoryUpdate {
  // Omit empty description — CategoryResponse does not round-trip it.
  const update: CategoryUpdate = {
    name: state.name.trim(),
    category_type: state.category_type,
    parent_id: state.parent_id.trim() || null,
    icon: state.icon.trim() || null,
    color: state.color.trim() || null,
    is_active: state.is_active,
  };
  if (state.description.trim() !== "") {
    update.description = state.description;
  }
  return update;
}
