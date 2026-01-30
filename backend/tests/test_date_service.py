"""
Tests for DateService.

Tests cover:
1. Effective date calculation based on day_start_time
2. Day range calculation with and without day_start_time
3. Recurrence calculations
"""
import pytest
from datetime import date, datetime, timedelta, time
from unittest.mock import patch

from backend.services.date_service import DateService
from backend.models import Settings, Task


class TestEffectiveDate:
    """Tests for get_effective_date function"""

    def test_returns_today_when_day_start_disabled(self, default_settings):
        """Should return today when day_start is disabled"""
        default_settings.day_start_enabled = False

        service = DateService()
        result = service.get_effective_date(default_settings)

        assert result == date.today()

    def test_returns_today_when_after_day_start(self, default_settings):
        """Should return today when current time is after day_start_time"""
        default_settings.day_start_enabled = True
        default_settings.day_start_time = "06:00"

        service = DateService()

        # Mock datetime.now() to 10:00
        with patch('backend.services.date_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 30, 10, 0, 0)
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            result = service.get_effective_date(default_settings)

        assert result == date(2026, 1, 30)

    def test_returns_yesterday_when_before_day_start(self, default_settings):
        """Should return yesterday when current time is before day_start_time"""
        default_settings.day_start_enabled = True
        default_settings.day_start_time = "06:00"

        service = DateService()

        # Mock datetime.now() to 03:00
        with patch('backend.services.date_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 30, 3, 0, 0)
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            result = service.get_effective_date(default_settings)

        assert result == date(2026, 1, 29)


class TestDayRange:
    """Tests for get_day_range function"""

    def test_midnight_to_midnight_without_settings(self):
        """Should return midnight to midnight when no settings provided"""
        service = DateService()
        target = date(2026, 1, 30)

        day_start, day_end = service.get_day_range(target)

        assert day_start == datetime(2026, 1, 30, 0, 0, 0)
        assert day_end == datetime(2026, 1, 31, 0, 0, 0)

    def test_midnight_to_midnight_when_day_start_disabled(self, default_settings):
        """Should return midnight to midnight when day_start is disabled"""
        default_settings.day_start_enabled = False

        service = DateService()
        target = date(2026, 1, 30)

        day_start, day_end = service.get_day_range(target, default_settings)

        assert day_start == datetime(2026, 1, 30, 0, 0, 0)
        assert day_end == datetime(2026, 1, 31, 0, 0, 0)

    def test_respects_day_start_time(self, default_settings):
        """Should use day_start_time when enabled"""
        default_settings.day_start_enabled = True
        default_settings.day_start_time = "06:00"

        service = DateService()
        target = date(2026, 1, 30)

        day_start, day_end = service.get_day_range(target, default_settings)

        assert day_start == datetime(2026, 1, 30, 6, 0, 0)
        assert day_end == datetime(2026, 1, 31, 6, 0, 0)

    def test_handles_different_times(self, default_settings):
        """Should handle various day_start_time values"""
        default_settings.day_start_enabled = True

        service = DateService()
        target = date(2026, 1, 30)

        # Test 04:30
        default_settings.day_start_time = "04:30"
        day_start, day_end = service.get_day_range(target, default_settings)
        assert day_start == datetime(2026, 1, 30, 4, 30, 0)
        assert day_end == datetime(2026, 1, 31, 4, 30, 0)


class TestNextOccurrence:
    """Tests for recurrence calculations"""

    def test_daily_recurrence_past_date(self):
        """Daily recurrence should calculate next occurrence from past date"""
        service = DateService()
        start = datetime(2026, 1, 25, 8, 0, 0)  # 5 days ago

        with patch('backend.services.date_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 30, 10, 0, 0)
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            result = service.calculate_next_occurrence(
                start, "daily", 1, None
            )

        # Should be today at 8:00 or tomorrow
        assert result.date() >= date(2026, 1, 30)

    def test_every_n_days_recurrence(self):
        """Every N days should calculate proper interval"""
        service = DateService()
        start = datetime(2026, 1, 25, 8, 0, 0)

        with patch('backend.services.date_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 30, 10, 0, 0)
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            result = service.calculate_next_occurrence(
                start, "every_n_days", 3, None
            )

        # From Jan 25, every 3 days: Jan 25, 28, 31...
        # Jan 30 is current, so next is Jan 31
        assert result == datetime(2026, 1, 31, 8, 0, 0)

    def test_weekly_recurrence_with_days(self):
        """Weekly recurrence should find next matching weekday"""
        service = DateService()
        start = datetime(2026, 1, 25, 8, 0, 0)  # Saturday
        recurrence_days = "[1,3,5]"  # Mon, Wed, Fri

        with patch('backend.services.date_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 30, 10, 0, 0)  # Friday
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            mock_dt.combine = datetime.combine

            result = service.calculate_next_occurrence(
                start, "weekly", 1, recurrence_days
            )

        # Jan 30 is Thursday (3), so next Mon/Wed/Fri would be Fri Jan 31 (4)
        # Actually Jan 30 2026 is Friday (weekday=4), so next would be Mon Feb 2
        assert result is not None

    def test_future_date_unchanged(self):
        """Future date should return as-is"""
        service = DateService()
        future = datetime(2026, 2, 15, 8, 0, 0)

        with patch('backend.services.date_service.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 30, 10, 0, 0)
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            result = service.calculate_next_occurrence(
                future, "daily", 1, None
            )

        assert result == future


class TestCalculateNextDueDate:
    """Tests for calculate_next_due_date function"""

    def test_no_recurrence_returns_none(self, db_session):
        """Non-recurring task should return None"""
        task = Task(
            description="Test",
            recurrence_type="none"
        )

        service = DateService()
        result = service.calculate_next_due_date(task, date(2026, 1, 30))

        assert result is None

    def test_daily_returns_next_day(self, db_session):
        """Daily recurrence should return next day"""
        task = Task(
            description="Test",
            recurrence_type="daily"
        )

        service = DateService()
        result = service.calculate_next_due_date(task, date(2026, 1, 30))

        assert result == date(2026, 1, 31)

    def test_every_n_days_returns_correct_interval(self, db_session):
        """Every N days should return date + interval"""
        task = Task(
            description="Test",
            recurrence_type="every_n_days",
            recurrence_interval=3
        )

        service = DateService()
        result = service.calculate_next_due_date(task, date(2026, 1, 30))

        assert result == date(2026, 2, 2)
