"""
Core handler implementation for table data loading operations.

This module provides the base handler class for loading table data in the transaction tracking
system. It implements the abstract handler interface and adds dependency management functionality,
allowing handlers to work with multiple services while maintaining proper dependency validation
and instantiation.

The main class (BaseTableHandler) serves as a foundation for specific table data handlers
by providing record retrieval methods and dependency management capabilities.
"""

import inspect
import logging
import uuid
from typing import Annotated, Dict, Generic, List, Self, Tuple, Type, TypeVarTuple

import pandas as pd
from pydantic import BeforeValidator, Field, model_validator

from papita_txnsmodel.access.base.dto import TableDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.database.upsert import OnUpsertConflictDo
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.utils.classutils import ClassDiscovery

from .abstract import AbstractHandler, S
from .helpers import make_service_dependencies_validator

ServiceDependencies = TypeVarTuple("ServiceDependencies")
logger = logging.getLogger(__name__)


class BaseTableHandler(AbstractHandler[S], Generic[S, *ServiceDependencies]):
    """
    Base implementation of a handler for loading table data with service dependencies.

    This class extends the abstract load handler interface to provide concrete implementation
    for working with table data. It manages service dependencies through a validated dictionary
    and provides methods for retrieving individual records or record sets.

    The class uses dependency validation to ensure that all required services are properly
    configured and that they match the expected service types. Dependencies are initialized
    with the same connector as the principal service.

    Attributes:
        dependencies: Dictionary mapping dependency names to service instances or types.
            This is validated to ensure only permitted service types are included and is
            initialized during model validation.

    Examples:
        ```python
        class UserTableHandler(BaseTableHandler[UserService, AuthService, LoggingService]):
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
        Dict[str, Type[S] | S | str],
        BeforeValidator(
            make_service_dependencies_validator(principal_service=S, allowed_dependencies=ServiceDependencies)
        ),
    ] = Field(default_factory=dict)
    on_conflict_do: OnUpsertConflictDo = OnUpsertConflictDo.UPDATE

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

    @classmethod
    def labels(cls) -> Tuple[str, ...]:
        """
        Get the labels associated with this handler.

        This method should be implemented by subclasses to return a tuple of
        string labels that identify the handler's purpose or type.

        Returns:
            Tuple[str, ...]: A tuple of labels for the handler.

        Raises:
            NotImplementedError: When called directly on the abstract class.
        """
        raise NotImplementedError("Subclasses must implement the labels method.")

    def get_record(
        self,
        dto: TableDTO | dict | str | uuid.UUID,
        from_dependency: str | None = None,
        owner: UsersDTO | None = None,
        **kwargs,
    ) -> TableDTO | None:
        """
        Retrieve a single record from the service or a specified dependency.

        This method fetches a single record using either the principal service or a
        specified dependency service.

        Args:
            dto: The data transfer object, dictionary, ID string or UUID identifying the record
            from_dependency: Optional name of the dependency service to use for retrieval
            owner: The owner of the record. Defaults to None.
            **kwargs: Additional arguments to pass to the service's get method

        Returns:
            The retrieved record as a data transfer object or None if not found

        Raises:
            ValueError: If the specified dependency is not found in the dependencies dictionary
        """
        if from_dependency:
            service = self.dependencies.get(from_dependency)
            if service is None:
                raise ValueError(f"Dependency '{from_dependency}' not found in dependencies.")

            return service.get(obj=dto, owner=owner, **kwargs)

        return self.service.get(obj=dto, owner=owner, **kwargs)

    def get_records(
        self,
        dto: TableDTO | dict | None,
        from_dependency: str | None = None,
        owner: UsersDTO | None = None,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Retrieve multiple records from the service or a specified dependency.

        This method fetches multiple records using either the principal service or a
        specified dependency service, returning the results as a pandas DataFrame.

        Args:
            dto: The data transfer object, dictionary, or None for querying records
            from_dependency: Optional name of the dependency service to use for retrieval
            owner: The owner of the records to retrieve. Defaults to None.
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

            return service.get_records(dto=dto, owner=owner, **kwargs)

        return self.service.get_records(
            dto=dto, owner=owner, on_conflict_do=kwargs.pop("on_conflict_do", self.on_conflict_do), **kwargs
        )

    def build_record(self, dto: TableDTO | dict, owner: UsersDTO | None = None, **kwargs) -> TableDTO:
        """
        Build a complete record by resolving dependencies.

        This method takes a DTO or dictionary and transforms it into a fully resolved DTO
        by fetching or creating any dependent records referenced within it. For each dependency
        specified in the handler, corresponding fields in the DTO are resolved to actual
        instances by using the appropriate dependency service.

        Args:
            dto: The data transfer object or dictionary to build
            owner: The owner of the records. Defaults to None.
            **kwargs: Additional arguments to pass to dependency service operations

        Returns:
            TableDTO: The fully built record with resolved dependencies

        Raises:
            TypeError: If the provided DTO is not of the expected type
        """
        if isinstance(dto, dict):
            dto = self.service.dto_type.model_validate(dto)

        if not isinstance(dto, self.service.dto_type):
            raise TypeError(f"Invalid DTO type: {dto.__class__}, expected: {self.service.dto_type}")

        for field_name, dep_service in self.dependencies.items():
            value = getattr(dto, field_name, None)
            if not value:
                continue

            dependency_dto = dep_service.get_or_create(
                obj=value, owner=owner, on_conflict_do=kwargs.pop("on_conflict_do", self.on_conflict_do), **kwargs
            )
            setattr(dto, field_name, dependency_dto)

        return dto

    def build_records(
        self, dtos: pd.DataFrame | List[TableDTO] | List[dict], owner: "UsersDTO | None" = None, **kwargs
    ) -> pd.DataFrame:
        """
        Build multiple records by resolving dependencies for each.

        This method processes a collection of DTOs, dictionaries, or a DataFrame and transforms
        each record into a fully resolved DTO by fetching or creating any dependent records.
        It applies the build_record method to each item in the collection.

        Args:
            dtos: Collection of records to build (DataFrame, list of DTOs, or list of dicts)
            owner: The owner of the records. Defaults to None.
            **kwargs: Additional arguments to pass to dependency service operations

        Returns:
            pd.DataFrame: DataFrame containing all fully built records with resolved dependencies

        Raises:
            TypeError: If the provided input is not of a supported type
        """
        if isinstance(dtos, list) and all(isinstance(dto, self.service.dto_type) for dto in dtos):
            dtos_ = pd.DataFrame([dto.model_dump(mode="python") for dto in dtos])
        elif isinstance(dtos, list):
            dtos_ = pd.DataFrame(dtos)
        elif isinstance(dtos, pd.DataFrame):
            dtos_ = dtos
        else:
            raise TypeError("dtos must be a DataFrame or a list of TableDTO or dict instances.")

        return dtos_.apply(
            lambda row: self.build_record(dto=row.to_dict(), owner=owner, **kwargs).model_dump(mode="python"),
            axis=1,
            result_type="expand",
        )

    def create_record(self, dto: TableDTO | dict, owner: "UsersDTO | None" = None, **kwargs) -> TableDTO:
        """
        Create a new record using the service.

        This method persists a single record through the principal service's create method.

        Args:
            dto: The data transfer object or dictionary to create
            owner: The owner of the record. Defaults to None.
            **kwargs: Additional arguments to pass to the service's create method

        Returns:
            TableDTO: The created record as returned by the service
        """
        logger.debug("Upserting record for %s", self.service.dto_type.__dao_type__.__tablename__)
        return self.service.create(
            obj=dto, owner=owner, on_conflict_do=kwargs.pop("on_conflict_do", self.on_conflict_do), **kwargs
        )

    def create_records(
        self, dtos: pd.DataFrame | List[TableDTO] | List[dict], owner: "UsersDTO | None" = None, **kwargs
    ) -> pd.DataFrame:
        """
        Create multiple records using the service.

        This method persists multiple records through the principal service's upsert_records method.

        Args:
            dtos: Collection of records to create (DataFrame, list of DTOs, or list of dicts)
            owner: The owner of the records. Defaults to None.
            **kwargs: Additional arguments to pass to the service's upsert_records method

        Returns:
            pd.DataFrame: DataFrame containing the created records as returned by the service

        Raises:
            TypeError: If the provided input is not of a supported type
        """
        logger.debug("Upserting records for %s", self.service.dto_type.__dao_type__.__tablename__)
        if isinstance(dtos, list) and all(isinstance(dto, self.service.dto_type) for dto in dtos):
            dtos_ = pd.DataFrame([dto.model_dump(mode="python") for dto in dtos])
        elif isinstance(dtos, list) and all(isinstance(dto, dict) for dto in dtos):
            dtos_ = pd.DataFrame(dtos)
        elif isinstance(dtos, pd.DataFrame):
            dtos_ = dtos
        else:
            raise TypeError("dtos must be a DataFrame or a list of TableDTO or dict instances.")

        return self.service.upsert_records(
            df=dtos_,
            owner=owner,
            on_conflict_do=kwargs.pop("on_conflict_do", self.on_conflict_do),
            **kwargs,
        )

    def load(
        self,
        *,
        data: pd.DataFrame | List[TableDTO] | List[dict] | TableDTO,
        owner: UsersDTO | None = None,
        **kwargs,
    ) -> Self:
        """
        Load data into the handler, building records with resolved dependencies.

        This method processes input data by building complete records with resolved dependencies.
        The result is stored in the handler's _loaded_data attribute for later processing or dumping.

        Args:
            data: Input data to load (DataFrame, list of DTOs, list of dicts, or a single DTO/dict)
            owner: The owner of the records. Defaults to None.
            **kwargs: Additional arguments to pass to the build operations

        Returns:
            Self: The handler instance for method chaining

        Raises:
            TypeError: If the provided data is not of a supported type
        """
        logger.debug("Loading data into %s", self.service.dto_type.__dao_type__.__tablename__)
        if isinstance(data, (pd.DataFrame, list)):
            self._loaded_data = self.build_records(
                dtos=data, owner=owner, on_conflict_do=kwargs.pop("on_conflict_do", self.on_conflict_do), **kwargs
            )
            return self

        if not isinstance(data, (TableDTO, dict)):
            raise TypeError("data must be a DataFrame, list of TableDTO/dict, or a single TableDTO/dict.")

        self._loaded_data = self.build_record(
            dto=data, owner=owner, on_conflict_do=kwargs.pop("on_conflict_do", self.on_conflict_do), **kwargs
        )
        return self

    def dump(self, *, owner: UsersDTO | None = None, **kwargs) -> Self:
        """
        Persist loaded data to the underlying data store.

        This method saves the previously loaded data (from the load method) to the data store
        through the service layer. It handles both single records and collections of records.

        Args:
            owner: The owner of the records. Defaults to None.
            **kwargs: Additional arguments to pass to the create operations

        Returns:
            Self: The handler instance for method chaining

        Raises:
            ValueError: If no data has been loaded (call load() first)
        """
        logger.debug("Dumping data from %s", self.service.dto_type.__dao_type__.__tablename__)
        if self._loaded_data is None:
            raise ValueError("No data loaded to dump. Please load data before dumping.")

        if isinstance(self._loaded_data, pd.DataFrame):
            self.create_records(
                dtos=self._loaded_data,
                owner=owner,
                on_conflict_do=kwargs.pop("on_conflict_do", self.on_conflict_do),
                **kwargs,
            )
        else:
            self.create_record(
                dto=self._loaded_data,
                owner=owner,
                on_conflict_do=kwargs.pop("on_conflict_do", self.on_conflict_do),
                **kwargs,
            )

        return self
