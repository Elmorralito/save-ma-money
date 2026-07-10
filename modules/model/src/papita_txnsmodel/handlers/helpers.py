"""Pydantic validators for handler service dependency wiring.

Provides factory helpers used by load handlers to ensure injected service maps include
the principal service and only DTO-backed dependency names allowed by the handler contract.
"""

import inspect
from typing import Callable, Dict, Tuple, Type

from pydantic import ValidationInfo

from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.utils.classutils import ClassDiscovery


def make_service_dependencies_validator(
    *, principal_service: Type[BaseService], allowed_dependencies: Tuple[Type[BaseService], ...]
) -> Callable[
    [Dict[str, Type[BaseService] | BaseService | str], ValidationInfo], Dict[str, Type[BaseService] | BaseService | str]
]:
    """Create a Pydantic validator for handler service dependency maps.

    Args:
        principal_service: Main service that must appear in the dependency map.
        allowed_dependencies: Service types permitted as dependency values.

    Returns:
        Callable suitable for ``field_validator`` / legacy ``validator`` on a dependencies
        dict field; returns the validated map unchanged when all checks pass.

    Raises:
        ValueError: When a dependency cannot be resolved, has a disallowed type, or its
            key is not a field on the principal service DTO.
    """

    def validate_service_dependencies(
        val: Dict[str, Type[BaseService] | BaseService | str],
        _: ValidationInfo,
    ) -> Dict[str, Type[BaseService] | BaseService | str]:
        """Validate injected service dependencies against the principal DTO schema.

        Args:
            val: Mapping of dependency field names to service classes, instances, or
                import path strings resolvable via ``ClassDiscovery``.
            _: Pydantic validation context (unused).

        Returns:
            The input mapping when every dependency resolves and type-checks.

        Raises:
            ValueError: When the principal service is missing, a dependency type is not
                allowed, or a key is absent from the principal DTO ``model_fields``.
        """
        dto = principal_service.dto_type
        allowed = tuple(
            type_ for type_ in allowed_dependencies if inspect.isclass(type_) and issubclass(type_, BaseService)
        )
        if not allowed:
            allowed = (BaseService,)

        for dep_name, dep_value in val.items():
            if dep_name == principal_service.__name__:
                continue

            dep_value_ = ClassDiscovery.select(dep_value, BaseService) if isinstance(dep_value, str) else dep_value
            if not dep_value_:
                raise ValueError(f"Dependency '{dep_name}' could not be resolved.")

            if inspect.isclass(dep_value_):
                dep_value_type = dep_value_
            else:
                dep_value_type = type(dep_value_)

            if not issubclass(dep_value_type, allowed):
                raise ValueError(f"Dependency '{dep_name}' has an invalid type '{dep_value_type.__name__}'.")

            if dep_name not in dto.model_fields:
                raise ValueError(f"The name '{dep_name}' is not a valid field in DTO '{dto.__name__}'.")

        return val

    return validate_service_dependencies
