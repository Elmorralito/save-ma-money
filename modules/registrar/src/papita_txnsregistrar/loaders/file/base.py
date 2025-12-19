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
import os
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class FileLoader(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
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

    path: str | Path

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
        path = Path(self.path) if isinstance(self.path, str) else self.path
        if not (path.is_file() and path.exists() and os.access(path.as_posix(), os.R_OK)):
            self.on_failure_do.handle(
                OSError("The path does not correspond to a file or does not exist."), logger=logger
            )

        self.path = path
        return self
