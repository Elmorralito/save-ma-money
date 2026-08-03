import { apiFetch } from "@/api/http";
import type {
  CategoryCreate,
  CategoryResponse,
  CategoryUpdate,
  PaginatedCategories,
} from "@/types/domain";

const CATEGORIES_PATH = "/api/v1/categories";

export type ListCategoriesParams = {
  parent_id?: string;
  category_type?: string;
  skip?: number;
  limit?: number;
  signal?: AbortSignal;
};

function buildListQuery(params: ListCategoriesParams): string {
  const search = new URLSearchParams();
  if (params.parent_id) {
    search.set("parent_id", params.parent_id);
  }
  if (params.category_type) {
    search.set("category_type", params.category_type);
  }
  if (params.skip !== undefined) {
    search.set("skip", String(params.skip));
  }
  if (params.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  const qs = search.toString();
  return qs === "" ? CATEGORIES_PATH : `${CATEGORIES_PATH}?${qs}`;
}

/** ``GET /api/v1/categories`` — tenant + global seed categories. */
export async function listCategories(
  params: ListCategoriesParams = {},
): Promise<PaginatedCategories> {
  const { signal, ...filters } = params;
  const result = await apiFetch<PaginatedCategories>(buildListQuery(filters), { signal });
  return result.data;
}

/** ``GET /api/v1/categories/{category_id}``. */
export async function getCategory(
  categoryId: string,
  signal?: AbortSignal,
): Promise<CategoryResponse> {
  const result = await apiFetch<CategoryResponse>(`${CATEGORIES_PATH}/${categoryId}`, { signal });
  return result.data;
}

/** ``POST /api/v1/categories``. */
export async function createCategory(
  body: CategoryCreate,
  signal?: AbortSignal,
): Promise<CategoryResponse> {
  const result = await apiFetch<CategoryResponse>(CATEGORIES_PATH, {
    method: "POST",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return result.data;
}

/** ``PUT /api/v1/categories/{category_id}``. */
export async function updateCategory(
  categoryId: string,
  body: CategoryUpdate,
  signal?: AbortSignal,
): Promise<CategoryResponse> {
  const result = await apiFetch<CategoryResponse>(`${CATEGORIES_PATH}/${categoryId}`, {
    method: "PUT",
    signal,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return result.data;
}

/** ``DELETE /api/v1/categories/{category_id}`` — soft-delete (204). */
export async function deleteCategory(categoryId: string, signal?: AbortSignal): Promise<void> {
  await apiFetch<undefined>(`${CATEGORIES_PATH}/${categoryId}`, {
    method: "DELETE",
    signal,
  });
}
