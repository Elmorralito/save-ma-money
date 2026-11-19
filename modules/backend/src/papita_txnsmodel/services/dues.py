"""Payment-due helpers for transaction templates (PPT-072 / #165).

Resolves one-off and recurring due dates, upcoming-window membership, and
calendar-month period keys used to derive paid state from linked postings.
"""

from __future__ import annotations

import calendar
import uuid
from datetime import date, timedelta

from pydantic import BaseModel, ConfigDict, Field

from papita_txnsmodel.access.transactions.dto import TransactionTemplatesDTO
from papita_txnsmodel.config.transaction_partitions import add_months, month_start


class UpcomingDueDTO(BaseModel):
    """Owner-scoped upcoming due row for in-app reminders.

    Attributes:
        template: Source payment-due template.
        due_date: Resolved calendar due for this occurrence.
        remind_start: First day the due should surface in-app.
        is_paid: Whether an active linked posting exists for the due period.
        paid_transaction_id: Latest active linked posting id when paid.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    template: TransactionTemplatesDTO
    due_date: date
    remind_start: date
    is_paid: bool = False
    paid_transaction_id: uuid.UUID | None = Field(default=None)


def period_key(due: date) -> tuple[int, int]:
    """Return ``(year, month)`` for paid-state matching on a resolved due."""
    return due.year, due.month


def period_bounds(due: date) -> tuple[date, date]:
    """Return inclusive calendar-month bounds for a resolved due date.

    Args:
        due: Resolved payment due date.

    Returns:
        Tuple of ``(month_start, month_end)`` inclusive dates.
    """
    start = month_start(due)
    end = date(due.year, due.month, calendar.monthrange(due.year, due.month)[1])
    return start, end


def due_in_month(template: TransactionTemplatesDTO, *, year: int, month: int) -> date:
    """Resolve the recurring due date within a calendar month.

    Args:
        template: Template with ``planned_day`` / ``use_month_end``.
        year: Calendar year.
        month: Calendar month (1–12).

    Returns:
        Due date clamped to the month length when needed.
    """
    last_day = calendar.monthrange(year, month)[1]
    if template.use_month_end:
        day = last_day
    else:
        day = min(int(template.planned_day), last_day)
    return date(year, month, day)


def resolve_due_date(template: TransactionTemplatesDTO, *, ref: date) -> date:
    """Resolve a single due date for ``ref``'s month (one-off wins).

    Args:
        template: Payment-due template.
        ref: Reference date whose calendar month is used for recurring dues.

    Returns:
        One-off ``due_date`` when set; otherwise recurring due in ``ref``'s month.
    """
    if template.due_date is not None:
        return template.due_date
    return due_in_month(template, year=ref.year, month=ref.month)


def candidate_due_dates(template: TransactionTemplatesDTO, *, as_of: date) -> list[date]:
    """Candidate dues near ``as_of`` for upcoming-window evaluation.

    One-off templates yield only ``due_date``. Recurring templates yield dues for
    the previous, current, and next calendar months relative to ``as_of``.

    Args:
        template: Payment-due template.
        as_of: Window anchor date.

    Returns:
        Ordered candidate due dates (earliest first, de-duplicated).
    """
    if template.due_date is not None:
        return [template.due_date]

    candidates: list[date] = []
    for offset in (-1, 0, 1):
        month_ref = add_months(month_start(as_of), offset)
        candidates.append(due_in_month(template, year=month_ref.year, month=month_ref.month))
    return sorted(set(candidates))


def remind_start_for(due: date, remind_days_before: int | None) -> date:
    """First calendar day the due should surface (``None`` remind ⇒ due day)."""
    lead = 0 if remind_days_before is None else int(remind_days_before)
    return due - timedelta(days=lead)


def in_upcoming_window(
    due: date,
    remind_days_before: int | None,
    *,
    as_of: date,
    window_days: int,
) -> bool:
    """Return whether the reminder interval overlaps ``[as_of, as_of+window]``.

    Overlap uses closed intervals: ``[due - remind, due]`` vs
    ``[as_of, as_of + window_days]``. ``remind_days_before is None`` is treated as 0.

    Args:
        due: Resolved due date.
        remind_days_before: Optional lead days before due.
        as_of: Window start (inclusive).
        window_days: Inclusive days after ``as_of`` to include.

    Returns:
        True when the intervals overlap.
    """
    if window_days < 0:
        raise ValueError("window_days must be >= 0")
    remind_start = remind_start_for(due, remind_days_before)
    window_end = as_of + timedelta(days=window_days)
    return remind_start <= window_end and as_of <= due


def select_upcoming_due(
    template: TransactionTemplatesDTO,
    *,
    as_of: date,
    window_days: int,
) -> date | None:
    """Pick the earliest candidate due that falls in the upcoming window.

    Args:
        template: Payment-due template.
        as_of: Window anchor.
        window_days: Inclusive window length in days.

    Returns:
        Resolved due date, or None when no candidate is in window.
    """
    for due in candidate_due_dates(template, as_of=as_of):
        if in_upcoming_window(due, template.remind_days_before, as_of=as_of, window_days=window_days):
            return due
    return None
