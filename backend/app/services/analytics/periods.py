from calendar import monthrange
from datetime import date
from enum import Enum

from sqlalchemy import func

from app.models import Transaction


class GroupBy(str, Enum):
    month = "month"
    quarter = "quarter"
    year = "year"


def _period_label(group_by: GroupBy):
    """Return SQL date_trunc expression for Transaction.date depending on grouping."""
    return func.date_trunc(group_by.value, Transaction.date)


def _generate_periods(date_from: date, date_to: date, group_by: GroupBy) -> list[tuple[date, date]]:
    """Generate (period_start, period_end) tuples covering the date range."""
    periods = []
    if group_by == GroupBy.month:
        cur = date(date_from.year, date_from.month, 1)
        while cur <= date_to:
            end = date(cur.year, cur.month, monthrange(cur.year, cur.month)[1])
            periods.append((cur, end))
            if cur.month == 12:
                cur = date(cur.year + 1, 1, 1)
            else:
                cur = date(cur.year, cur.month + 1, 1)
    elif group_by == GroupBy.quarter:
        qstart_month = ((date_from.month - 1) // 3) * 3 + 1
        cur = date(date_from.year, qstart_month, 1)
        while cur <= date_to:
            end_month = cur.month + 2
            end = date(cur.year, end_month, monthrange(cur.year, end_month)[1])
            periods.append((cur, end))
            if cur.month >= 10:
                cur = date(cur.year + 1, 1, 1)
            else:
                cur = date(cur.year, cur.month + 3, 1)
    else:  # year
        cur = date(date_from.year, 1, 1)
        while cur <= date_to:
            end = date(cur.year, 12, 31)
            periods.append((cur, end))
            cur = date(cur.year + 1, 1, 1)
    return periods
