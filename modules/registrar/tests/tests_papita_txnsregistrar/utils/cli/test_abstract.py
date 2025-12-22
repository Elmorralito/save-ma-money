"""Test suite for AbstractCLIUtils abstract base class.

This module contains unit tests for the AbstractCLIUtils class, which serves as the foundation
for all command-line interface utilities in the transaction registrar system. The tests verify
that the abstract class properly enforces its interface contract and cannot be instantiated
directly, while ensuring that concrete subclasses must implement all required abstract methods.
"""

import pytest
from typing import Self, Dict, Any

from papita_txnsregistrar.utils.cli.abstract import AbstractCLIUtils


class ConcreteCLIUtils(AbstractCLIUtils):
    """Concrete implementation of AbstractCLIUtils for testing purposes."""

    @classmethod
    def parse_cli_args(cls, **kwargs) -> Dict[str, Any]:
        """Parse command-line arguments and return a dictionary of parsed arguments."""
        return kwargs

    @classmethod
    def load(cls, **kwargs) -> Self:
        """Create and return a new instance of ConcreteCLIUtils."""
        return cls.model_validate(cls.parse_cli_args(**kwargs))

    def run(self) -> Self:
        """Run the CLI utility and return self for method chaining."""
        return self

    def stop(self) -> Self:
        """Stop the CLI utility and return self for method chaining."""
        return self


class IncompleteCLIUtils(AbstractCLIUtils):
    """Incomplete implementation missing abstract methods for testing."""

    @classmethod
    def load(cls, **kwargs) -> Self:
        """Create and return a new instance of IncompleteCLIUtils."""
        return cls.model_validate(kwargs)

    # Missing run() and stop() methods


def test_abstract_class_cannot_be_instantiated_directly():
    """Test that AbstractCLIUtils raises TypeError when attempting direct instantiation."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        AbstractCLIUtils()


def test_incomplete_subclass_cannot_be_instantiated():
    """Test that a subclass missing abstract methods raises TypeError during instantiation."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteCLIUtils.load()


def test_concrete_subclass_can_be_instantiated_and_used():
    """Test that a properly implemented subclass can be instantiated and all methods work correctly."""
    instance = ConcreteCLIUtils.load()
    assert isinstance(instance, AbstractCLIUtils)
    assert isinstance(instance, ConcreteCLIUtils)
    result_run = instance.run()
    assert result_run is instance
    result_stop = instance.stop()
    assert result_stop is instance


def test_abstract_methods_are_defined_on_class():
    """Test that all abstract methods are properly defined on AbstractCLIUtils class."""
    assert hasattr(AbstractCLIUtils, "load")
    assert hasattr(AbstractCLIUtils, "run")
    assert hasattr(AbstractCLIUtils, "stop")
    assert callable(getattr(AbstractCLIUtils, "load"))
    assert callable(getattr(AbstractCLIUtils, "run"))
    assert callable(getattr(AbstractCLIUtils, "stop"))
