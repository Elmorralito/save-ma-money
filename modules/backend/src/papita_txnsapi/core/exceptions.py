class HandlerError(Exception):
    """
    Base exception for all errors raised by the handler layer.

    The router layer catches subclasses of this exception and maps them to
    the appropriate HTTP status codes via FastAPI exception handlers registered
    in ``api/core/exceptions.py``.
    """

    def __init__(self, message: str, resource_id: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.resource_id = resource_id


class HandlerNotFoundError(HandlerError):
    """
    Raised when a requested resource does not exist.

    Router mapping → HTTP 404 Not Found.
    """


class HandlerConflictError(HandlerError):
    """
    Raised when a create/update operation conflicts with an existing record.

    Router mapping → HTTP 409 Conflict.
    """


class HandlerValidationError(HandlerError):
    """
    Raised when domain-level validation fails beyond what Pydantic enforces.

    Router mapping → HTTP 422 Unprocessable Entity.
    """


class HandlerAuthorizationError(HandlerError):
    """
    Raised when the requesting user does not own the target resource.

    Router mapping → HTTP 403 Forbidden.
    """
