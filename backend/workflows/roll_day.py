"""
Roll Day Workflow - Orchestrates daily task planning.

This workflow coordinates:
1. PenaltyService - calculates penalties for yesterday
2. TaskService - rolls tasks for today
3. PointsService - saves today's history
4. SettingsService - updates last_roll_date
"""

import json
from typing import Optional
from sqlalchemy.orm import Session

from backend.modules.tasks import TaskService
from backend.modules.points import PointsService
from backend.modules.penalties import PenaltyService
from backend.modules.settings import SettingsService
from backend.modules.rest_days import RestDayService
from backend.shared.date_utils import get_effective_date


class RollDayWorkflow:
    """Orchestrator for daily task planning."""

    def __init__(self, db: Session):
        self.db = db
        self.task_service = TaskService(db)
        self.points_service = PointsService(db)
        self.penalty_service = PenaltyService(db)
        self.settings_service = SettingsService(db)
        self.rest_day_service = RestDayService(db)

    def can_roll(self) -> tuple[bool, str]:
        """
        Check if roll is available right now.

        Returns:
            Tuple of (can_roll, error_message)
        """
        settings = self.settings_service.get_data()
        today = get_effective_date(settings.day_start_enabled, settings.day_start_time)

        return self.task_service.can_roll(
            effective_today=today,
            last_roll_date=settings.last_roll_date,
            day_start_enabled=settings.day_start_enabled,
            roll_available_time=settings.roll_available_time
        )

    def execute(self, mood: Optional[str] = None) -> dict:
        """
        Generate daily task plan.

        Args:
            mood: Energy level filter (0-5)

        Returns:
            Dictionary with roll results
        """
        # Check if roll is available
        can_roll, error_msg = self.can_roll()
        if not can_roll:
            return self._error_response(error_msg)

        settings = self.settings_service.get_data()
        today = get_effective_date(settings.day_start_enabled, settings.day_start_time)

        # 1. Calculate penalties for yesterday (and any skipped days)
        penalty_info = self.penalty_service.calculate_daily_penalties(
            effective_today=today,
            is_rest_day_fn=self.rest_day_service.is_rest_day,
            settings=settings,
            get_yesterday_history=lambda d: self.points_service.get_history_for_date(d),
            get_yesterday_completed_tasks=lambda start, end: self.task_service._get_completed_in_range(start, end),
            get_yesterday_completed_habits=lambda start, end: self.task_service._get_completed_habits_in_range(start, end),
            get_missed_habits_fn=lambda start, end: self.task_service.get_missed_habits(start, end),
            count_habits_due_fn=lambda start, end: self.task_service.count_habits_due(start, end),
            roll_forward_habit_fn=lambda h, d: self.task_service.roll_forward_missed_habit(h, d),
        )

        # 2. Roll tasks (handles overdue habits, selects tasks)
        tasks, habits, deleted_count = self.task_service.roll_tasks(
            mood=mood,
            daily_limit=settings.max_tasks_per_day,
            today=today
        )

        # 3. Save tasks_planned count and task details to history
        today_history = self.points_service.get_or_create_today_history(today)
        today_history_data = self.points_service.get_history_data(today)

        if tasks:
            task_details = self.task_service.get_today_task_details()
            self.points_service.save_planned_tasks(
                today=today,
                tasks_planned=len(tasks),
                task_details=task_details
            )

        # 4. Update last roll date
        self.settings_service.update_last_roll_date(today)

        return {
            "habits": habits,
            "tasks": tasks,
            "deleted_habits": deleted_count,
            "penalty_info": penalty_info
        }

    def complete_roll(self, mood: str) -> dict:
        """
        Complete morning check-in with selected mood.
        Called after user selects energy level.

        Args:
            mood: Energy level (0-5)

        Returns:
            Roll results
        """
        settings = self.settings_service.get_data()

        # Check if there's a pending roll
        if not settings.pending_roll:
            return {
                "error": "No pending roll. Morning check-in already completed or not triggered."
            }

        # Validate mood
        if not mood or not mood.isdigit() or not (0 <= int(mood) <= 5):
            return {
                "error": "Invalid mood. Must be a number between 0 and 5."
            }

        # Execute roll with mood
        result = self.execute(mood)

        if "error" not in result:
            # Clear pending_roll flag
            self.settings_service.clear_pending_roll()
            result["mood"] = int(mood)
            result["message"] = "Morning check-in completed. Daily plan generated!"

        return result

    def _error_response(self, error_msg: str) -> dict:
        """Create error response for roll."""
        return {
            "error": error_msg,
            "habits": [],
            "tasks": [],
            "deleted_habits": 0,
            "penalty_info": {
                "penalty": 0,
                "completion_rate": 0,
                "tasks_completed": 0,
                "tasks_planned": 0,
                "missed_habits": 0
            }
        }
