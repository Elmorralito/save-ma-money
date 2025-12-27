"""
File Base Loader Module.

This module defines the base class for all file-based data loaders in the Papita transaction registrar
system. It provides common functionality for validating file paths and establishing a consistent
interface for file loading operations.

The FileBaseLoader is designed to be extended by specific file format loaders (such as CSV, Excel,
JSON, etc.) which will implement the actual data loading logic while inheriting the path validation
and interface structure.
"""

import logging
from pathlib import Path
from typing import Self

import boto3
import smart_open
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class FileLoader(BaseModel):
    """
    Base class for all file-based data loaders.

    This abstract class provides the foundation for loading data from files in various formats.
    It handles file path validation and defines the interface that all file loaders must implement.
    Specific file format loaders should inherit from this class and override the `load` method
    to implement format-specific loading logic.

    Attributes:
        path: File path as string or Path object pointing to the data file to be loaded.

    Examples:
        ```python
        class CSVLoader(FileBaseLoader):
            def load(self, **kwargs):
                self.check_source()
                # CSV-specific loading logic
                return self

        loader = CSVLoader(path="/path/to/data.csv")
        data = loader.load().result
        ```
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: str | Path
    profile: str = "default"
    region_name: str | None = None
    endpoint_url: str | None = None

    @property
    def client(self) -> boto3.client:
        """
        Get the client for the file loader.

        Returns:
            boto3.client: The client for the file loader.
        """
        session_kwargs = {"profile_name": self.profile}
        client_kwargs = {}
        if self.region_name:
            session_kwargs["region_name"] = self.region_name
        if self.endpoint_url:
            client_kwargs["endpoint_url"] = self.endpoint_url
        return boto3.Session(**session_kwargs).client("s3", **client_kwargs)

    @property
    def transport_params(self) -> dict:
        """
        Get the transport parameters for the file loader.

        Returns:
            dict: The transport parameters for the file loader.
        """
        try:
            return {"client": self.client}
        except Exception:
            return {}

    def check_source(self, **kwargs) -> Self:
        """
        Validate that the provided file path exists and is readable.

        This method ensures that:
        1. The path points to an existing file
        2. The file is accessible for reading

        The method converts string paths to Path objects for consistent handling.

        Args:
            **kwargs: Additional keyword arguments for validation (unused in base implementation).

        Returns:
            Self: Instance of the loader for method chaining.

        Raises:
            OSError: If the path doesn't exist or isn't a readable file.
        """
        if isinstance(self.path, Path):
            self.path = self.path.absolute().as_posix()

        try:
            with smart_open.open(self.path, transport_params=self.transport_params) as freader:
                if not freader.readable():
                    self.on_failure_do.handle(OSError(f"The path '{self.path}' is not readable."), logger=logger)

        except FileNotFoundError:
            self.on_failure_do.handle(
                FileNotFoundError(f"The path '{self.path}' does not correspond to a file or does not exist."),
                logger=logger,
            )
        except Exception as err:
            self.on_failure_do.handle(err, logger=logger)

        self.path = self.path
        return self
