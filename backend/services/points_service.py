"""
Points calculation service.
Handles all points-related calculations including task points, habit points, and bonuses.
"""
import math
import json
from datetime import datetime, date, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session

from backend.models import Task, Settings, PointHistory, PointGoal
from backend.repositories.points_repository import (
    PointHistoryRepository, PointGoalRepository
)
from backend.repositories.settings_repository import SettingsRepository
from backend.services.date_service import DateService
from backend.constants import (
    TIME_QUALITY_THRESHOLD,
    TIME_RATIO_THRESHOLD_LOW,
    TIME_RATIO_THRESHOLD_HIGH,
    TIME_RATIO_THRESHOLD_VERY_HIGH,
    TIME_QUALITY_FACTOR_GOOD,
    TIME_QUALITY_FACTOR_BAD,
    FOCUS_PENALTY_MULTIPLIER,
    HABIT_TYPE_SKILL,
    PROJECTION_MULTIPLIER_LOW,
    PROJECTION_MULTIPLIER_HIGH
)


class PointsService:
    """Service for points calculation and management"""

    def __init__(self, db: Session):
        self.db = db
        self.history_repo = PointHistoryRepository()
        self.settings_repo = SettingsRepository()
        self.date_service = DateService()

    def calculate_task_points(self, task: Task, settings: Settings) -> int:
        """
        Calculate points for completing a task using Balanced Progress v2.0 formula.

        Formula: Points = Base × EnergyMultiplier × TimeQualityFactor × FocusFactor

        Args:
            task: Completed task
            settings: Application settings

        Returns:
            Points earned (minimum 1)
        """
        base = settings.points_per_task_base

        # 1. Energy Multiplier
        energy_multiplier = self._calculate_energy_multiplier(task, settings)

        # 2. Time Quality Factor
        time_quality_factor = self._calculate_time_quality_factor(task, settings)

        # 3. Focus Factor
        focus_factor = self._calculate_focus_factor(task)

        # Calculate total points
        total_points = base * energy_multiplier * time_quality_factor * focus_factor

        # Minimum 1 point for any completed task
        return max(1, int(total_points))

    def _calculate_energy_multiplier(self, task: Task, settings: Settings) -> float:
        """
        Calculate energy multiplier based on task energy level.

        E0 -> 0.6, E1 -> 0.8, E2 -> 1.0, E3 -> 1.2, E4 -> 1.4, E5 -> 1.6
        """
        return settings.energy_mult_base + (task.energy * settings.energy_mult_step)

    def _calculate_time_quality_factor(self, task: Task, settings: Settings) -> float:
        """
        Calculate time quality factor based on actual vs expected time.

        - ActualTime < min_work_time: 0.5 (suspiciously fast)
        - Ratio < 0.5: 0.8 (too fast)
        - 0.5 ≤ Ratio ≤ 1.5: 1.0 (normal)
        - 1.5 < Ratio ≤ 3.0: 0.9 (slightly slow)
        - Ratio > 3.0: 0.7 (very slow)
        """
        actual_time = task.time_spent if task.time_spent else 0
        expected_time = task.energy * settings.minutes_per_energy_unit * 60  # seconds

        # Suspiciously fast
        if actual_time < settings.min_work_time_seconds:
            return TIME_QUALITY_THRESHOLD

        # No expected time (E0 tasks)
        if expected_time == 0:
            return 1.0

        # Calculate time ratio
        ratio = actual_time / expected_time

        if ratio < TIME_QUALITY_THRESHOLD:
            return TIME_RATIO_THRESHOLD_LOW  # Too fast
        elif ratio <= TIME_RATIO_THRESHOLD_HIGH:
            return 1.0  # Normal range
        elif ratio <= TIME_RATIO_THRESHOLD_VERY_HIGH:
            return TIME_QUALITY_FACTOR_GOOD  # Slightly slow
        else:
            return TIME_QUALITY_FACTOR_BAD  # Very slow

    def _calculate_focus_factor(self, task: Task) -> float:
        """
        Calculate focus factor based on task tracking.

        - Task was tracked: 1.0
        - Completed without start: 0.8
        """
        if task.started_at is None:
            # Completed without starting - suspicious
            return FOCUS_PENALTY_MULTIPLIER

        # Normal completion with tracking
        return 1.0

    def calculate_habit_points(self, task: Task, settings: Settings) -> int:
        """
        Calculate points for completing a habit.

        Skill habits: Base × StreakBonus
            StreakBonus = 1 + log₂(streak + 1) × streak_log_factor

        Routine habits: Fixed points (no streak bonus)

        Args:
            task: Completed habit
            settings: Application settings

        Returns:
            Points earned (minimum 1)
        """
        # Routine habits get fixed points, no streak
        if task.habit_type != HABIT_TYPE_SKILL:
            return settings.routine_points_fixed

        # Skill habits: base + streak bonus
        base = settings.points_per_habit_base
        streak = task.streak if task.streak else 0

        # Calculate streak bonus using log₂ (naturally caps growth)
        streak_bonus = 1 + math.log2(streak + 1) * settings.streak_log_factor

        total = base * streak_bonus
        return max(1, int(total))

    def get_or_create_today_history(self) -> PointHistory:
        """
        Get or create point history for today.

        If yesterday hasn't been finalized, triggers finalization first.

        Returns:
            Point history for today
        """
        settings = self.settings_repo.get(self.db)
        today = self.date_service.get_effective_date(settings)
        history = self.history_repo.get_by_date(self.db, today)

        if history:
            return history

        # Finalize yesterday before creating today
        yesterday = today - timedelta(days=1)
        yesterday_history = self.history_repo.get_by_date(self.db, yesterday)

        if yesterday_history and yesterday_history.points_penalty == 0:
            # Yesterday hasn't been finalized - will be done during roll
            pass

        # Get most recent history entry to get cumulative total
        last_history = self.history_repo.get_most_recent(self.db, today)
        previous_total = last_history.cumulative_total if last_history else 0

        # Create new history entry
        history = PointHistory(
            date=today,
            cumulative_total=previous_total
        )
        return self.history_repo.create(self.db, history)

    def add_task_completion_points(self, task: Task) -> None:
        """
        Add points when a task/habit is completed.

        Args:
            task: Completed task or habit
        """
        settings = self.settings_repo.get(self.db)
        history = self.get_or_create_today_history()

        # Calculate points
        if task.is_habit:
            points = self.calculate_habit_points(task, settings)
            history.habits_completed += 1
        else:
            points = self.calculate_task_points(task, settings)
            history.tasks_completed += 1

        # Add to earned points
        history.points_earned += points

        # Update daily and cumulative totals
        history.daily_total = (
            history.points_earned + history.points_bonus - history.points_penalty
        )
        history.cumulative_total += points

        # Store completion details (preserve dict format)
        details = {}
        if history.details:
            try:
                details = json.loads(history.details)
                # Handle legacy format where details was a list
                if isinstance(details, list):
                    details = {"task_completions": details}
            except json.JSONDecodeError:
                details = {}

        # Ensure task_completions is a list
        if "task_completions" not in details:
            details["task_completions"] = []

        # Add task completion
        details["task_completions"].append({
            "task_id": task.id,
            "description": task.description,
            "is_habit": task.is_habit,
            "points": points,
            "time": datetime.now().isoformat()
        })
        history.details = json.dumps(details)

        self.history_repo.update(self.db, history)

    def get_current_points(self) -> int:
        """Get current total points"""
        history = self.get_or_create_today_history()
        return history.cumulative_total

    def get_point_history(self, days: int = 30) -> List[PointHistory]:
        """Get point history for last N days"""
        settings = self.settings_repo.get(self.db)
        today = self.date_service.get_effective_date(settings)
        return self.history_repo.get_history(self.db, days, today)

    def get_day_details(self, target_date: date) -> dict:
        """Get detailed breakdown for a specific day"""
        import json
        from sqlalchemy import and_
        from backend.models import Task
        from backend.constants import TASK_STATUS_COMPLETED

        # Get history for target date
        history = self.history_repo.get_by_date(self.db, target_date)
        if not history:
            return {
                "date": target_date.isoformat(),
                "error": "No history found for this date"
            }

        # Parse details JSON
        details = {}
        if history.details:
            try:
                details = json.loads(history.details)
                # Handle legacy format where details was a list
                if isinstance(details, list):
                    details = {"task_completions": details}
            except json.JSONDecodeError:
                details = {}

        # Get completed tasks/habits for this day
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        completed_tasks = self.db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_COMPLETED,
                Task.completed_at >= day_start,
                Task.completed_at < day_end,
                Task.is_habit == False
            )
        ).all()

        completed_habits = self.db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_COMPLETED,
                Task.completed_at >= day_start,
                Task.completed_at < day_end,
                Task.is_habit == True
            )
        ).all()

        # Get points for each task/habit from details
        task_completions = details.get("task_completions", [])
        points_map = {item["task_id"]: item["points"] for item in task_completions if "task_id" in item and "points" in item}

        # Build response
        return {
            "date": target_date.isoformat(),
            "summary": {
                "points_earned": history.points_earned,
                "points_penalty": history.points_penalty,
                "cumulative_total": history.cumulative_total,
                "tasks_completed": history.tasks_completed,
                "tasks_planned": history.tasks_planned,
                "completion_rate": history.completion_rate
            },
            "completed_tasks": [
                {
                    "id": task.id,
                    "description": task.description,
                    "project": task.project,
                    "energy": task.energy,
                    "points": points_map.get(task.id, 0)
                }
                for task in completed_tasks
            ],
            "completed_habits": [
                {
                    "id": habit.id,
                    "description": habit.description,
                    "habit_type": habit.habit_type,
                    "streak": habit.streak,
                    "points": points_map.get(habit.id, 0)
                }
                for habit in completed_habits
            ],
            "penalties": self._parse_penalty_details(details),
            "planned_tasks": details.get("planned_tasks", [])
        }

    def _parse_penalty_details(self, details: dict) -> dict:
        """Parse penalty details from JSON"""
        penalty_breakdown = details.get("penalty_breakdown", {})
        return {
            "idle_penalty": penalty_breakdown.get("idle_penalty", 0),
            "incomplete_penalty": penalty_breakdown.get("incomplete_penalty", 0),
            "missed_habits_penalty": penalty_breakdown.get("missed_habits_penalty", 0),
            "progressive_multiplier": penalty_breakdown.get("progressive_multiplier", 1.0),
            "total": penalty_breakdown.get("total_penalty", 0),
            "missed_habits": penalty_breakdown.get("missed_habits", []),
            "incomplete_tasks": penalty_breakdown.get("incomplete_tasks", [])
        }

    def calculate_projection(self, target_date: date) -> dict:
        """
        Calculate point projections until target date.

        Args:
            target_date: Date to project to

        Returns:
            Dictionary with projections (min, avg, max)
        """
        # Get last 30 days average
        history = self.get_point_history(30)

        if not history:
            avg_per_day = 0
        else:
            total_daily = sum(h.daily_total for h in history)
            avg_per_day = total_daily / len(history)

        current_total = self.get_current_points()
        settings = self.settings_repo.get(self.db)
        today = self.date_service.get_effective_date(settings)
        days_until = (target_date - today).days

        if days_until <= 0:
            return {
                "current_total": current_total,
                "days_until": days_until,
                "avg_per_day": avg_per_day,
                "projection": current_total
            }

        # Calculate projections
        min_projection = current_total + int(
            avg_per_day * PROJECTION_MULTIPLIER_LOW * days_until
        )
        avg_projection = current_total + int(avg_per_day * days_until)
        max_projection = current_total + int(
            avg_per_day * PROJECTION_MULTIPLIER_HIGH * days_until
        )

        return {
            "current_total": current_total,
            "days_until": days_until,
            "avg_per_day": round(avg_per_day, 2),
            "min_projection": max(min_projection, current_total),
            "avg_projection": max(avg_projection, current_total),
            "max_projection": max(max_projection, current_total)
        }

    def check_goal_achievements(self) -> List[PointGoal]:
        """
        Check and mark achieved goals.

        Returns:
            List of newly achieved goals
        """
        from backend.constants import TASK_STATUS_COMPLETED
        from sqlalchemy import and_

        current_total = self.get_current_points()
        goal_repo = PointGoalRepository()
        goals = goal_repo.get_all(self.db, include_achieved=False)

        achieved_goals = []
        settings = self.settings_repo.get(self.db)
        today = self.date_service.get_effective_date(settings)

        for goal in goals:
            is_achieved = False

            # Check based on goal type
            if goal.goal_type == "points":
                # Points goal: check if current total >= target
                if goal.target_points and current_total >= goal.target_points:
                    is_achieved = True

            elif goal.goal_type == "project_completion":
                # Project completion goal: check if all tasks in project are completed
                if goal.project_name:
                    # Count total tasks in project
                    from backend.models import Task
                    total_tasks = self.db.query(Task).filter(
                        and_(
                            Task.project == goal.project_name,
                            Task.is_habit == False
                        )
                    ).count()

                    # Count completed tasks in project
                    completed_tasks = self.db.query(Task).filter(
                        and_(
                            Task.project == goal.project_name,
                            Task.is_habit == False,
                            Task.status == TASK_STATUS_COMPLETED
                        )
                    ).count()

                    # Project is complete if all tasks are done (and there's at least 1 task)
                    if total_tasks > 0 and completed_tasks == total_tasks:
                        is_achieved = True

            if is_achieved:
                goal.achieved = True
                goal.achieved_date = today
                goal_repo.update(self.db, goal)
                achieved_goals.append(goal)

        return achieved_goals
