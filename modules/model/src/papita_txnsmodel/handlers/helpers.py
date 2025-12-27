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
        allowed = tuple(type_ for type_ in allowed_dependencies if issubclass(type_, BaseService))
        for dep_name, dep_value in val.items():
            dep_value_ = ClassDiscovery.select(dep_value, BaseService) if isinstance(dep_value, str) else dep_value
            if not dep_value_:
                raise ValueError(f"Dependency '{dep_name}' could not be resolved.")

            if inspect.isclass(dep_value_):
                dep_value_type = dep_value_
            else:
                dep_value_type = type(dep_value_)

            if not issubclass(dep_value_type, allowed):
                raise ValueError(f"Dependency '{dep_name}' has an invalid type '{dep_value_type.__name__}'.")

            field = dto.model_fields.get(dep_name)
            if field is None:
                raise ValueError(f"The name '{dep_name}' is not a valid field in DTO '{dto.__name__}'.")

        return val

    return validate_service_dependencies
