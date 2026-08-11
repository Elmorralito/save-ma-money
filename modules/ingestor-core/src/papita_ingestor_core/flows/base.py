"""Prefect flow factory (optional extra ``prefect``) — PPT-079 / #173."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from papita_ingestor_core.runner.ingestion_runner import IngestionRunner
from papita_ingestor_core.types.records import FetchFilter, RunResult


def build_base_ingestion_flow(
    *,
    name: str = "papita-base-ingestion",
    runner_factory: Callable[[], IngestionRunner] | None = None,
) -> Any:
    """Return a Prefect ``@flow`` that runs ``IngestionRunner``.

    Requires the optional Poetry extra: ``poetry install -E prefect``.

    Args:
        name: Prefect flow name.
        runner_factory: Zero-arg callable that builds a configured ``IngestionRunner``.
            Required at flow run time.

    Returns:
        A Prefect flow callable.

    Raises:
        ImportError: If Prefect is not installed.
    """
    try:
        from prefect import flow
    except ImportError as exc:  # pragma: no cover - exercised when extra missing
        raise ImportError(
            "Prefect is required for build_base_ingestion_flow(). "
            "Install with: poetry install -E prefect  (papita-ingestor-core)"
        ) from exc

    @flow(name=name)
    def _ingestion_flow(fetch_filter: FetchFilter | None = None) -> RunResult:
        if runner_factory is None:
            raise ValueError("runner_factory is required to run the base ingestion flow")
        runner = runner_factory()
        return runner.run(fetch_filter)

    return _ingestion_flow


__all__ = ["build_base_ingestion_flow"]
