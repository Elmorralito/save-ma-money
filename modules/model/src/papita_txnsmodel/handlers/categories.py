# pylint: disable=access-member-before-definition
# mypy: disable-error-code="has-type"
"""
Categories Table Handler Module.

This module provides functionality for loading and processing category table data
in the Papita transaction system. Categories replace the legacy Types taxonomy.
"""

import inspect
from typing import Self, Tuple

from pydantic import model_validator

from papita_txnsmodel.services.categories import CategoriesService

from .base import BaseTableHandler


class CategoriesTableHandler(BaseTableHandler[CategoriesService, CategoriesService]):
    """Handler for loading and processing category table data.

    This handler specializes in managing category-related data by leveraging the
    CategoriesService. It provides methods to load, process, and dump category data
    through the service layer. parent_id references are resolved via CategoriesService.
    """

    @model_validator(mode="after")
    def _validate(self) -> Self:
        """Wire parent_id hierarchy resolution through CategoriesService."""
        if not self.dependencies:
            self.dependencies = {"parent_id": CategoriesService}

        connector = self.service.connector
        self.dependencies = {
            name: (service.model_validate({"connector": connector}) if inspect.isclass(service) else service)
            for name, service in self.dependencies.items()
        }
        return self

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """Get the v3 label identifiers for this handler."""
        return "categories", "categories_table", "category_table"

    @classmethod
    def legacy_labels(cls) -> Tuple[str, ...]:
        """Registrar-compat labels that emit DeprecationWarning on lookup."""
        return "types", "types_table", "type_table", "general_types"
