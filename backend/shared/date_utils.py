"""
Date calculation and manipulation utilities.
Pure functions without business logic dependencies.
"""
from datetime import datetime, timedelta, date, time
from typing import Optional, Tuple
import json

from .constants import (
    RECURRENCE_NONE,
    RECURRENCE_DAILY,
    RECURRENCE_EVERY_N_DAYS,
    RECURRENCE_WEEKLY,
)


def parse_time(time_str: str) -> Tuple[int, int]:
    """
    Parse time string into hour and minute.

    Args:
        time_str: Time string in "HH:MM" format

    Returns:
        Tuple of (hour, minute)

    Raises:
        ValueError: If time string is invalid
    """
    parts = time_str.split(":")
    hour = int(parts[0])
    minute = int(parts[1])
    return hour, minute


def normalize_to_midnight(dt: datetime) -> datetime:
    """
    Normalize datetime to midnight (remove time component).

    Args:
        dt: Datetime to normalize

    Returns:
        Datetime set to midnight
    """
    return datetime.combine(dt.date(), datetime.min.time())


def get_effective_date(
    day_start_enabled: bool,
    day_start_time: Optional[str] = None
) -> date:
    """
    Get the effective current date based on day_start_time setting.

    If day_start_enabled is True and current time is before day_start_time,
    returns yesterday's date. Otherwise returns today's date.

    Example: If day_start_time = "06:00" and current time is 03:00,
    the effective date is still yesterday because the user hasn't
    started their "new day" yet.

    Args:
        day_start_enabled: Whether custom day start is enabled
        day_start_time: Time string in "HH:MM" format (default "06:00")

    Returns:
        Effective date (today or yesterday)
    """
    now = datetime.now()
    today = now.date()

    if not day_start_enabled:
        return today

    # Parse day_start_time
    try:
        t_str = day_start_time or "06:00"
        t_str = t_str.replace(":", "")
        t_str = t_str.zfill(4)
        day_start_hour = int(t_str[:2])
        day_start_minute = int(t_str[2:])
    except (ValueError, IndexError, AttributeError):
        return today

    # If current time is before day_start_time, we're still in "yesterday"
    current_minutes = now.hour * 60 + now.minute
    start_minutes = day_start_hour * 60 + day_start_minute

    if current_minutes < start_minutes:
        return today - timedelta(days=1)

    return today


def calculate_next_occurrence(
    start_date: datetime,
    recurrence_type: str,
    recurrence_interval: int = 1,
    recurrence_days: Optional[str] = None
) -> datetime:
    """
    Calculate next occurrence date for recurring habits.
    If start_date is in the past, calculates the next future occurrence.

    Args:
        start_date: Initial/start date for the habit
        recurrence_type: "daily", "every_n_days", "weekly", or "none"
        recurrence_interval: For "every_n_days", the number of days between occurrences
        recurrence_days: For "weekly", JSON array of weekdays [0-6]

    Returns:
        Next occurrence date (today or in the future)
    """
    if recurrence_type == RECURRENCE_NONE or not start_date:
        return start_date

    now = datetime.now()
    current_date = start_date

    # If start_date is already in the future, return it as-is
    if current_date.replace(tzinfo=None) >= now:
        return current_date

    # Calculate next occurrence based on recurrence type
    if recurrence_type == RECURRENCE_DAILY:
        current_date = _calculate_daily_occurrence(current_date, now)
    elif recurrence_type == RECURRENCE_EVERY_N_DAYS:
        current_date = _calculate_every_n_days_occurrence(
            current_date, now, recurrence_interval
        )
    elif recurrence_type == RECURRENCE_WEEKLY:
        current_date = _calculate_weekly_occurrence(
            current_date, now, recurrence_days
        )

    return current_date


def _calculate_daily_occurrence(start_date: datetime, now: datetime) -> datetime:
    """Calculate next daily occurrence."""
    days_diff = (now.date() - start_date.date()).days
    current_date = start_date + timedelta(days=days_diff)

    # If we're past today's time, move to tomorrow
    if current_date.replace(tzinfo=None) < now:
        current_date = current_date + timedelta(days=1)

    return current_date


def _calculate_every_n_days_occurrence(
    start_date: datetime,
    now: datetime,
    interval: int
) -> datetime:
    """Calculate next occurrence for every N days recurrence."""
    days_diff = (now.date() - start_date.date()).days
    # Calculate how many intervals have passed
    intervals_passed = days_diff // interval
    # Add one more interval to get the next future date
    next_interval = (intervals_passed + 1) * interval
    return start_date + timedelta(days=next_interval)


def _calculate_weekly_occurrence(
    start_date: datetime,
    now: datetime,
    recurrence_days: Optional[str]
) -> datetime:
    """Calculate next weekly occurrence."""
    # Parse recurrence_days JSON array like "[0,2,4]" (Mon, Wed, Fri)
    try:
        days = json.loads(recurrence_days) if recurrence_days else []
        if not days:
            # No specific days, default to weekly (every 7 days)
            days_diff = (now.date() - start_date.date()).days
            weeks_passed = days_diff // 7
            return start_date + timedelta(days=(weeks_passed + 1) * 7)

        # Find next occurrence starting from now
        current_date = now.date()
        target_time = start_date.time()

        # Check next 14 days to find the next matching weekday
        for offset in range(0, 14):
            check_date = current_date + timedelta(days=offset)
            if check_date.weekday() in days:
                # If it's today, only accept if we haven't passed the habit time yet
                if offset == 0:
                    habit_datetime_today = datetime.combine(check_date, target_time)
                    if now >= habit_datetime_today:
                        # Time has passed today, skip to next occurrence
                        continue
                return datetime.combine(check_date, target_time)

        # Fallback: just add 7 days
        return start_date + timedelta(days=7)
    except (json.JSONDecodeError, ValueError):
        # Fallback to weekly
        days_diff = (now.date() - start_date.date()).days
        weeks_passed = days_diff // 7
        return start_date + timedelta(days=(weeks_passed + 1) * 7)


def calculate_next_due_date(
    recurrence_type: str,
    from_date: date,
    recurrence_interval: int = 1,
    recurrence_days: Optional[str] = None
) -> Optional[date]:
    """
    Calculate next due date based on recurrence settings.

    Args:
        recurrence_type: Type of recurrence
        from_date: Date to calculate from
        recurrence_interval: Interval for every_n_days
        recurrence_days: JSON array of weekdays for weekly

    Returns:
        Next due date, or None if not recurring
    """
    if recurrence_type == RECURRENCE_NONE:
        return None

    if recurrence_type == RECURRENCE_DAILY:
        return from_date + timedelta(days=1)

    if recurrence_type == RECURRENCE_EVERY_N_DAYS:
        interval = max(1, recurrence_interval or 1)
        return from_date + timedelta(days=interval)

    if recurrence_type == RECURRENCE_WEEKLY:
        # Use existing weekly calculation logic
        start_datetime = datetime.combine(from_date, datetime.min.time())
        next_datetime = _calculate_weekly_occurrence(
            start_datetime,
            start_datetime + timedelta(days=1),  # Force next occurrence
            recurrence_days
        )
        return next_datetime.date()

    return None


def get_day_range(
    target_date: date,
    day_start_enabled: bool = False,
    day_start_time: Optional[str] = None
) -> Tuple[datetime, datetime]:
    """
    Get datetime range for a full day, respecting day_start_time setting.

    If day_start_enabled is True and day_start_time is set (e.g., "06:00"),
    the day runs from that time on target_date to that time on the next date.

    Args:
        target_date: Date to get range for
        day_start_enabled: Whether custom day start is enabled
        day_start_time: Time string in "HH:MM" format

    Returns:
        Tuple of (day_start, day_end) datetimes
    """
    # Default to midnight-to-midnight if day_start not enabled
    if not day_start_enabled:
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date + timedelta(days=1), datetime.min.time())
        return day_start, day_end

    # Parse day_start_time
    try:
        t_str = day_start_time or "06:00"
        hour, minute = parse_time(t_str)
        start_time = time(hour=hour, minute=minute)

        day_start = datetime.combine(target_date, start_time)
        day_end = datetime.combine(target_date + timedelta(days=1), start_time)
        return day_start, day_end
    except (ValueError, IndexError, AttributeError):
        # Fallback to midnight
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date + timedelta(days=1), datetime.min.time())
        return day_start, day_end
