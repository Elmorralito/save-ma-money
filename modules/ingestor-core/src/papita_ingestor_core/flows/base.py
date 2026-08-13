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
    retries: int = 0,
    retry_delay_seconds: float = 60,
    default_fetch_filter_factory: Callable[[], FetchFilter | None] | None = None,
    execute: Callable[[IngestionRunner, FetchFilter | None], RunResult] | None = None,
) -> Any:
    """Return a Prefect ``@flow`` that runs ``IngestionRunner``.

    Requires the optional Poetry extra: ``poetry install -E prefect``.
    Monorepo day-to-day install: ``make ingestor-flow-install`` (root group
    ``ingestor-prefect``) — root ``package-mode = false`` so ``-E prefect`` at
    the workspace root does not apply.

    Args:
        name: Prefect flow name.
        runner_factory: Zero-arg callable that builds a configured ``IngestionRunner``.
            Required at flow run time.
        retries: Prefect flow-level retries (transient run failures).
        retry_delay_seconds: Delay between Prefect flow retries.
        default_fetch_filter_factory: Used when the flow is invoked without an
            explicit ``fetch_filter`` (e.g. lookback window).
        execute: Optional wrapper around ``runner.run`` (e.g. status persistence).
            Defaults to ``runner.run(fetch_filter)``.

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
            "Install with: poetry install -E prefect  (papita-ingestor-core) "
            "or make ingestor-flow-install (monorepo)"
        ) from exc

    @flow(name=name, retries=retries, retry_delay_seconds=retry_delay_seconds)
    def _ingestion_flow(fetch_filter: FetchFilter | None = None) -> RunResult:
        if runner_factory is None:
            raise ValueError("runner_factory is required to run the base ingestion flow")
        effective = fetch_filter
        if effective is None and default_fetch_filter_factory is not None:
            effective = default_fetch_filter_factory()
        runner = runner_factory()
        if execute is not None:
            return execute(runner, effective)
        return runner.run(effective)

    return _ingestion_flow


__all__ = ["build_base_ingestion_flow"]
