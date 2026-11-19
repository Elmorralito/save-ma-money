"""Email ingestion CLI + synchronous batch runner entrypoint (PPT-082 / PPT-098)."""

from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from papita_ingestor_core.runner.ingestion_runner import IngestionRunner
from papita_ingestor_core.types.records import FetchFilter, RunResult
from papita_ingestor_email.flow_settings import EmailFlowSettings
from papita_ingestor_email.owner import users_dto_for_owner_id
from papita_ingestor_email.parsers import default_email_parsers
from papita_ingestor_email.run_status import execute_with_run_status
from papita_ingestor_email.runtime import (
    establish_database_from_env,
    load_environment_file,
    require_owner_in_database,
    run_cli_preflight,
)
from papita_ingestor_email.sources.gmail import GmailSource
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
    """Wire Gmail + explicit email parsers + bridge into ``IngestionRunner``.

    Args:
        deps: Optional wiring bundle (settings, source/bridge/owner injections).

    Returns:
        Configured ``IngestionRunner``.
    """
    wiring = deps or EmailFlowDeps()
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
        parsers=default_email_parsers(),
        settings=settings,
    )


def build_email_ingestion_flow(
    *,
    deps: EmailFlowDeps | None = None,
    name: str = _FLOW_NAME,
) -> Callable[[FetchFilter | None], RunResult]:
    """Return a synchronous callable for email ingestion (Prefect-free).

    Non-dry runs persist connection + run status (PPT-083) via model services —
    never Gmail OAuth secrets.
    """
    wiring = deps or EmailFlowDeps()
    settings = wiring.flow_settings or EmailFlowSettings()
    deployment_name = wiring.deployment_name or _DEPLOYMENT_NAME
    should_persist_status = wiring.persist_status if wiring.persist_status is not None else not settings.dry_run

    def _run_batch(fetch_filter: FetchFilter | None = None) -> RunResult:
        runner = build_email_runner(wiring)
        eff_filter = fetch_filter if fetch_filter is not None else default_fetch_filter(settings)
        return execute_with_run_status(
            runner,
            eff_filter,
            settings=settings,
            flow_name=name,
            deployment_name=deployment_name,
            connection_service=wiring.connection_service,
            run_service=wiring.run_service,
            persist_status=should_persist_status,
        )

    return _run_batch


def serve_email_ingestion(
    *,
    deps: EmailFlowDeps | None = None,
    interval_minutes: int | None = None,
    deployment_name: str = _DEPLOYMENT_NAME,
    webserver: bool = True,
    max_runs: int | None = None,
) -> None:
    """Run the email ingestion loop on an interval schedule (no Prefect dependency)."""
    wiring = replace(deps or EmailFlowDeps(), deployment_name=deployment_name)
    settings = wiring.flow_settings or EmailFlowSettings()
    minutes = interval_minutes if interval_minutes is not None else settings.schedule_interval_minutes
    flow_fn = build_email_ingestion_flow(deps=wiring)
    logger.info(
        "Serving %s every %s minute(s) (webserver=%s)",
        deployment_name,
        minutes,
        webserver,
    )
    if hasattr(flow_fn, "serve"):
        flow_fn.serve(
            name=deployment_name,
            interval=timedelta(minutes=minutes),
            webserver=webserver,
        )
        return
    runs = 0
    while max_runs is None or runs < max_runs:
        flow_fn(None)
        runs += 1
        if max_runs is None or runs < max_runs:
            time.sleep(max(1, minutes * 60))


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
        result = flow_fn(None)
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
