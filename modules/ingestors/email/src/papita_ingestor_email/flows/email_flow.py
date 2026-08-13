"""Email ingestion Prefect flow + Compose/serve entrypoint (PPT-082 / #176)."""

from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any

from papita_ingestor_core.flows.base import build_base_ingestion_flow
from papita_ingestor_core.runner.ingestion_runner import IngestionRunner
from papita_ingestor_core.types.records import FetchFilter, RunResult
from papita_ingestor_email.flow_settings import EmailFlowSettings
from papita_ingestor_email.owner import users_dto_for_owner_id
from papita_ingestor_email.parsers import ensure_parsers_registered
from papita_ingestor_email.run_status import execute_with_run_status
from papita_ingestor_email.runtime import (
    establish_database_from_env,
    load_environment_file,
    require_owner_in_database,
    run_cli_preflight,
)
from papita_ingestor_email.sources.gmail import GmailSource, ensure_registered
from papita_ingestor_email.wiring import EmailFlowDeps
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.ingestion import IngestionBridgeService

logger = logging.getLogger(__name__)

_FLOW_NAME = "papita-email-ingestion"
_DEPLOYMENT_NAME = "papita-email-ingestion-hourly"
_RUNNER_HEALTH_PORT = 8080


def default_fetch_filter(settings: EmailFlowSettings) -> FetchFilter:
    """Build a lookback ``since`` filter; ``fetch_limit`` stays on runner settings only."""
    since = datetime.now(timezone.utc) - timedelta(hours=settings.lookback_hours)
    return FetchFilter(since=since)


def build_email_runner(deps: EmailFlowDeps | None = None) -> IngestionRunner:
    """Wire Gmail + registered email parsers + bridge into ``IngestionRunner``.

    Registry ensure calls are the production SSOT after ``SourceRegistry`` /
    ``ParserRegistry`` clears in shared pytest runs (package ``__init__`` also
    registers on import for convenience).

    Args:
        deps: Optional wiring bundle (settings, source/bridge/owner injections).

    Returns:
        Configured ``IngestionRunner``.
    """
    wiring = deps or EmailFlowDeps()
    ensure_registered()
    ensure_parsers_registered()
    settings = wiring.flow_settings or EmailFlowSettings()
    owner = wiring.owner
    using_real_bridge = wiring.bridge is None
    should_establish = (
        wiring.establish_db if wiring.establish_db is not None else (using_real_bridge and not settings.dry_run)
    )
    should_verify_owner = (
        wiring.verify_owner if wiring.verify_owner is not None else (using_real_bridge and not settings.dry_run)
    )

    if should_establish:
        establish_database_from_env(require=True)

    if owner is None:
        owner_id = settings.owner_id
        if should_verify_owner:
            resolved = require_owner_in_database(owner_id)

            def _owner_from_db() -> UsersDTO:
                return resolved

            owner = _owner_from_db
        else:

            def _owner_from_env() -> UsersDTO:
                return users_dto_for_owner_id(owner_id)

            owner = _owner_from_env

    resolved_source = wiring.source or GmailSource(settings=wiring.gmail_settings)
    resolved_bridge = wiring.bridge if wiring.bridge is not None else IngestionBridgeService()
    return IngestionRunner(
        source=resolved_source,
        owner=owner,
        bridge=resolved_bridge,
        settings=settings,
    )


def build_email_ingestion_flow(
    *,
    deps: EmailFlowDeps | None = None,
    name: str = _FLOW_NAME,
) -> Any:
    """Return a Prefect ``@flow`` for email ingestion via ``build_base_ingestion_flow``.

    Requires Prefect (``make ingestor-flow-install``).

    Note (H1=B): bank parsers leave account/category FKs ``None``. Live runs
    without an injected enricher will DLQ-then-ack successfully parsed mail —
    they will not upsert ledger rows. Prefer ``PAPITA_INGESTOR_DRY_RUN=true``
    until a FK enricher lands.

    Non-dry runs persist connection + run status (PPT-083) via model services —
    never Gmail OAuth secrets.
    """
    wiring = deps or EmailFlowDeps()
    settings = wiring.flow_settings or EmailFlowSettings()
    deployment_name = wiring.deployment_name or _DEPLOYMENT_NAME
    should_persist_status = wiring.persist_status if wiring.persist_status is not None else not settings.dry_run

    def _runner_factory() -> IngestionRunner:
        return build_email_runner(wiring)

    def _default_filter() -> FetchFilter:
        logger.info(
            "Email ingestion default filter lookback_hours=%s fetch_limit=%s dry_run=%s",
            settings.lookback_hours,
            settings.fetch_limit,
            settings.dry_run,
        )
        return default_fetch_filter(settings)

    def _execute(runner: IngestionRunner, fetch_filter: FetchFilter | None) -> RunResult:
        return execute_with_run_status(
            runner,
            fetch_filter,
            settings=settings,
            flow_name=name,
            deployment_name=deployment_name,
            connection_service=wiring.connection_service,
            run_service=wiring.run_service,
            persist_status=should_persist_status,
        )

    return build_base_ingestion_flow(
        name=name,
        runner_factory=_runner_factory,
        retries=settings.flow_retries,
        retry_delay_seconds=settings.flow_retry_delay_seconds,
        default_fetch_filter_factory=_default_filter,
        execute=_execute,
    )


def serve_email_ingestion(
    *,
    deps: EmailFlowDeps | None = None,
    interval_minutes: int | None = None,
    deployment_name: str = _DEPLOYMENT_NAME,
    webserver: bool = True,
) -> None:
    """Serve the email flow on an interval schedule (Prefect ``flow.serve``).

    ``webserver=True`` exposes Prefect runner ``/health`` (default port 8080) for
    Compose HEALTHCHECK. ``deployment_name`` is persisted on connection/run rows
    (overrides ``EmailFlowDeps.deployment_name``).
    """
    wiring = replace(deps or EmailFlowDeps(), deployment_name=deployment_name)
    settings = wiring.flow_settings or EmailFlowSettings()
    minutes = interval_minutes if interval_minutes is not None else settings.schedule_interval_minutes
    flow_fn = build_email_ingestion_flow(deps=wiring)
    logger.info(
        "Serving %s every %s minute(s) (runner health :%s=%s)",
        deployment_name,
        minutes,
        _RUNNER_HEALTH_PORT,
        webserver,
    )
    flow_fn.serve(
        name=deployment_name,
        interval=timedelta(minutes=minutes),
        webserver=webserver,
    )


def _run_once_exit_code(result: RunResult) -> int:
    """Non-zero when the batch recorded failures (partial success still exits 1)."""
    if result.failed > 0:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI: ``--once`` for a single run; default serves the hourly schedule."""
    parser = argparse.ArgumentParser(description="Papita email ingestion Prefect flow (PPT-082)")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one ingestion batch and exit (default: serve on interval)",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=None,
        help="Override PAPITA_INGESTOR_SCHEDULE_INTERVAL_MINUTES when serving",
    )
    parser.add_argument(
        "--skip-env-file",
        action="store_true",
        help="Do not load environments/<PAPITA_ENV>/.env (Compose / already-exported env)",
    )
    parser.add_argument(
        "--skip-preflight",
        action="store_true",
        help="Skip Gmail env + owner DB checks (tests / advanced dry wiring only)",
    )
    parser.add_argument(
        "--no-webserver",
        action="store_true",
        help="Disable Prefect runner /health webserver when serving",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    if not args.skip_env_file:
        load_environment_file(override=False)
    settings = EmailFlowSettings()
    preflight_owner: UsersDTO | None = None
    if not args.skip_preflight:
        preflight_owner = run_cli_preflight(
            owner_id=settings.owner_id,
            dry_run=settings.dry_run,
            require_gmail=True,
        )

    owner_provider = None
    if preflight_owner is not None:
        resolved_owner = preflight_owner

        def _owner_provider() -> UsersDTO:
            return resolved_owner

        owner_provider = _owner_provider

    deps = EmailFlowDeps(
        flow_settings=settings,
        owner=owner_provider,
        # Preflight already established DB / verified owner when applicable.
        establish_db=False if preflight_owner is not None else None,
        verify_owner=False if preflight_owner is not None else None,
    )

    if args.once:
        flow_fn = build_email_ingestion_flow(deps=deps)
        result = flow_fn()
        logger.info("Email ingestion finished: %s", result.model_dump())
        return _run_once_exit_code(result)
    serve_email_ingestion(
        deps=deps,
        interval_minutes=args.interval_minutes,
        webserver=not args.no_webserver,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "build_email_ingestion_flow",
    "build_email_runner",
    "default_fetch_filter",
    "main",
    "serve_email_ingestion",
]
