"""
Tests for PenaltyService.

Tests cover:
1. Penalty streak calculation
2. Progressive multiplier
3. Idle penalty
4. Idempotency
5. Rest day handling
6. Complete penalty flow
"""
import pytest
import json
from datetime import date, datetime, timedelta

from backend.modules.penalties.service import PenaltyService
from backend.models import PointHistory, Task, Settings, RestDay
from backend.tests.conftest import create_history_with_penalties


def _make_settings_data(settings):
    """Convert Settings ORM object to dict for PenaltyService."""
    return {
        "idle_penalty": settings.idle_penalty,
        "incomplete_penalty_percent": settings.incomplete_penalty_percent,
        "missed_habit_penalty_base": settings.missed_habit_penalty_base,
        "progressive_penalty_factor": settings.progressive_penalty_factor,
        "progressive_penalty_max": settings.progressive_penalty_max,
        "penalty_streak_reset_days": settings.penalty_streak_reset_days,
        "completion_bonus_full": settings.completion_bonus_full,
        "completion_bonus_good": settings.completion_bonus_good,
    }


def _noop_completed_count(start, end, is_habit=None):
    """Stub for get_completed_count."""
    return 0


def _noop_missed_habits(start, end):
    """Stub for get_missed_habits."""
    return []


def _noop_count_habits_due(start, end):
    """Stub for count_habits_due."""
    return 0


def _noop_roll_forward(habit_data, from_date):
    """Stub for roll_forward_habit."""
    pass


class TestProgressiveMultiplier:
    """Tests for progressive penalty multiplier calculation"""

    def test_first_day_penalty_streak_is_1(self, db_session, default_settings, today):
        """First day with penalties should have streak=1"""
        # Create history for today (no previous history)
        history = PointHistory(
            date=today,
            points_earned=10,
            cumulative_total=100
        )
        db_session.add(history)
        db_session.commit()

        service = PenaltyService(db_session)
        settings_data = _make_settings_data(default_settings)

        penalty, multiplier = service._apply_progressive_multiplier(
            penalty=10,
            target_date=today,
            day_history=history,
            settings_data=settings_data
        )

        assert history.penalty_streak == 1
        assert multiplier == 1.1  # 1 + 1*0.1
        assert penalty == 11  # 10 * 1.1

    def test_consecutive_days_increment_streak(self, db_session, default_settings, today, yesterday):
        """Consecutive days with penalties should increment streak"""
        # Create history for yesterday with streak=3
        create_history_with_penalties(db_session, yesterday, penalty=10, streak=3)

        # Create history for today
        history = PointHistory(date=today, points_earned=10, cumulative_total=100)
        db_session.add(history)
        db_session.commit()

        service = PenaltyService(db_session)
        settings_data = _make_settings_data(default_settings)

        penalty, multiplier = service._apply_progressive_multiplier(
            penalty=10,
            target_date=today,
            day_history=history,
            settings_data=settings_data
        )

        assert history.penalty_streak == 4  # yesterday's 3 + 1
        assert multiplier == 1.4  # 1 + 4*0.1

    def test_multiplier_capped_at_max(self, db_session, default_settings, today, yesterday):
        """Multiplier should not exceed progressive_penalty_max"""
        # Create history for yesterday with streak=10 (way above max)
        create_history_with_penalties(db_session, yesterday, penalty=10, streak=10)

        # Create history for today
        history = PointHistory(date=today, points_earned=10, cumulative_total=100)
        db_session.add(history)
        db_session.commit()

        service = PenaltyService(db_session)
        settings_data = _make_settings_data(default_settings)

        penalty, multiplier = service._apply_progressive_multiplier(
            penalty=10,
            target_date=today,
            day_history=history,
            settings_data=settings_data
        )

        # Max multiplier is 1.5, streak should be 11
        assert history.penalty_streak == 11
        assert multiplier == 1.5  # Capped at max
        assert penalty == 15  # 10 * 1.5

    def test_no_penalty_keeps_previous_streak(self, db_session, default_settings, today, yesterday):
        """Day with no penalties should keep previous streak (not reset yet)"""
        # Create history for yesterday with streak=3
        create_history_with_penalties(db_session, yesterday, penalty=10, streak=3)

        # Create history for today
        history = PointHistory(date=today, points_earned=10, cumulative_total=100)
        db_session.add(history)
        db_session.commit()

        service = PenaltyService(db_session)
        settings_data = _make_settings_data(default_settings)

        # No penalty today
        penalty, multiplier = service._apply_progressive_multiplier(
            penalty=0,
            target_date=today,
            day_history=history,
            settings_data=settings_data
        )

        # With 0 penalty, streak should remain from yesterday
        assert history.penalty_streak == 3
        assert multiplier == 1.0


class TestEffectivePenaltyStreak:
    """Tests for _get_effective_penalty_streak function"""

    def test_streak_from_finalized_days(self, db_session, default_settings, today):
        """Should count streak from finalized days with penalties"""
        # Create 5 days of history with penalties
        for i in range(5):
            target_date = today - timedelta(days=i+1)
            create_history_with_penalties(db_session, target_date, penalty=10, streak=5-i)

        service = PenaltyService(db_session)
        yesterday = today - timedelta(days=1)

        streak = service._get_effective_penalty_streak(yesterday)

        assert streak == 5

    def test_streak_breaks_on_no_penalty(self, db_session, default_settings, today):
        """Streak should break when a day has no penalties"""
        # Day -1: has penalty
        create_history_with_penalties(db_session, today - timedelta(days=1), penalty=10, streak=1)
        # Day -2: NO penalty (breaks streak)
        create_history_with_penalties(db_session, today - timedelta(days=2), penalty=0, streak=0)
        # Day -3: has penalty (old streak)
        create_history_with_penalties(db_session, today - timedelta(days=3), penalty=10, streak=2)

        service = PenaltyService(db_session)
        yesterday = today - timedelta(days=1)

        streak = service._get_effective_penalty_streak(yesterday)

        # Should only count day -1, because day -2 has no penalty
        assert streak == 1


class TestIdlePenalty:
    """Tests for idle penalty calculation"""

    def test_idle_penalty_when_nothing_done(self, db_session, default_settings, today):
        """Should apply idle penalty when 0 tasks AND 0 habits completed"""
        history = PointHistory(
            date=today,
            points_earned=0,
            cumulative_total=100,
            tasks_completed=0,
            habits_completed=0
        )
        db_session.add(history)
        db_session.commit()

        service = PenaltyService(db_session)
        settings_data = _make_settings_data(default_settings)
        idle_penalty = service._calculate_idle_penalty(history, settings_data)

        assert idle_penalty == default_settings.idle_penalty  # 30

    def test_no_idle_penalty_when_tasks_done(self, db_session, default_settings, today):
        """Should NOT apply idle penalty if any tasks completed"""
        history = PointHistory(
            date=today,
            points_earned=10,
            cumulative_total=110,
            tasks_completed=1,
            habits_completed=0
        )
        db_session.add(history)
        db_session.commit()

        service = PenaltyService(db_session)
        settings_data = _make_settings_data(default_settings)
        idle_penalty = service._calculate_idle_penalty(history, settings_data)

        assert idle_penalty == 0

    def test_no_idle_penalty_when_habits_done(self, db_session, default_settings, today):
        """Should NOT apply idle penalty if any habits completed"""
        history = PointHistory(
            date=today,
            points_earned=10,
            cumulative_total=110,
            tasks_completed=0,
            habits_completed=1
        )
        db_session.add(history)
        db_session.commit()

        service = PenaltyService(db_session)
        settings_data = _make_settings_data(default_settings)
        idle_penalty = service._calculate_idle_penalty(history, settings_data)

        assert idle_penalty == 0


class TestIdempotency:
    """Tests for idempotency of penalty finalization"""

    def test_already_finalized_returns_existing(self, db_session, default_settings, today):
        """Should return existing values if already finalized"""
        # Create already finalized history
        history = PointHistory(
            date=today,
            points_earned=20,
            points_penalty=15,  # Already has penalty
            cumulative_total=105,
            tasks_completed=2,
            tasks_planned=3,
            completion_rate=0.67
        )
        db_session.add(history)
        db_session.commit()

        service = PenaltyService(db_session)
        settings_data = _make_settings_data(default_settings)

        result = service.finalize_day_penalties(
            target_date=today,
            is_rest_day=False,
            day_start_enabled=False,
            day_start_time="06:00",
            settings_data=settings_data,
            get_completed_count=_noop_completed_count,
            get_missed_habits=_noop_missed_habits,
            count_habits_due=_noop_count_habits_due,
            roll_forward_habit=_noop_roll_forward,
        )

        assert result["already_finalized"] == True
        assert result["penalty"] == 15


class TestCompletePenaltyFlow:
    """Integration tests for complete penalty calculation flow"""

    def test_full_finalization_flow(self, db_session, default_settings, today):
        """Test complete finalization including all penalty types"""
        # Create history with no activity
        history = PointHistory(
            date=today,
            points_earned=0,
            cumulative_total=100,
            tasks_completed=0,
            habits_completed=0,
            tasks_planned=0
        )
        db_session.add(history)
        db_session.commit()

        service = PenaltyService(db_session)
        settings_data = _make_settings_data(default_settings)

        result = service.finalize_day_penalties(
            target_date=today,
            is_rest_day=False,
            day_start_enabled=False,
            day_start_time="06:00",
            settings_data=settings_data,
            get_completed_count=_noop_completed_count,
            get_missed_habits=_noop_missed_habits,
            count_habits_due=_noop_count_habits_due,
            roll_forward_habit=_noop_roll_forward,
        )

        # Should have idle penalty at minimum
        assert result["penalty"] >= default_settings.idle_penalty

        # Verify history was updated
        db_session.refresh(history)
        assert history.points_penalty > 0
        assert history.penalty_streak == 1  # First penalty day

    def test_penalty_breakdown_saved(self, db_session, default_settings, today):
        """Test that penalty breakdown is saved to details"""
        history = PointHistory(
            date=today,
            points_earned=0,
            cumulative_total=100,
            tasks_completed=0,
            habits_completed=0
        )
        db_session.add(history)
        db_session.commit()

        service = PenaltyService(db_session)
        settings_data = _make_settings_data(default_settings)

        service.finalize_day_penalties(
            target_date=today,
            is_rest_day=False,
            day_start_enabled=False,
            day_start_time="06:00",
            settings_data=settings_data,
            get_completed_count=_noop_completed_count,
            get_missed_habits=_noop_missed_habits,
            count_habits_due=_noop_count_habits_due,
            roll_forward_habit=_noop_roll_forward,
        )

        db_session.refresh(history)
        assert history.details is not None

        details = json.loads(history.details)
        assert "penalty_breakdown" in details
        assert "idle_penalty" in details["penalty_breakdown"]
        assert "progressive_multiplier" in details["penalty_breakdown"]
        assert "penalty_streak" in details["penalty_breakdown"]

    def test_cumulative_total_updated(self, db_session, default_settings, today):
        """Test that cumulative total is updated after penalties"""
        initial_cumulative = 100
        history = PointHistory(
            date=today,
            points_earned=0,
            cumulative_total=initial_cumulative,
            tasks_completed=0,
            habits_completed=0
        )
        db_session.add(history)
        db_session.commit()

        service = PenaltyService(db_session)
        settings_data = _make_settings_data(default_settings)

        result = service.finalize_day_penalties(
            target_date=today,
            is_rest_day=False,
            day_start_enabled=False,
            day_start_time="06:00",
            settings_data=settings_data,
            get_completed_count=_noop_completed_count,
            get_missed_habits=_noop_missed_habits,
            count_habits_due=_noop_count_habits_due,
            roll_forward_habit=_noop_roll_forward,
        )

        db_session.refresh(history)

        # Cumulative should decrease by penalty (but not go below 0)
        expected = max(0, initial_cumulative - result["penalty"])
        assert history.cumulative_total == expected


class TestRestDays:
    """Tests for rest day handling"""

    def test_no_penalties_on_rest_day(self, db_session, default_settings, today):
        """Should not apply penalties on rest days"""
        # Create history with no activity
        history = PointHistory(
            date=today,
            points_earned=0,
            cumulative_total=100,
            tasks_completed=0,
            habits_completed=0
        )
        db_session.add(history)
        db_session.commit()

        service = PenaltyService(db_session)
        settings_data = _make_settings_data(default_settings)

        result = service.finalize_day_penalties(
            target_date=today,
            is_rest_day=True,  # This is a rest day
            day_start_enabled=False,
            day_start_time="06:00",
            settings_data=settings_data,
            get_completed_count=_noop_completed_count,
            get_missed_habits=_noop_missed_habits,
            count_habits_due=_noop_count_habits_due,
            roll_forward_habit=_noop_roll_forward,
        )

        assert result["penalty"] == 0
        assert result["is_rest_day"] == True
