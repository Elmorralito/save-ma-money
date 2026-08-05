import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { PapitaApiError } from "@/api/errors";
import * as categoriesApi from "@/api/categories";
import { CategoriesPage } from "@/pages/CategoriesPage";
import { QueryTestProvider } from "@/test/queryWrapper";

vi.mock("@/api/categories", () => ({
  listCategories: vi.fn(),
  getCategory: vi.fn(),
  createCategory: vi.fn(),
  updateCategory: vi.fn(),
  deleteCategory: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const emptyDiscovery = {
  breakingChanges: null,
  bulkMax: null,
  reportWindowMaxDays: null,
  cashFlowRefreshDefault: null,
  reportsForeignAccountStatus: null,
  errorCode: null,
  compatActive: [] as string[],
};

describe("CategoriesPage", () => {
  it("shows empty state when the API returns no items", async () => {
    vi.mocked(categoriesApi.listCategories).mockResolvedValue({
      items: [],
      limit: 100,
      skip: 0,
      total: 0,
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <CategoriesPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("No categories yet")).toBeInTheDocument();
    });
  });

  it("creates a category through the dialog", async () => {
    const user = userEvent.setup();
    vi.mocked(categoriesApi.listCategories)
      .mockResolvedValueOnce({ items: [], limit: 100, skip: 0, total: 0 })
      .mockResolvedValueOnce({
        items: [
          {
            id: "33333333-3333-3333-3333-333333333333",
            name: "Coffee",
            category_type: "expense",
            is_active: true,
            subcategories: [],
          },
        ],
        limit: 100,
        skip: 0,
        total: 1,
      });
    vi.mocked(categoriesApi.createCategory).mockResolvedValue({
      id: "33333333-3333-3333-3333-333333333333",
      name: "Coffee",
      category_type: "expense",
      is_active: true,
      subcategories: [],
    });

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <CategoriesPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("No categories yet")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "New category" }));
    await user.type(screen.getByLabelText("Name"), "Coffee");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(categoriesApi.createCategory).toHaveBeenCalled();
    });
    await waitFor(() => {
      expect(screen.getByText("Coffee")).toBeInTheDocument();
    });
  });

  it("lists categories and maps global delete 404 to read-only", async () => {
    const user = userEvent.setup();
    const seedId = "22222222-2222-2222-2222-222222222222";

    vi.mocked(categoriesApi.listCategories).mockResolvedValue({
      items: [
        {
          id: seedId,
          name: "Groceries",
          category_type: "expense",
          is_active: true,
          subcategories: [],
        },
      ],
      limit: 100,
      skip: 0,
      total: 1,
    });
    vi.mocked(categoriesApi.deleteCategory).mockRejectedValue(
      new PapitaApiError({
        message: "Category not found",
        status: 404,
        discovery: emptyDiscovery,
      }),
    );

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <CategoriesPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Groceries")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Delete" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Delete" }));

    await waitFor(() => {
      expect(screen.getByText("(read-only)")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Edit" })).toBeDisabled();
  });

  it("maps global edit 404 to read-only", async () => {
    const user = userEvent.setup();
    const seedId = "22222222-2222-2222-2222-222222222222";

    vi.mocked(categoriesApi.listCategories).mockResolvedValue({
      items: [
        {
          id: seedId,
          name: "Groceries",
          category_type: "expense",
          is_active: true,
          subcategories: [],
        },
      ],
      limit: 100,
      skip: 0,
      total: 1,
    });
    vi.mocked(categoriesApi.updateCategory).mockRejectedValue(
      new PapitaApiError({
        message: "Category not found",
        status: 404,
        discovery: emptyDiscovery,
      }),
    );

    render(
      <QueryTestProvider>
        <MemoryRouter>
          <CategoriesPage />
        </MemoryRouter>
      </QueryTestProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Groceries")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Edit" }));
    const dialog = await screen.findByRole("dialog");
    await user.clear(within(dialog).getByLabelText("Name"));
    await user.type(within(dialog).getByLabelText("Name"), "Food");
    await user.click(within(dialog).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(within(dialog).getByRole("alert")).toHaveTextContent(/cannot be modified/i);
    });
    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
    await waitFor(() => {
      expect(screen.getByText("(read-only)")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Edit" })).toBeDisabled();
  });
});
