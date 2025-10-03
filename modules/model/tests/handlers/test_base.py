"""
Tests for BaseHandler class in papita_txnsmodel.handlers.base module.

This module contains tests for the BaseHandler class, which is a generic handler
for services. Tests cover instantiation, service setup, validation, and error
handling when checking services.
"""

import pytest
from unittest.mock import MagicMock

from papita_txnsmodel.handlers.base import BaseHandler
from papita_txnsmodel.services.base import BaseService
from papita_txnsmodel.utils.classutils import FallbackAction


class MockService(BaseService):
    """Mock implementation of BaseService for testing purposes."""



class MockHandler(BaseHandler[MockService]):
    pass


class MockConnector:
    """Mock connector for testing connection status checks."""
    def connected(self, on_disconnected=None):
        """Mock connected method."""
        return True


class TestBaseHandler:
    """Test suite for the BaseHandler class."""

    def test_init_default_values(self):
        """
        Test that BaseHandler initializes with correct default values.

        Ensures that a new BaseHandler has service=None and error_handler=RAISE.
        """
        handler = BaseHandler()
        assert handler.service is None
        assert handler.error_handler == FallbackAction.RAISE

    def test_init_custom_values(self):
        """
        Test that BaseHandler can be initialized with custom values.

        Verifies that the error_handler can be customized during initialization.
        """
        handler = BaseHandler(error_handler=FallbackAction.IGNORE)
        assert handler.service is None
        assert handler.error_handler == FallbackAction.IGNORE

    def test_setup_service_valid(self):
        """
        Test setup_service with a valid service instance.

        Verifies that the method correctly assigns the service and returns self.
        """
        handler = MockHandler()
        service = MockService()
        result = handler.setup_service(service)

        assert handler.service is service
        assert result is handler  # Method should return self for chaining

    def test_setup_service_invalid_type(self):
        """
        Test setup_service with an invalid service type.

        Confirms that TypeError is raised when a non-service object is provided.
        """
        handler = BaseHandler()
        not_a_service = "not a service"

        with pytest.raises(TypeError, match="Service type not compatible with this handler."):
            handler.setup_service(not_a_service)

    def test_checked_service_no_service(self):
        """
        Test checked_service property when no service is set.

        Verifies that ValueError is raised when trying to access the service
        before it has been set.
        """
        handler = BaseHandler()

        with pytest.raises(ValueError, match="The service has not being loaded."):
            _ = handler.checked_service

    def test_checked_service_with_service(self):
        """
        Test checked_service property with a properly set service.

        Verifies that the property returns the service after checking the
        connector's connected status.
        """
        handler = BaseHandler()
        service = MockService()
        handler.setup_service(service)

        # Mock the connector attribute
        mock_connector = MagicMock()
        handler.connector = mock_connector

        result = handler.checked_service

        assert result is service
        mock_connector.connected.assert_called_once_with(on_disconnected=FallbackAction.RAISE)

    def test_checked_service_custom_error_handler(self):
        """
        Test checked_service with a custom error handler.

        Ensures the custom error handler is passed to the connector's connected method.
        """
        handler = BaseHandler(error_handler=FallbackAction.IGNORE)
        service = MockService()
        handler.setup_service(service)

        mock_connector = MagicMock()
        handler.connector = mock_connector

        _ = handler.checked_service

        mock_connector.connected.assert_called_once_with(on_disconnected=FallbackAction.IGNORE)

    def test_setup_service_with_kwargs(self):
        """
        Test setup_service with additional keyword arguments.

        Verifies that the method accepts additional kwargs even if unused.
        """
        handler = BaseHandler()
        service = MockService()
        result = handler.setup_service(service, extra_param="value")

        assert handler.service is service
        assert result is handler
