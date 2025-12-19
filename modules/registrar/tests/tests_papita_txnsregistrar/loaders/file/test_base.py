"""
Unit tests for the FileLoader base class.

This module contains tests that verify file path validation, source checking functionality,
and proper handling of various file path scenarios including valid files, invalid paths,
and error conditions.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from papita_txnsmodel.utils.classutils import FallbackAction
from papita_txnsregistrar.loaders.abstract import AbstractLoader
from papita_txnsregistrar.loaders.file.base import FileLoader


class TestFileLoader(FileLoader, AbstractLoader):
    """Test implementation of FileLoader with AbstractLoader for testing purposes."""

    _result: list = []

    @property
    def result(self):
        """Return test result."""
        return self._result

    def load(self, **kwargs):
        """Load implementation for testing."""
        return self

    def unload(self, **kwargs):
        """Unload implementation for testing."""
        return self


def test_check_source_with_valid_string_path():
    """Test that check_source validates and accepts a valid file path provided as string."""
    # Arrange
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name
        try:
            loader = TestFileLoader(path=tmp_path, error_handler=FallbackAction.RAISE)

            # Act
            result = loader.check_source()

            # Assert
            assert result is loader
            assert isinstance(loader.path, Path)
            assert loader.path.exists()
            assert loader.path.is_file()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


def test_check_source_with_valid_path_object():
    """Test that check_source validates and accepts a valid file path provided as Path object."""
    # Arrange
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
        try:
            loader = TestFileLoader(path=tmp_path, error_handler=FallbackAction.RAISE)

            # Act
            result = loader.check_source()

            # Assert
            assert result is loader
            assert isinstance(loader.path, Path)
            assert loader.path.exists()
            assert loader.path.is_file()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


def test_check_source_with_nonexistent_path_raises_error():
    """Test that check_source raises OSError when file path does not exist."""
    # Arrange
    nonexistent_path = "/nonexistent/path/to/file.txt"
    loader = TestFileLoader(path=nonexistent_path, error_handler=FallbackAction.RAISE)

    # Act & Assert
    with pytest.raises(OSError, match="The path does not correspond to a file or does not exist"):
        loader.check_source()


def test_check_source_with_directory_path_raises_error():
    """Test that check_source raises OSError when path points to a directory instead of a file."""
    # Arrange
    with tempfile.TemporaryDirectory() as tmp_dir:
        loader = TestFileLoader(path=tmp_dir, error_handler=FallbackAction.RAISE)

        # Act & Assert
        with pytest.raises(OSError, match="The path does not correspond to a file or does not exist"):
            loader.check_source()
