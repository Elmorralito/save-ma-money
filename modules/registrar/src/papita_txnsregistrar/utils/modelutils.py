"""
Validation utilities for Pydantic models in the transaction tracker system.

This module provides validator functions used by Pydantic models to ensure data
consistency and correctness. It includes functions for validating semantic version
strings and tag formatting to maintain data quality throughout the system.
consistency and correctness. It includes specialized validators for:
- Semantic version strings
- Tag formatting and normalization
- Service dependency validation

These utilities help maintain data quality and structural integrity throughout
the transaction tracking system by providing reusable validation logic.
"""

import inspect
import re
from typing import Callable, Dict, List, Tuple, Type

from pydantic import ValidationInfo, ValidatorFunctionWrapHandler
from semver import Version

from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.utils.classutils import ClassDiscovery


def validate_python_version(value: str, handler: ValidatorFunctionWrapHandler) -> str:
    """
    Validate that a string follows semantic versioning format.

    This function verifies that a string represents a valid semantic version
    using the semver library. It's designed to be used as a Pydantic validator.

    Args:
        value: The version string to validate.
        handler: Pydantic validator handler for chaining validators.

    Returns:
        The validated version string.

    Raises:
        ValueError: If the string is not a valid semantic version.
    """
    return Version.is_valid(handler(value))


def validate_tags(value: List[str], handler: ValidatorFunctionWrapHandler) -> List[str]:
    """
    Validate and normalize a list of tag strings.

    This function processes a list of tags, ensuring that each tag:
    1. Contains only letters and spaces
    2. Is converted to lowercase
    3. Is unique in the final list

    It's designed to be used as a Pydantic validator.

    Args:
        value: List of tag strings to validate.
        handler: Pydantic validator handler for chaining validators.

    Returns:
        A normalized list of unique, lowercase tags.

    Raises:
        ValueError: If no valid tags are found after filtering.
    """
    value_ = handler(value)
    tags = [str.lower(elem) for elem in value_ if re.match(r"^([A-Za-z]|\s)+$", elem or "")]
    if not tags:
        raise ValueError("No valid tags found.")

    return list(set(tags))


def make_service_dependencies_validator(
    *, principal_service: Type[BaseService], allowed_dependencies: Tuple[Type[BaseService], ...]
) -> Callable[
    [Dict[str, Type[BaseService] | BaseService | str], ValidationInfo], Dict[str, Type[BaseService] | BaseService | str]
]:
    """
    Create a validator function to validate service dependencies.

    This function generates a validator that checks if the provided dependencies
    include the principal service and only allowed dependency types. It also
    verifies that dependency names correspond to fields in the principal service's
    DTO type.

    Args:
        principal_service: The main service that must be included in the dependencies.
        allowed_dependencies: A tuple of allowed service types for dependencies.

    Returns:
        A validator function that takes a dictionary of dependencies and validation info,
        and returns the validated dependencies dictionary.

    Example:
        ```python
        # Creating a validator for UserService dependencies
        user_dependencies_validator = make_service_dependencies_validator(
            principal_service=UserService,
            allowed_dependencies=(BaseService, AuthService, ProfileService)
        )

        # Using in a Pydantic model
        class UserServiceConfig(BaseModel):
            dependencies: Dict[str, Type[BaseService]]

            _validate_deps = validator('dependencies')(user_dependencies_validator)
        ```
    """

    def validate_service_dependencies(
        val: Dict[str, Type[BaseService] | BaseService | str],
        _: ValidationInfo,
    ) -> Dict[str, Type[BaseService] | BaseService | str]:
        """
        Validate the service dependencies.

        Args:
            val: The dependencies to validate as a dictionary mapping names to services.
            _: Additional validation info (not used in this implementation).

        Returns:
            The validated dependencies dictionary.

        Raises:
            ValueError: If the principal service is missing, if there are invalid
                        dependency types, or if a dependency name doesn't match a DTO field.
        """
        if principal_service.__name__ not in val:
            raise ValueError(f"Principal service '{principal_service.__name__}' is missing from dependencies.")

        dto = principal_service.dto_type
        for dep_name, dep_value in val.items():
            dep_value_ = ClassDiscovery.select(dep_value, BaseService) if isinstance(dep_value, str) else dep_value
            if not dep_value_:
                raise ValueError(f"Dependency '{dep_name}' could not be resolved.")

            dep_value_type = dep_value_ if inspect.isclass(dep_value_) else dep_value_.__class__
            if not issubclass(dep_value_type, allowed_dependencies):
                raise ValueError(f"Dependency '{dep_name}' has an invalid type '{dep_value_type.__name__}'.")

            field = dto.model_fields.get(dep_name)
            if field is None:
                raise ValueError(f"The name '{dep_name}' is not a valid field in DTO '{dto.__name__}'.")

        return val

    return validate_service_dependencies
