"""
Date calculation and manipulation service.
Handles effective dates, day start time logic, and recurrence calculations.
"""
from datetime import datetime, timedelta, date
from typing import Optional
import json

from backend.models import Settings, Task
from backend.constants import (
    RECURRENCE_NONE, RECURRENCE_DAILY, RECURRENCE_EVERY_N_DAYS, RECURRENCE_WEEKLY
)


class DateService:
    """Service for date-related operations"""

    @staticmethod
    def get_effective_date(settings: Settings) -> date:
        """
        Get the effective current date based on day_start_time setting.

        If day_start_enabled is True and current time is before day_start_time,
        returns yesterday's date. Otherwise returns today's date.

        Example: If day_start_time = "06:00" and current time is 03:00,
        the effective date is still yesterday because the user hasn't
        started their "new day" yet.

        Args:
            settings: Settings object containing day_start configuration

        Returns:
            Effective date (today or yesterday)
        """
        now = datetime.now()
        today = now.date()

        if not settings.day_start_enabled:
            return today

        # Parse day_start_time
        try:
            t_str = settings.day_start_time or "06:00"
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

    @staticmethod
    def parse_time(time_str: str) -> tuple[int, int]:
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

    @staticmethod
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
            current_date = DateService._calculate_daily_occurrence(current_date, now)
        elif recurrence_type == RECURRENCE_EVERY_N_DAYS:
            current_date = DateService._calculate_every_n_days_occurrence(
                current_date, now, recurrence_interval
            )
        elif recurrence_type == RECURRENCE_WEEKLY:
            current_date = DateService._calculate_weekly_occurrence(
                current_date, now, recurrence_days
            )

        return current_date

    @staticmethod
    def _calculate_daily_occurrence(start_date: datetime, now: datetime) -> datetime:
        """Calculate next daily occurrence"""
        days_diff = (now.date() - start_date.date()).days
        current_date = start_date + timedelta(days=days_diff)

        # If we're past today's time, move to tomorrow
        if current_date.replace(tzinfo=None) < now:
            current_date = current_date + timedelta(days=1)

        return current_date

    @staticmethod
    def _calculate_every_n_days_occurrence(
        start_date: datetime,
        now: datetime,
        interval: int
    ) -> datetime:
        """Calculate next occurrence for every N days recurrence"""
        days_diff = (now.date() - start_date.date()).days
        # Calculate how many intervals have passed
        intervals_passed = days_diff // interval
        # Add one more interval to get the next future date
        next_interval = (intervals_passed + 1) * interval
        return start_date + timedelta(days=next_interval)

    @staticmethod
    def _calculate_weekly_occurrence(
        start_date: datetime,
        now: datetime,
        recurrence_days: Optional[str]
    ) -> datetime:
        """Calculate next weekly occurrence"""
        # Parse recurrence_days JSON array like "[0,2,4]" (Mon, Wed, Fri)
        try:
            days = json.loads(recurrence_days) if recurrence_days else []
            if not days:
                # No specific days, default to weekly (every 7 days)
                days_diff = (now.date() - start_date.date()).days
                weeks_passed = days_diff // 7
                return start_date + timedelta(days=(weeks_passed + 1) * 7)

            # Find next occurrence starting from today
            current_date = now.date()
            # Check next 14 days to find the next matching weekday
            for offset in range(0, 14):
                check_date = current_date + timedelta(days=offset)
                if check_date.weekday() in days:
                    # If it's today, only accept if we haven't passed the time yet
                    if offset == 0 and now >= start_date.replace(tzinfo=None):
                        continue
                    return datetime.combine(check_date, start_date.time())

            # Fallback: just add 7 days
            return start_date + timedelta(days=7)
        except (json.JSONDecodeError, ValueError):
            # Fallback to weekly
            days_diff = (now.date() - start_date.date()).days
            weeks_passed = days_diff // 7
            return start_date + timedelta(days=(weeks_passed + 1) * 7)

    @staticmethod
    def calculate_next_due_date(
        task: Task,
        from_date: date
    ) -> Optional[date]:
        """
        Calculate next due date based on task's recurrence settings.

        Args:
            task: Task with recurrence settings
            from_date: Date to calculate from

        Returns:
            Next due date, or None if not recurring
        """
        if task.recurrence_type == RECURRENCE_NONE:
            return None

        if task.recurrence_type == RECURRENCE_DAILY:
            return from_date + timedelta(days=1)

        if task.recurrence_type == RECURRENCE_EVERY_N_DAYS:
            interval = max(1, task.recurrence_interval or 1)
            return from_date + timedelta(days=interval)

        if task.recurrence_type == RECURRENCE_WEEKLY:
            # Use existing weekly calculation logic
            start_datetime = datetime.combine(from_date, datetime.min.time())
            next_datetime = DateService._calculate_weekly_occurrence(
                start_datetime,
                start_datetime + timedelta(days=1),  # Force next occurrence
                task.recurrence_days
            )
            return next_datetime.date()

        return None

    @staticmethod
    def normalize_to_midnight(dt: datetime) -> datetime:
        """
        Normalize datetime to midnight (remove time component).

        Args:
            dt: Datetime to normalize

        Returns:
            Datetime set to midnight
        """
        return datetime.combine(dt.date(), datetime.min.time())

    @staticmethod
    def get_day_range(target_date: date) -> tuple[datetime, datetime]:
        """
        Get datetime range for a full day (midnight to midnight).

        Args:
            target_date: Date to get range for

        Returns:
            Tuple of (day_start, day_end) datetimes
        """
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date + timedelta(days=1), datetime.min.time())
        return day_start, day_end
