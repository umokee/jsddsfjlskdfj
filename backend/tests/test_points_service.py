"""
Tests for PointsService.

Tests cover:
1. Task points calculation
2. Habit points calculation with streak bonus
3. History management
4. Day details retrieval
"""
import pytest
from datetime import date, datetime, timedelta

from backend.services.points_service import PointsService
from backend.models import Task, PointHistory, Settings


class TestTaskPointsCalculation:
    """Tests for calculate_task_points function"""

    def test_base_points_with_energy_multiplier(self, db_session, default_settings):
        """Should apply energy multiplier to base points"""
        # E3 task expects 3*20=60 minutes, so 60 min time_spent is in normal range
        task = Task(
            description="Test task",
            energy=3,  # E3 -> mult = 0.6 + 3*0.2 = 1.2
            time_spent=3600,  # 60 minutes (normal range for E3)
            started_at=datetime.now() - timedelta(minutes=60)
        )
        db_session.add(task)
        db_session.commit()

        service = PointsService(db_session)
        points = service.calculate_task_points(task, default_settings)

        # Base 10 * 1.2 energy = 12
        # Time quality should be 1.0 (60 min for E3 = expected)
        # Focus factor 1.0 (started properly)
        assert points == 12

    def test_low_energy_reduces_points(self, db_session, default_settings):
        """Low energy tasks should give fewer points"""
        task = Task(
            description="Test task",
            energy=0,  # E0 -> mult = 0.6
            time_spent=300,
            started_at=datetime.now() - timedelta(minutes=5)
        )
        db_session.add(task)
        db_session.commit()

        service = PointsService(db_session)
        points = service.calculate_task_points(task, default_settings)

        # Base 10 * 0.6 = 6
        assert points == 6

    def test_high_energy_increases_points(self, db_session, default_settings):
        """High energy tasks should give more points"""
        # E5 task expects 5*20=100 minutes, so 100 min time_spent is in normal range
        task = Task(
            description="Test task",
            energy=5,  # E5 -> mult = 0.6 + 5*0.2 = 1.6
            time_spent=6000,  # 100 minutes (normal range for E5)
            started_at=datetime.now() - timedelta(minutes=100)
        )
        db_session.add(task)
        db_session.commit()

        service = PointsService(db_session)
        points = service.calculate_task_points(task, default_settings)

        # Base 10 * 1.6 = 16
        assert points == 16

    def test_suspiciously_fast_completion(self, db_session, default_settings):
        """Completing too fast should reduce points"""
        task = Task(
            description="Test task",
            energy=3,
            time_spent=60,  # Only 1 minute (below min_work_time of 120s)
            started_at=datetime.now() - timedelta(minutes=1)
        )
        db_session.add(task)
        db_session.commit()

        service = PointsService(db_session)
        points = service.calculate_task_points(task, default_settings)

        # Base 10 * 1.2 energy * 0.5 time quality = 6
        assert points == 6

    def test_no_start_reduces_points(self, db_session, default_settings):
        """Completing without starting should reduce points (focus penalty)"""
        # E3 expects 60 min, so use 60 min time_spent for normal time quality
        task = Task(
            description="Test task",
            energy=3,
            time_spent=3600,  # 60 minutes (normal range for E3)
            started_at=None  # Never started - this is the focus penalty
        )
        db_session.add(task)
        db_session.commit()

        service = PointsService(db_session)
        points = service.calculate_task_points(task, default_settings)

        # Base 10 * 1.2 energy * 0.8 focus = 9.6 -> 9
        assert points == 9

    def test_minimum_one_point(self, db_session, default_settings):
        """Should never give less than 1 point"""
        task = Task(
            description="Test task",
            energy=0,  # Lowest energy
            time_spent=1,  # Suspiciously fast
            started_at=None  # No focus
        )
        db_session.add(task)
        db_session.commit()

        service = PointsService(db_session)
        points = service.calculate_task_points(task, default_settings)

        # Even with all penalties, minimum is 1
        assert points >= 1


class TestHabitPointsCalculation:
    """Tests for calculate_habit_points function"""

    def test_routine_gets_fixed_points(self, db_session, default_settings):
        """Routine habits should get fixed points, no streak bonus"""
        habit = Task(
            description="Test routine",
            is_habit=True,
            habit_type="routine",
            streak=10  # High streak should not affect routines
        )
        db_session.add(habit)
        db_session.commit()

        service = PointsService(db_session)
        points = service.calculate_habit_points(habit, default_settings)

        assert points == default_settings.routine_points_fixed  # 6

    def test_skill_habit_with_streak_bonus(self, db_session, default_settings):
        """Skill habits should get streak bonus"""
        habit = Task(
            description="Test skill",
            is_habit=True,
            habit_type="skill",
            streak=7
        )
        db_session.add(habit)
        db_session.commit()

        service = PointsService(db_session)
        points = service.calculate_habit_points(habit, default_settings)

        # Base 10 * (1 + log2(8) * 0.15) = 10 * (1 + 3 * 0.15) = 10 * 1.45 = 14.5 -> 14
        assert points > default_settings.points_per_habit_base

    def test_skill_habit_no_streak(self, db_session, default_settings):
        """Skill habit with 0 streak should still get base points"""
        habit = Task(
            description="Test skill",
            is_habit=True,
            habit_type="skill",
            streak=0
        )
        db_session.add(habit)
        db_session.commit()

        service = PointsService(db_session)
        points = service.calculate_habit_points(habit, default_settings)

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
        history = service.get_or_create_today_history()

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
        history = service.get_or_create_today_history()

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
        history = service.get_or_create_today_history()

        assert history.cumulative_total == 200


class TestAddCompletionPoints:
    """Tests for add_task_completion_points function"""

    def test_adds_task_points_to_history(self, db_session, default_settings, today):
        """Completing a task should add points to history"""
        task = Task(
            description="Test task",
            energy=3,
            time_spent=300,
            started_at=datetime.now() - timedelta(minutes=5),
            is_habit=False
        )
        db_session.add(task)
        db_session.commit()

        service = PointsService(db_session)
        service.add_task_completion_points(task)

        history = service.get_or_create_today_history()
        assert history.points_earned > 0
        assert history.tasks_completed == 1

    def test_adds_habit_points_to_history(self, db_session, default_settings, today):
        """Completing a habit should add points to history"""
        habit = Task(
            description="Test habit",
            is_habit=True,
            habit_type="skill",
            streak=3
        )
        db_session.add(habit)
        db_session.commit()

        service = PointsService(db_session)
        service.add_task_completion_points(habit)

        history = service.get_or_create_today_history()
        assert history.points_earned > 0
        assert history.habits_completed == 1

    def test_updates_cumulative_total(self, db_session, default_settings, today):
        """Completing tasks should update cumulative_total"""
        task = Task(
            description="Test task",
            energy=3,
            time_spent=300,
            started_at=datetime.now() - timedelta(minutes=5),
            is_habit=False
        )
        db_session.add(task)
        db_session.commit()

        service = PointsService(db_session)

        # Get initial cumulative
        history = service.get_or_create_today_history()
        initial_cumulative = history.cumulative_total

        service.add_task_completion_points(task)

        db_session.refresh(history)
        assert history.cumulative_total > initial_cumulative


class TestGetDayDetails:
    """Tests for get_day_details function"""

    def test_returns_error_for_missing_date(self, db_session, default_settings, today):
        """Should return error if no history exists for date"""
        service = PointsService(db_session)
        result = service.get_day_details(today)

        assert "error" in result

    def test_returns_summary_for_existing_date(self, db_session, default_settings, today):
        """Should return summary for existing history"""
        import json
        history = PointHistory(
            date=today,
            points_earned=50,
            points_penalty=10,
            cumulative_total=100,
            tasks_completed=3,
            tasks_planned=5,
            completion_rate=0.6,
            details=json.dumps({"task_completions": []})
        )
        db_session.add(history)
        db_session.commit()

        service = PointsService(db_session)
        result = service.get_day_details(today)

        assert result["summary"]["points_earned"] == 50
        assert result["summary"]["points_penalty"] == 10
        assert result["summary"]["completion_rate"] == 0.6
