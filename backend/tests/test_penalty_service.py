"""
Tests for PenaltyService.

Tests cover:
1. Penalty streak calculation
2. Progressive multiplier
3. Missing days finalization
4. Idle penalty
5. Incomplete day penalty
6. Missed habits penalty
7. Idempotency
"""
import pytest
import json
from datetime import date, datetime, timedelta

from backend.services.penalty_service import PenaltyService
from backend.models import PointHistory, Task, Settings, RestDay
from backend.tests.conftest import create_history_with_penalties


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

        # Manually test the multiplier function
        penalty, multiplier = service._apply_progressive_multiplier(
            penalty=10,
            target_date=today,
            day_history=history,
            settings=default_settings
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

        penalty, multiplier = service._apply_progressive_multiplier(
            penalty=10,
            target_date=today,
            day_history=history,
            settings=default_settings
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

        penalty, multiplier = service._apply_progressive_multiplier(
            penalty=10,
            target_date=today,
            day_history=history,
            settings=default_settings
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

        # No penalty today
        penalty, multiplier = service._apply_progressive_multiplier(
            penalty=0,
            target_date=today,
            day_history=history,
            settings=default_settings
        )

        # With 1 day without penalty (today), streak should remain from yesterday
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

        streak = service._get_effective_penalty_streak(yesterday, default_settings)

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

        streak = service._get_effective_penalty_streak(yesterday, default_settings)

        # Should only count day -1, because day -2 has no penalty
        assert streak == 1


class TestMissingDaysFinalization:
    """Tests for _finalize_missing_days function"""

    def test_no_missing_days_when_all_finalized(self, db_session, default_settings, today, yesterday):
        """Should not finalize anything if previous day is finalized"""
        # Create finalized history for yesterday
        create_history_with_penalties(db_session, yesterday, penalty=10, streak=1)

        service = PenaltyService(db_session)
        service._finalize_missing_days(today)

        # Yesterday should remain unchanged
        history = db_session.query(PointHistory).filter(PointHistory.date == yesterday).first()
        assert history.points_penalty == 10
        assert history.penalty_streak == 1

    def test_finalizes_missing_days_in_order(self, db_session, default_settings, today):
        """Should finalize missing days in chronological order"""
        # Create unfinalized history for 3 days ago (has history but no penalty breakdown)
        day_3 = today - timedelta(days=3)
        create_history_with_penalties(db_session, day_3, penalty=10, streak=1)

        # Create unfinalized history for 2 days ago
        day_2 = today - timedelta(days=2)
        history_2 = PointHistory(
            date=day_2,
            points_earned=0,
            cumulative_total=90,
            tasks_completed=0,
            habits_completed=0
        )
        db_session.add(history_2)

        # Create unfinalized history for yesterday
        day_1 = today - timedelta(days=1)
        history_1 = PointHistory(
            date=day_1,
            points_earned=0,
            cumulative_total=90,
            tasks_completed=0,
            habits_completed=0
        )
        db_session.add(history_1)
        db_session.commit()

        service = PenaltyService(db_session)
        service._finalize_missing_days(today)

        # Check that day_2 was finalized with correct streak
        history_2_updated = db_session.query(PointHistory).filter(PointHistory.date == day_2).first()
        assert history_2_updated.points_penalty > 0 or history_2_updated.details is not None

        # Check that day_1 was finalized with streak incremented from day_2
        history_1_updated = db_session.query(PointHistory).filter(PointHistory.date == day_1).first()
        assert history_1_updated.penalty_streak >= history_2_updated.penalty_streak


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
        idle_penalty = service._calculate_idle_penalty(history, default_settings)

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
        idle_penalty = service._calculate_idle_penalty(history, default_settings)

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
        idle_penalty = service._calculate_idle_penalty(history, default_settings)

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
        result = service._finalize_single_day(today)

        assert result["already_finalized"] == True
        assert result["penalty"] == 15

    def test_finalization_sets_values(self, db_session, default_settings, today):
        """Should set penalty values on first finalization"""
        # Create unfinalized history
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
        result = service._finalize_single_day(today)

        assert "already_finalized" not in result or result.get("already_finalized") == False
        assert result["penalty"] > 0  # Should have idle penalty


class TestPenaltyStreakReset:
    """Tests for penalty streak reset logic"""

    def test_streak_resets_after_n_days_without_penalty(self, db_session, default_settings, today):
        """Streak should reset after penalty_streak_reset_days without penalties"""
        # penalty_streak_reset_days = 2
        # Create 2 days without penalties
        day_2 = today - timedelta(days=2)
        create_history_with_penalties(db_session, day_2, penalty=0, streak=3)

        day_1 = today - timedelta(days=1)
        create_history_with_penalties(db_session, day_1, penalty=0, streak=3)

        # Create history for today
        history = PointHistory(date=today, points_earned=10, cumulative_total=100)
        db_session.add(history)
        db_session.commit()

        service = PenaltyService(db_session)
        yesterday_history = db_session.query(PointHistory).filter(PointHistory.date == day_1).first()

        # No penalty today
        service._update_penalty_streak(
            history,
            yesterday_history,
            default_settings,
            day_1
        )

        # After 2+ days without penalty, streak should reset to 0
        # Today + yesterday = 2 days without penalty
        assert history.penalty_streak == 0


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
        result = service.finalize_day_penalties(today)

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
        service.finalize_day_penalties(today)

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
        result = service.finalize_day_penalties(today)

        db_session.refresh(history)

        # Cumulative should decrease by penalty (but not go below 0)
        expected = max(0, initial_cumulative - result["penalty"])
        assert history.cumulative_total == expected


class TestRestDays:
    """Tests for rest day handling"""

    def test_no_penalties_on_rest_day(self, db_session, default_settings, today):
        """Should not apply penalties on rest days"""
        # Create rest day
        rest_day = RestDay(date=today, description="Weekend")
        db_session.add(rest_day)

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
        result = service.finalize_day_penalties(today)

        assert result["penalty"] == 0
        assert result["is_rest_day"] == True


class TestMissedDaysWithoutHistory:
    """Tests for handling missed days when user didn't open the app"""

    def test_creates_history_for_missed_day_with_habits(self, db_session, default_settings, today):
        """Should create history and apply penalties for missed days with habits due"""
        from datetime import datetime

        # Create a habit that was due 2 days ago (user didn't open app)
        missed_day = today - timedelta(days=2)
        habit = Task(
            description="Daily habit",
            is_habit=True,
            status="pending",
            recurrence_type="daily",
            habit_type="skill",
            due_date=datetime.combine(missed_day, datetime.min.time()),
            created_at=datetime.now()
        )
        db_session.add(habit)
        db_session.commit()

        # Finalize penalties for today (should process missed day first)
        service = PenaltyService(db_session)
        service._finalize_missing_days(today)

        # Check that history was created for missed day
        missed_history = db_session.query(PointHistory).filter(PointHistory.date == missed_day).first()
        assert missed_history is not None
        assert missed_history.points_penalty > 0

        # Check that penalty breakdown includes missed habits
        details = json.loads(missed_history.details)
        assert "penalty_breakdown" in details
        assert details["penalty_breakdown"]["idle_penalty"] == default_settings.idle_penalty
        assert details["penalty_breakdown"]["missed_habits_penalty"] > 0
        assert details["penalty_breakdown"]["auto_finalized"] == True

    def test_habits_rolled_forward_after_missed_day(self, db_session, default_settings, today):
        """Habits should be rolled forward to next occurrence after being marked as missed"""
        from datetime import datetime

        # Create a daily habit that was due 2 days ago
        missed_day = today - timedelta(days=2)
        habit = Task(
            description="Daily habit to roll",
            is_habit=True,
            status="pending",
            recurrence_type="daily",
            habit_type="skill",
            due_date=datetime.combine(missed_day, datetime.min.time()),
            streak=5,  # Had a streak
            created_at=datetime.now()
        )
        db_session.add(habit)
        db_session.commit()

        original_habit_id = habit.id

        # Finalize missing days
        service = PenaltyService(db_session)
        service._finalize_missing_days(today)

        # Original habit should be deleted
        old_habit = db_session.query(Task).filter(Task.id == original_habit_id).first()
        assert old_habit is None

        # New habit should exist with next due date and reset streak
        new_habit = db_session.query(Task).filter(
            Task.description == "Daily habit to roll",
            Task.is_habit == True
        ).first()
        assert new_habit is not None
        assert new_habit.due_date.date() > missed_day
        assert new_habit.streak == 0  # Streak reset because habit was missed

    def test_multiple_missed_days_all_penalized(self, db_session, default_settings, today):
        """Multiple consecutive missed days should all receive penalties"""
        from datetime import datetime

        # Create a daily habit due 3 days ago
        day_3 = today - timedelta(days=3)
        habit = Task(
            description="Daily habit",
            is_habit=True,
            status="pending",
            recurrence_type="daily",
            habit_type="skill",
            due_date=datetime.combine(day_3, datetime.min.time()),
            created_at=datetime.now()
        )
        db_session.add(habit)
        db_session.commit()

        # Finalize missing days
        service = PenaltyService(db_session)
        service._finalize_missing_days(today)

        # Check that history exists for day_3
        history_3 = db_session.query(PointHistory).filter(PointHistory.date == day_3).first()
        assert history_3 is not None
        assert history_3.points_penalty > 0

        # Day 2 should also have a penalty (habit was rolled forward to it)
        day_2 = today - timedelta(days=2)
        history_2 = db_session.query(PointHistory).filter(PointHistory.date == day_2).first()
        assert history_2 is not None
        assert history_2.points_penalty > 0

        # Check penalty streaks increment correctly
        assert history_2.penalty_streak > history_3.penalty_streak

    def test_non_recurring_habits_not_rolled_forward(self, db_session, default_settings, today):
        """Non-recurring habits should be counted as missed but not rolled forward"""
        from datetime import datetime

        # Create a non-recurring habit due 2 days ago
        missed_day = today - timedelta(days=2)
        habit = Task(
            description="One-time habit",
            is_habit=True,
            status="pending",
            recurrence_type="none",  # Non-recurring
            habit_type="skill",
            due_date=datetime.combine(missed_day, datetime.min.time()),
            created_at=datetime.now()
        )
        db_session.add(habit)
        db_session.commit()

        original_habit_id = habit.id

        # Finalize missing days
        service = PenaltyService(db_session)
        service._finalize_missing_days(today)

        # History should exist with penalty
        missed_history = db_session.query(PointHistory).filter(PointHistory.date == missed_day).first()
        assert missed_history is not None
        assert missed_history.points_penalty > 0

        # Non-recurring habit should be deleted (not rolled forward)
        old_habit = db_session.query(Task).filter(Task.id == original_habit_id).first()
        assert old_habit is None

        # No new habit should be created
        habits = db_session.query(Task).filter(
            Task.description == "One-time habit",
            Task.is_habit == True
        ).all()
        assert len(habits) == 0

    def test_progressive_multiplier_across_missed_days(self, db_session, default_settings, today):
        """Progressive penalty multiplier should increase across consecutive missed days"""
        from datetime import datetime

        # Create a daily habit due 3 days ago
        day_3 = today - timedelta(days=3)
        habit = Task(
            description="Daily habit for multiplier test",
            is_habit=True,
            status="pending",
            recurrence_type="daily",
            habit_type="skill",
            due_date=datetime.combine(day_3, datetime.min.time()),
            created_at=datetime.now()
        )
        db_session.add(habit)
        db_session.commit()

        # Finalize missing days
        service = PenaltyService(db_session)
        service._finalize_missing_days(today)

        # Check progressive multipliers
        day_2 = today - timedelta(days=2)
        day_1 = today - timedelta(days=1)

        history_3 = db_session.query(PointHistory).filter(PointHistory.date == day_3).first()
        history_2 = db_session.query(PointHistory).filter(PointHistory.date == day_2).first()
        history_1 = db_session.query(PointHistory).filter(PointHistory.date == day_1).first()

        # Penalty streaks should increment: 1, 2, 3
        if history_3:
            assert history_3.penalty_streak == 1
        if history_2:
            assert history_2.penalty_streak == 2
        if history_1:
            assert history_1.penalty_streak == 3
