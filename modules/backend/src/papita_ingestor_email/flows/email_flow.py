"""Email ingestion CLI + synchronous batch runner entrypoint (PPT-082 / PPT-098)."""

from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from papita_ingestor_core.registry import get_default_registry
from papita_ingestor_core.runner.ingestion_runner import IngestionRunner
from papita_ingestor_core.types.records import FetchFilter, RunResult
from papita_ingestor_email.enrichment import EmailFKEnricher
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
from papita_txnsmodel.access.ingestion.dto import IngestionConnectionDTO
from papita_txnsmodel.access.users.dto import UsersDTO
from papita_txnsmodel.services.ingestion import IngestionBridgeService
from papita_txnsmodel.services.ingestion_status import IngestionConnectionService

logger = logging.getLogger(__name__)

_FLOW_NAME = "papita-email-ingestion"
_DEPLOYMENT_NAME = "papita-email-ingestion-hourly"
_RUNNER_HEALTH_PORT = 8080


def default_fetch_filter(settings: EmailFlowSettings) -> FetchFilter:
    """Build lookback + channel filter; ``fetch_limit`` stays on runner settings only."""
    since = datetime.now(timezone.utc) - timedelta(hours=settings.lookback_hours)
    extra: dict[str, object] = {}
    if settings.email_senders:
        extra["senders"] = list(settings.email_senders)
    if settings.email_subjects:
        extra["subjects"] = list(settings.email_subjects)
    if settings.email_source_label:
        extra["source_label"] = settings.email_source_label
    if settings.email_query:
        extra["q"] = settings.email_query
    return FetchFilter(since=since, extra=extra)


def fetch_filter_from_connection(connection: IngestionConnectionDTO) -> FetchFilter:
    """Build lookback + channel filter from an owner's persisted DB connection."""
    since = datetime.now(timezone.utc) - timedelta(hours=connection.lookback_hours)
    extra: dict[str, object] = {}
    if connection.email_senders:
        extra["senders"] = list(connection.email_senders)
    if connection.email_subjects:
        extra["subjects"] = list(connection.email_subjects)
    if connection.email_source_label:
        extra["source_label"] = connection.email_source_label
    if connection.email_query:
        extra["q"] = connection.email_query
    return FetchFilter(since=since, extra=extra)


def _has_channel_scope(fetch_filter: FetchFilter | None) -> bool:
    """Return True when at least one narrowing email channel filter is configured."""
    if fetch_filter is None or not fetch_filter.extra:
        return False
    extra = fetch_filter.extra
    for key in ("senders", "sender", "source_label", "label", "subjects", "subject", "q"):
        val = extra.get(key)
        if isinstance(val, str) and val.strip():
            return True
        if isinstance(val, (list, tuple, set)) and any(str(item).strip() for item in val):
            return True
    return False


def _attach_fk_enricher(*, runner: IngestionRunner, db_conn: IngestionConnectionDTO) -> None:
    """Attach an ``EmailFKEnricher`` backed by ``db_conn.parsing_rules`` and owner accounts/categories."""
    try:
        from sqlalchemy import or_, select

        from papita_txnsmodel.database.session import get_session_manager
        from papita_txnsmodel.model.accounts import Accounts
        from papita_txnsmodel.model.categories import Categories

        owner = runner._resolve_owner()  # pylint: disable=protected-access
        if owner.id is None:
            return
        mgr = get_session_manager()
        with mgr.session_scope() as session:
            acc_rows = session.scalars(
                select(Accounts).where(Accounts.owner_id == owner.id, Accounts.active == True)  # noqa: E712
            ).all()
            cat_rows = session.scalars(
                select(Categories).where(
                    or_(Categories.owner_id == owner.id, Categories.owner_id.is_(None)),
                    Categories.active == True,  # noqa: E712
                )
            ).all()
            accounts = [{"id": a.id, "name": a.name} for a in acc_rows]
            categories = [
                {
                    "id": c.id,
                    "name": c.name,
                    "category_kind": c.category_kind.value
                    if hasattr(c.category_kind, "value")
                    else str(c.category_kind),
                }
                for c in cat_rows
            ]
        rules = list(getattr(db_conn, "parsing_rules", None) or [])
        runner.set_enricher(EmailFKEnricher(parsing_rules=rules, accounts=accounts, categories=categories))
    except Exception:  # pylint: disable=broad-except
        logger.exception("Failed to attach EmailFKEnricher; proceeding without FK enrichment")


def _load_db_connection(
    *,
    runner: IngestionRunner,
    wiring: EmailFlowDeps,
    flow_name: str,
    should_persist_status: bool,
) -> IngestionConnectionDTO | None:
    """Load the owner's persisted email connection config when DB status is active."""
    conn_svc = wiring.connection_service or (IngestionConnectionService() if should_persist_status else None)
    if conn_svc is None or not hasattr(conn_svc, "get_connection_by_natural_key"):
        return None
    owner = runner._resolve_owner()  # pylint: disable=protected-access  # intentional plugin seam
    try:
        found = conn_svc.get_connection_by_natural_key(owner=owner, provider="email", flow_name=flow_name)
    except Exception:  # pylint: disable=broad-except
        logger.exception(
            "Failed to load persisted ingestion connection owner_id=%s flow_name=%s; falling back to env settings",
            owner.id,
            flow_name,
        )
        return None
    return found if isinstance(found, IngestionConnectionDTO) else None


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

    active_registry = wiring.registry or get_default_registry()
    if wiring.source is not None:
        resolved_source = wiring.source
    elif wiring.connector_id == "gmail" and wiring.registry is None:
        resolved_source = GmailSource(settings=wiring.gmail_settings)
    else:
        resolved_source = active_registry.get_source(wiring.connector_id)
    resolved_bridge = wiring.bridge if wiring.bridge is not None else IngestionBridgeService()
    resolved_parsers = (
        default_email_parsers(registry=active_registry)
        if wiring.connector_id == "gmail"
        else active_registry.get_parsers(
            source_id=resolved_source.source_id,
            ingestion_source=resolved_source.manifest.ingestion_source,
        )
    )
    return IngestionRunner(
        source=resolved_source,
        owner=owner,
        bridge=resolved_bridge,
        parsers=resolved_parsers,
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
        provider_label = "email" if wiring.connector_id == "gmail" else runner.source_id
        eff_filter = fetch_filter
        db_conn = _load_db_connection(
            runner=runner,
            wiring=wiring,
            flow_name=name,
            should_persist_status=should_persist_status,
        )
        if db_conn is not None:
            _attach_fk_enricher(runner=runner, db_conn=db_conn)
        if eff_filter is None:
            if db_conn is not None:
                if not db_conn.enabled:
                    logger.info(
                        "Skipping disabled email ingestion connection id=%s owner_id=%s",
                        db_conn.id,
                        db_conn.owner_id,
                    )
                    return RunResult()
                if not getattr(db_conn, "gmail_access_enabled", True):
                    logger.info(
                        "Skipping email ingestion: per-user Gmail access is disabled id=%s owner_id=%s",
                        db_conn.id,
                        db_conn.owner_id,
                    )
                    return RunResult()
                eff_filter = fetch_filter_from_connection(db_conn)
            else:
                eff_filter = default_fetch_filter(settings)
            if not _has_channel_scope(eff_filter):
                logger.warning(
                    "Skipping email ingestion: no channel filters configured for owner_id=%s flow_name=%s",
                    settings.owner_id,
                    name,
                )
                return RunResult()
        return execute_with_run_status(
            runner,
            eff_filter,
            settings=settings,
            flow_name=name,
            deployment_name=deployment_name,
            connection_service=wiring.connection_service,
            run_service=wiring.run_service,
            persist_status=should_persist_status,
            provider=provider_label,
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


def _apply_cli_filter_overrides(settings: EmailFlowSettings, args: argparse.Namespace) -> EmailFlowSettings:
    """Return updated settings when optional CLI channel filter flags are supplied."""
    updates: dict[str, object] = {}
    if args.lookback_hours is not None:
        updates["lookback_hours"] = args.lookback_hours
    if args.sender is not None:
        updates["email_senders"] = [part.strip() for item in args.sender for part in item.split(",") if part.strip()]
    if args.subject is not None:
        updates["email_subjects"] = [part.strip() for item in args.subject for part in item.split(",") if part.strip()]
    if args.source_label is not None:
        updates["email_source_label"] = args.source_label.strip() or None
    if args.query is not None:
        updates["email_query"] = args.query.strip() or None
    if not updates:
        return settings
    return settings.model_copy(update=updates)


def main(argv: list[str] | None = None) -> int:
    """CLI: ``--once`` for a single run; default serves the hourly schedule."""
    parser = argparse.ArgumentParser(description="Papita email ingestion runner (PPT-082)")
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
        "--lookback-hours",
        type=int,
        default=None,
        help="Override PAPITA_INGESTOR_LOOKBACK_HOURS for fetched Gmail window",
    )
    parser.add_argument(
        "--sender",
        action="append",
        default=None,
        help="Override PAPITA_INGESTOR_EMAIL_SENDERS (repeatable or comma-separated)",
    )
    parser.add_argument(
        "--subject",
        action="append",
        default=None,
        help="Override PAPITA_INGESTOR_EMAIL_SUBJECTS (repeatable or comma-separated)",
    )
    parser.add_argument(
        "--source-label",
        default=None,
        help="Override PAPITA_INGESTOR_EMAIL_SOURCE_LABEL (restrict to a Gmail label)",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Override PAPITA_INGESTOR_EMAIL_QUERY (raw Gmail search fragment)",
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
        "--connector",
        type=str,
        default="gmail",
        help="Registered pull-source connector id from ConnectorRegistry (default: gmail)",
    )
    parser.add_argument(
        "--no-webserver",
        action="store_true",
        help="Disable Prefect runner /health webserver when serving",
    )
    parser.add_argument(
        "--orchestrator",
        action="store_true",
        help="Run as a Hatchet orchestrator worker (requires HATCHET_CLIENT_TOKEN)",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    if not args.skip_env_file:
        load_environment_file(override=False)
    if args.orchestrator:
        from papita_ingestor_email.orchestrator import run_orchestrator_worker

        return run_orchestrator_worker(skip_env_file=True)
    settings = _apply_cli_filter_overrides(EmailFlowSettings(), args)
    preflight_owner: UsersDTO | None = None
    if not args.skip_preflight:
        if args.connector == "gmail":
            preflight_owner = run_cli_preflight(
                owner_id=settings.owner_id,
                dry_run=settings.dry_run,
                require_gmail=True,
            )
        else:
            source = get_default_registry().get_source(args.connector)
            source.preflight()
            preflight_owner = run_cli_preflight(
                owner_id=settings.owner_id,
                dry_run=settings.dry_run,
                require_gmail=False,
            )

    owner_provider = None
    if preflight_owner is not None:
        resolved_owner = preflight_owner

        def _owner_provider() -> UsersDTO:
            return resolved_owner

        owner_provider = _owner_provider

    deps = EmailFlowDeps(
        flow_settings=settings,
        connector_id=args.connector,
        owner=owner_provider,
        # Preflight already established DB / verified owner when applicable.
        establish_db=False if preflight_owner is not None else None,
        verify_owner=False if preflight_owner is not None else None,
    )

    if args.once:
        flow_fn = build_email_ingestion_flow(deps=deps)
        result = flow_fn(None)
        logger.info(
            "Email ingestion finished: fetched=%d created=%d updated=%d reactivated=%d "
            "failed=%d dead_lettered=%d acknowledged=%d dry_run_skipped=%d",
            result.fetched,
            result.created,
            result.updated,
            result.reactivated,
            result.failed,
            result.dead_lettered,
            result.acknowledged,
            result.dry_run_skipped,
        )
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
    "fetch_filter_from_connection",
    "main",
    "serve_email_ingestion",
]
