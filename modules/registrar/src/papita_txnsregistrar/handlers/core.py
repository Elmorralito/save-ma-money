"""
Core handler implementation for table data loading operations.

This module provides the base handler class for loading table data in the transaction tracking
system. It implements the abstract handler interface and adds dependency management functionality,
allowing handlers to work with multiple services while maintaining proper dependency validation
and instantiation.

The main class (BaseLoadTableHandler) serves as a foundation for specific table data handlers
by providing record retrieval methods and dependency management capabilities.
"""

import inspect
import uuid
from typing import Annotated, Dict, Generic, Self, Type, TypeVarTuple

import pandas as pd
from pydantic import BeforeValidator, model_validator

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.utils.classutils import ClassDiscovery
from papita_txnsregistrar.handlers.abstract import AbstractLoadHandler, S
from papita_txnsregistrar.utils.modelutils import make_service_dependencies_validator

ServiceDependencies = TypeVarTuple("ServiceDependencies")


class BaseLoadTableHandler(AbstractLoadHandler[S], Generic[*ServiceDependencies]):
    """
    Base implementation of a handler for loading table data with service dependencies.

    This class extends the abstract load handler interface to provide concrete implementation
    for working with table data. It manages service dependencies through a validated dictionary
    and provides methods for retrieving individual records or record sets.

    The class uses dependency validation to ensure that all required services are properly
    configured and that they match the expected service types. Dependencies are initialized
    with the same connector as the principal service.

    Args:
        S: The principal service type this handler works with
        ServiceDependencies: Variable tuple of allowed service dependency types

    Attributes:
        dependencies: Dictionary mapping dependency names to service instances or types

    Example:
        ```python
        class UserTableHandler(BaseLoadTableHandler[UserService, AuthService, LoggingService]):
            # Implementation specific to user table handling
            pass

        handler = UserTableHandler(
            service=UserService(...),
            dependencies={
                "UserService": UserService,
                "auth": AuthService,
                "logging": "LoggingService"  # String reference resolved during validation
            }
        )
        ```
    """

    dependencies: Annotated[
        Dict[str, Type[BaseService] | BaseService | str],
        BeforeValidator(
            make_service_dependencies_validator(principal_service=S, allowed_dependencies=ServiceDependencies)
        ),
    ]

    @model_validator(mode="after")
    def _validate_model(self) -> Self:
        """
        Validate and instantiate service dependencies after model initialization.

        This validator processes the dependencies dictionary to ensure all services are
        properly instantiated. It handles three cases:
        1. Class types - instantiated with the principal service's connector
        2. String references - resolved to classes and then instantiated
        3. Already instantiated services - used as-is

        Returns:
            Self: The validated instance with instantiated dependencies

        Raises:
            ValueError: If a string dependency cannot be resolved to a valid service class
        """
        new_dependencies = {}
        for dep_name, dep_type in self.dependencies.items():
            if inspect.isclass(dep_type):
                new_dependencies[dep_name] = dep_type.model_validate({"connector": self.service.connector})
            elif isinstance(dep_type, str):
                service_class = ClassDiscovery.select(dep_type, class_type=BaseService)
                if not inspect.isclass(service_class):
                    raise ValueError(f"Dependency '{dep_name}' could not be resolved to a valid service class.")

                new_dependencies[dep_name] = service_class.model_validate({"connector": self.service.connector})
            else:
                new_dependencies[dep_name] = dep_type

        self.dependencies = new_dependencies
        return self

    def get_record(
        self, dto: TableDTO | dict | str | uuid.UUID, from_dependency: str | None = None, **kwargs
    ) -> TableDTO | None:
        """
        Retrieve a single record from the service or a specified dependency.

        This method fetches a single record using either the principal service or a
        specified dependency service.

        Args:
            dto: The data transfer object, dictionary, ID string or UUID identifying the record
            from_dependency: Optional name of the dependency service to use for retrieval
            **kwargs: Additional arguments to pass to the service's get method

        Returns:
            TableDTO: The retrieved record as a data transfer object

        Raises:
            ValueError: If the specified dependency is not found in the dependencies dictionary
        """
        if from_dependency:
            service = self.dependencies.get(from_dependency)
            if service is None:
                raise ValueError(f"Dependency '{from_dependency}' not found in dependencies.")

            return service.get(dto=dto, **kwargs)

        return self.service.get(dto=dto, **kwargs)

    def get_records(self, dto: TableDTO | dict | None, from_dependency: str | None = None, **kwargs) -> pd.DataFrame:
        """
        Retrieve multiple records from the service or a specified dependency.

        This method fetches multiple records using either the principal service or a
        specified dependency service, returning the results as a pandas DataFrame.

        Args:
            dto: The data transfer object, dictionary, ID string or UUID identifying the records
            from_dependency: Optional name of the dependency service to use for retrieval
            **kwargs: Additional arguments to pass to the service's get_records method

        Returns:
            pd.DataFrame: The retrieved records as a pandas DataFrame

        Raises:
            ValueError: If the specified dependency is not found in the dependencies dictionary
        """
        if from_dependency:
            service = self.dependencies.get(from_dependency)
            if service is None:
                raise ValueError(f"Dependency '{from_dependency}' not found in dependencies.")

            return service.get_records(dto=dto, **kwargs)

        return self.service.get_records(dto=dto, **kwargs)
