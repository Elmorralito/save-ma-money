"""FastAPI application entrypoint for the unified backend package."""

from papita_txnsapi.main import app, create_app

__all__ = ["app", "create_app"]
