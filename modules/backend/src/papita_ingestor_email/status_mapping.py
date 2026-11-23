"""Backward-compatible re-exports of provider-agnostic status mapping."""

from __future__ import annotations

from papita_ingestor_core.status_mapping import (
    derive_run_status,
    run_result_to_record_request,
    summarize_failures,
)

__all__ = [
    "derive_run_status",
    "run_result_to_record_request",
    "summarize_failures",
]
