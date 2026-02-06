"""
Complete Task Workflow - Orchestrates task completion with points.

This workflow coordinates:
1. TaskService - completes the task
2. PointsService - awards points
3. GoalService - checks goal achievements
"""

from typing import Optional
from sqlalchemy.orm import Session

from backend.modules.tasks import TaskService, TaskResult
from backend.modules.tasks.schemas import TaskResponse
from backend.modules.points import PointsService
from backend.modules.goals import GoalService
from backend.modules.settings import SettingsService
from backend.shared.date_utils import get_effective_date


class CompleteTaskWorkflow:
    """Orchestrator for completing tasks and awarding points."""

    def __init__(self, db: Session):
        self.db = db
        self.task_service = TaskService(db)
        self.points_service = PointsService(db)
        self.goal_service = GoalService(db)
        self.settings_service = SettingsService(db)

    def execute(self, task_id: Optional[int] = None) -> TaskResponse:
        """
        Complete a task and award points.

        Args:
            task_id: Specific task to complete, or None for active task

        Returns:
            Completed task response

        Raises:
            TaskNotFoundError: If task not found
            DependencyNotMetError: If task has unmet dependency
        """
        # Get settings for effective date
        settings = self.settings_service.get_data()
        today = get_effective_date(settings.day_start_enabled, settings.day_start_time)

        # Complete the task (TaskService handles logic, returns TaskResult)
        result: TaskResult = self.task_service.complete(task_id, today)

        # Award points if task was fully completed
        if result.fully_completed:
            # Calculate and add points
            self.points_service.add_task_completion_points(
                task_id=result.id,
                energy=result.energy,
                priority=result.priority,
                is_habit=result.is_habit,
                habit_type=result.habit_type,
                streak=result.streak,
                time_spent=result.time_spent,
                started_at=result.started_at,
                points_per_task_base=settings.points_per_task_base,
                points_per_habit_base=settings.points_per_habit_base,
                energy_mult_base=settings.energy_mult_base,
                energy_mult_step=settings.energy_mult_step,
                today=today,
                minutes_per_energy_unit=settings.minutes_per_energy_unit,
                min_work_time_seconds=settings.min_work_time_seconds,
                streak_log_factor=settings.streak_log_factor,
                routine_points_fixed=settings.routine_points_fixed,
                description=result.description,
            )

            # Check if any goals were achieved
            current_points = self.points_service.get_current_points(today)
            self.goal_service.check_achievements(
                current_points=current_points,
                today=today,
                get_project_progress=self.task_service.get_project_progress
            )

        # Return the task response
        return self.task_service.get_or_none(result.id)
