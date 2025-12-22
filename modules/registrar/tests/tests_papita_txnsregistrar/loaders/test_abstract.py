"""
Unit tests for the AbstractLoader abstract base class.

This module contains tests that verify the abstract interface behavior of AbstractLoader,
including instantiation restrictions, abstract method enforcement, and proper attribute
initialization for concrete implementations.
"""

import pytest
from typing import Iterable, Self

from papita_txnsmodel.utils.classutils import FallbackAction
from papita_txnsregistrar.loaders.abstract import AbstractLoader


def test_abstract_loader_cannot_be_instantiated_directly():
    """Test that AbstractLoader raises TypeError when attempting direct instantiation."""
    # Act & Assert
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AbstractLoader(on_failure_do=FallbackAction.RAISE)


def test_concrete_loader_must_implement_all_abstract_methods():
    """Test that incomplete concrete implementation raises TypeError due to missing abstract methods."""
    # Arrange
    class IncompleteLoader(AbstractLoader):
        pass

    # Act & Assert
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteLoader(on_failure_do=FallbackAction.LOG)


def test_complete_concrete_loader_can_be_instantiated():
    """Test that a complete concrete implementation with all abstract methods can be instantiated successfully."""
    # Arrange
    class CompleteLoader(AbstractLoader):
        _result: list = []

        @property
        def result(self) -> Iterable:
            return self._result

        def check_source(self, **kwargs) -> Self:
            return self

        def load(self, **kwargs) -> Self:
            return self

        def unload(self, **kwargs) -> Self:
            return self

    # Act
    loader = CompleteLoader(on_failure_do=FallbackAction.IGNORE)

    # Assert
    assert loader.on_failure_do == FallbackAction.IGNORE
    assert isinstance(loader, AbstractLoader)
    assert loader.result == []
