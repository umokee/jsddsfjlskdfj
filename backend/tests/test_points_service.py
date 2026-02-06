"""
Tests for PointsService.

Tests cover:
1. Task points calculation
2. Habit points calculation with streak bonus
3. History management
4. Completion points tracking
"""
import pytest
from datetime import date, datetime, timedelta

from backend.modules.points.service import PointsService
from backend.models import Task, PointHistory, Settings


class TestTaskPointsCalculation:
    """Tests for calculate_task_points function"""

    def test_base_points_with_energy_multiplier(self, db_session, default_settings):
        """Should apply energy multiplier to base points"""
        service = PointsService(db_session)
        result = service.calculate_task_points(
            energy=3,  # E3 -> mult = 0.6 + 3*0.2 = 1.2
            time_spent=3600,  # 60 minutes (normal range for E3)
            started_at=datetime.now() - timedelta(minutes=60),
            points_per_task_base=default_settings.points_per_task_base,
            energy_mult_base=default_settings.energy_mult_base,
            energy_mult_step=default_settings.energy_mult_step,
            minutes_per_energy_unit=default_settings.minutes_per_energy_unit,
            min_work_time_seconds=default_settings.min_work_time_seconds,
        )

        # Base 10 * 1.2 energy = 12
        # Time quality should be 1.0 (60 min for E3 = expected)
        # Focus factor 1.0 (started properly)
        assert result.points == 12

    def test_low_energy_reduces_points(self, db_session, default_settings):
        """Low energy tasks should give fewer points"""
        service = PointsService(db_session)
        result = service.calculate_task_points(
            energy=0,  # E0 -> mult = 0.6
            time_spent=300,
            started_at=datetime.now() - timedelta(minutes=5),
            points_per_task_base=default_settings.points_per_task_base,
            energy_mult_base=default_settings.energy_mult_base,
            energy_mult_step=default_settings.energy_mult_step,
            minutes_per_energy_unit=default_settings.minutes_per_energy_unit,
            min_work_time_seconds=default_settings.min_work_time_seconds,
        )

        # Base 10 * 0.6 = 6
        assert result.points == 6

    def test_high_energy_increases_points(self, db_session, default_settings):
        """High energy tasks should give more points"""
        service = PointsService(db_session)
        result = service.calculate_task_points(
            energy=5,  # E5 -> mult = 0.6 + 5*0.2 = 1.6
            time_spent=6000,  # 100 minutes (normal range for E5)
            started_at=datetime.now() - timedelta(minutes=100),
            points_per_task_base=default_settings.points_per_task_base,
            energy_mult_base=default_settings.energy_mult_base,
            energy_mult_step=default_settings.energy_mult_step,
            minutes_per_energy_unit=default_settings.minutes_per_energy_unit,
            min_work_time_seconds=default_settings.min_work_time_seconds,
        )

        # Base 10 * 1.6 = 16
        assert result.points == 16

    def test_suspiciously_fast_completion(self, db_session, default_settings):
        """Completing too fast should reduce points"""
        service = PointsService(db_session)
        result = service.calculate_task_points(
            energy=3,
            time_spent=60,  # Only 1 minute (below min_work_time of 120s)
            started_at=datetime.now() - timedelta(minutes=1),
            points_per_task_base=default_settings.points_per_task_base,
            energy_mult_base=default_settings.energy_mult_base,
            energy_mult_step=default_settings.energy_mult_step,
            minutes_per_energy_unit=default_settings.minutes_per_energy_unit,
            min_work_time_seconds=default_settings.min_work_time_seconds,
        )

        # Base 10 * 1.2 energy * 0.5 time quality = 6
        assert result.points == 6

    def test_no_start_reduces_points(self, db_session, default_settings):
        """Completing without starting should reduce points (focus penalty)"""
        service = PointsService(db_session)
        result = service.calculate_task_points(
            energy=3,
            time_spent=3600,  # 60 minutes (normal range for E3)
            started_at=None,  # Never started - this is the focus penalty
            points_per_task_base=default_settings.points_per_task_base,
            energy_mult_base=default_settings.energy_mult_base,
            energy_mult_step=default_settings.energy_mult_step,
            minutes_per_energy_unit=default_settings.minutes_per_energy_unit,
            min_work_time_seconds=default_settings.min_work_time_seconds,
        )

        # Base 10 * 1.2 energy * 0.8 focus = 9.6 -> 9
        assert result.points == 9

    def test_minimum_one_point(self, db_session, default_settings):
        """Should never give less than 1 point"""
        service = PointsService(db_session)
        result = service.calculate_task_points(
            energy=0,  # Lowest energy
            time_spent=1,  # Suspiciously fast
            started_at=None,  # No focus
            points_per_task_base=default_settings.points_per_task_base,
            energy_mult_base=default_settings.energy_mult_base,
            energy_mult_step=default_settings.energy_mult_step,
            minutes_per_energy_unit=default_settings.minutes_per_energy_unit,
            min_work_time_seconds=default_settings.min_work_time_seconds,
        )

        # Even with all penalties, minimum is 1
        assert result.points >= 1


class TestHabitPointsCalculation:
    """Tests for calculate_habit_points function"""

    def test_routine_gets_fixed_points(self, db_session, default_settings):
        """Routine habits should get fixed points, no streak bonus"""
        service = PointsService(db_session)
        points = service.calculate_habit_points(
            habit_type="routine",
            streak=10,  # High streak should not affect routines
            points_per_habit_base=default_settings.points_per_habit_base,
            routine_points_fixed=default_settings.routine_points_fixed,
            streak_log_factor=default_settings.streak_log_factor,
        )

        assert points == default_settings.routine_points_fixed  # 6

    def test_skill_habit_with_streak_bonus(self, db_session, default_settings):
        """Skill habits should get streak bonus"""
        service = PointsService(db_session)
        points = service.calculate_habit_points(
            habit_type="skill",
            streak=7,
            points_per_habit_base=default_settings.points_per_habit_base,
            routine_points_fixed=default_settings.routine_points_fixed,
            streak_log_factor=default_settings.streak_log_factor,
        )

        # Base 10 * (1 + log2(8) * 0.15) = 10 * (1 + 3 * 0.15) = 10 * 1.45 = 14.5 -> 14
        assert points > default_settings.points_per_habit_base

    def test_skill_habit_no_streak(self, db_session, default_settings):
        """Skill habit with 0 streak should still get base points"""
        service = PointsService(db_session)
        points = service.calculate_habit_points(
            habit_type="skill",
            streak=0,
            points_per_habit_base=default_settings.points_per_habit_base,
            routine_points_fixed=default_settings.routine_points_fixed,
            streak_log_factor=default_settings.streak_log_factor,
        )

        # Base 10 * (1 + log2(1) * 0.15) = 10 * (1 + 0) = 10
        assert points == default_settings.points_per_habit_base


class TestHistoryManagement:
    """Tests for history management functions"""

    def test_get_or_create_creates_new(self, db_session, default_settings, today):
        """Should create new history if none exists"""
        # Ensure no history exists
        existing = db_session.query(PointHistory).filter(
            PointHistory.date == today
        ).first()
        assert existing is None

        service = PointsService(db_session)
        history = service.get_or_create_today_history(today)

        assert history is not None
        assert history.date == today
        assert history.points_earned == 0

    def test_get_or_create_returns_existing(self, db_session, default_settings, today):
        """Should return existing history if it exists"""
        # Create existing history
        existing = PointHistory(
            date=today,
            points_earned=100,
            cumulative_total=500
        )
        db_session.add(existing)
        db_session.commit()

        service = PointsService(db_session)
        history = service.get_or_create_today_history(today)

        assert history.id == existing.id
        assert history.points_earned == 100

    def test_inherits_cumulative_total(self, db_session, default_settings, today, yesterday):
        """New history should inherit cumulative_total from previous day"""
        # Create yesterday's history with cumulative_total
        yesterday_history = PointHistory(
            date=yesterday,
            points_earned=50,
            cumulative_total=200
        )
        db_session.add(yesterday_history)
        db_session.commit()

        service = PointsService(db_session)
        history = service.get_or_create_today_history(today)

        assert history.cumulative_total == 200


class TestAddCompletionPoints:
    """Tests for add_task_completion_points function"""

    def test_adds_task_points_to_history(self, db_session, default_settings, today):
        """Completing a task should add points to history"""
        service = PointsService(db_session)
        service.add_task_completion_points(
            task_id=1,
            energy=3,
            priority=5,
            is_habit=False,
            habit_type="",
            streak=0,
            time_spent=300,
            started_at=datetime.now() - timedelta(minutes=5),
            points_per_task_base=default_settings.points_per_task_base,
            points_per_habit_base=default_settings.points_per_habit_base,
            energy_mult_base=default_settings.energy_mult_base,
            energy_mult_step=default_settings.energy_mult_step,
            today=today,
            minutes_per_energy_unit=default_settings.minutes_per_energy_unit,
            min_work_time_seconds=default_settings.min_work_time_seconds,
            streak_log_factor=default_settings.streak_log_factor,
            routine_points_fixed=default_settings.routine_points_fixed,
            description="Test task",
        )

        history = service.get_or_create_today_history(today)
        assert history.points_earned > 0
        assert history.tasks_completed == 1

    def test_adds_habit_points_to_history(self, db_session, default_settings, today):
        """Completing a habit should add points to history"""
        service = PointsService(db_session)
        service.add_task_completion_points(
            task_id=1,
            energy=2,
            priority=5,
            is_habit=True,
            habit_type="skill",
            streak=3,
            time_spent=0,
            started_at=None,
            points_per_task_base=default_settings.points_per_task_base,
            points_per_habit_base=default_settings.points_per_habit_base,
            energy_mult_base=default_settings.energy_mult_base,
            energy_mult_step=default_settings.energy_mult_step,
            today=today,
            minutes_per_energy_unit=default_settings.minutes_per_energy_unit,
            min_work_time_seconds=default_settings.min_work_time_seconds,
            streak_log_factor=default_settings.streak_log_factor,
            routine_points_fixed=default_settings.routine_points_fixed,
            description="Test habit",
        )

        history = service.get_or_create_today_history(today)
        assert history.points_earned > 0
        assert history.habits_completed == 1

    def test_updates_cumulative_total(self, db_session, default_settings, today):
        """Completing tasks should update cumulative_total"""
        service = PointsService(db_session)

        # Get initial cumulative
        history = service.get_or_create_today_history(today)
        initial_cumulative = history.cumulative_total

        service.add_task_completion_points(
            task_id=1,
            energy=3,
            priority=5,
            is_habit=False,
            habit_type="",
            streak=0,
            time_spent=300,
            started_at=datetime.now() - timedelta(minutes=5),
            points_per_task_base=default_settings.points_per_task_base,
            points_per_habit_base=default_settings.points_per_habit_base,
            energy_mult_base=default_settings.energy_mult_base,
            energy_mult_step=default_settings.energy_mult_step,
            today=today,
            minutes_per_energy_unit=default_settings.minutes_per_energy_unit,
            min_work_time_seconds=default_settings.min_work_time_seconds,
            streak_log_factor=default_settings.streak_log_factor,
            routine_points_fixed=default_settings.routine_points_fixed,
            description="Test task",
        )

        db_session.refresh(history)
        assert history.cumulative_total > initial_cumulative
