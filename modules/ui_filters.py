"""
UI Filter Helpers

Functions to apply date filters that mimic what users see in the Cin7 UI.
The UI typically hides old/archived records by default using date range filters.
"""

from datetime import datetime, timedelta
from typing import Optional


def get_date_range(days_back: int = 90) -> str:
    """
    Get ISO date string for filtering records modified since X days ago.

    Args:
        days_back: Number of days to look back (default: 90)

    Returns:
        ISO formatted date string (YYYY-MM-DD)

    Example:
        >>> get_date_range(30)  # Last 30 days
        '2024-01-15'
    """
    cutoff_date = datetime.now() - timedelta(days=days_back)
    return cutoff_date.strftime('%Y-%m-%d')


def get_month_start(year: int, month: int) -> str:
    """
    Get the first day of a specific month.

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)

    Returns:
        ISO formatted date string (YYYY-MM-DD)

    Example:
        >>> get_month_start(2024, 1)
        '2024-01-01'
    """
    return f"{year:04d}-{month:02d}-01"


def get_month_range(year: int, month: int) -> tuple[str, str]:
    """
    Get start and end dates for a specific month.

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)

    Returns:
        Tuple of (start_date, end_date) as ISO strings

    Example:
        >>> get_month_range(2024, 1)
        ('2024-01-01', '2024-01-31')
    """
    start_date = datetime(year, month, 1)

    # Get last day of month
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)

    return (
        start_date.strftime('%Y-%m-%d'),
        end_date.strftime('%Y-%m-%d')
    )


def get_current_month_start() -> str:
    """
    Get the first day of the current month.

    Returns:
        ISO formatted date string (YYYY-MM-DD)

    Example:
        >>> get_current_month_start()  # If today is 2024-02-16
        '2024-02-01'
    """
    now = datetime.now()
    return f"{now.year:04d}-{now.month:02d}-01"


def get_previous_month_start() -> str:
    """
    Get the first day of the previous month.

    Returns:
        ISO formatted date string (YYYY-MM-DD)
    """
    now = datetime.now()
    if now.month == 1:
        prev_year = now.year - 1
        prev_month = 12
    else:
        prev_year = now.year
        prev_month = now.month - 1

    return f"{prev_year:04d}-{prev_month:02d}-01"


def filter_by_date_field(
    records: list,
    date_field: str,
    days_back: Optional[int] = None,
    start_date: Optional[str] = None
) -> list:
    """
    Filter a list of records by a date field (client-side filtering).

    Use this when the API doesn't support date filtering but returns a date field.

    Args:
        records: List of record dictionaries
        date_field: Name of the date field to filter on (e.g., 'OrderDate', 'ModifiedDate')
        days_back: Only include records from last X days
        start_date: Only include records on or after this date (YYYY-MM-DD)

    Returns:
        Filtered list of records

    Example:
        >>> pos = client.get_purchase_list(order_status="DRAFT")
        >>> recent_pos = filter_by_date_field(pos, 'OrderDate', days_back=30)
    """
    if not records:
        return []

    # Determine cutoff date
    if days_back:
        cutoff = datetime.now() - timedelta(days=days_back)
    elif start_date:
        cutoff = datetime.fromisoformat(start_date)
    else:
        # No filter - return all
        return records

    filtered = []
    for record in records:
        date_value = record.get(date_field)
        if not date_value:
            continue

        try:
            # Parse date (handles both ISO datetime and date-only formats)
            if 'T' in date_value:
                record_date = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            else:
                record_date = datetime.fromisoformat(date_value)

            # Compare (make cutoff timezone-aware if needed)
            if record_date.tzinfo and not cutoff.tzinfo:
                cutoff = cutoff.replace(tzinfo=record_date.tzinfo)

            if record_date >= cutoff:
                filtered.append(record)
        except (ValueError, AttributeError):
            # Skip records with invalid dates
            continue

    return filtered


class UIFilters:
    """
    Pre-configured filter sets that match common Cin7 UI views.

    Usage:
        >>> filters = UIFilters()
        >>> client.get_purchase_list(order_status="DRAFT", modified_since=filters.last_90_days)
    """

    def __init__(self):
        self.last_30_days = get_date_range(30)
        self.last_60_days = get_date_range(60)
        self.last_90_days = get_date_range(90)
        self.last_180_days = get_date_range(180)
        self.last_365_days = get_date_range(365)
        self.current_month = get_current_month_start()
        self.previous_month = get_previous_month_start()

    def __repr__(self):
        return (
            f"UIFilters(\n"
            f"  last_30_days={self.last_30_days}\n"
            f"  last_60_days={self.last_60_days}\n"
            f"  last_90_days={self.last_90_days}\n"
            f"  current_month={self.current_month}\n"
            f")"
        )
