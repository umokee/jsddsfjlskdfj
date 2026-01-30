"""
CRUD operations facade.
This module provides backward compatibility by delegating to the new service layer.

The actual business logic has been refactored into focused services:
- DateService: Date calculations and effective date handling
- TaskService: Task CRUD and business logic
- PointsService: Points calculations
- PenaltyService: Penalty calculations
- GoalService: Goal management
- RestDayService: Rest day management
"""
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Optional

from backend.models import Task, Settings, PointHistory, PointGoal, RestDay
from backend.schemas import (
    TaskCreate, TaskUpdate, SettingsUpdate, PointGoalCreate,
    PointGoalUpdate, RestDayCreate
)

from backend.services.date_service import DateService
from backend.services.task_service import TaskService
from backend.services.points_service import PointsService
from backend.services.penalty_service import PenaltyService
from backend.services.goal_service import GoalService, RestDayService
from backend.repositories.settings_repository import SettingsRepository


# ====================
# DATE FUNCTIONS
# ====================

def get_effective_date(settings: Settings) -> date:
    """Get the effective current date based on day_start_time setting"""
    return DateService.get_effective_date(settings)


def get_effective_today(db: Session) -> date:
    """Convenience function: get settings and return effective date"""
    settings = get_settings(db)
    return DateService.get_effective_date(settings)


# ====================
# TASK FUNCTIONS
# ====================

def get_task(db: Session, task_id: int) -> Optional[Task]:
    """Get task by ID"""
    service = TaskService(db)
    return service.get_task(task_id)


def get_tasks(db: Session, skip: int = 0, limit: int = 100) -> List[Task]:
    """Get all tasks with pagination"""
    service = TaskService(db)
    return service.get_tasks(skip, limit)


def enrich_task_with_dependency(db: Session, task: Task) -> dict:
    """Add dependency info to task for API response"""
    task_dict = {
        "id": task.id,
        "description": task.description,
        "project": task.project,
        "priority": task.priority,
        "energy": task.energy,
        "is_habit": task.is_habit,
        "is_today": task.is_today,
        "due_date": task.due_date,
        "estimated_time": task.estimated_time,
        "depends_on": task.depends_on,
        "recurrence_type": task.recurrence_type,
        "recurrence_interval": task.recurrence_interval,
        "recurrence_days": task.recurrence_days,
        "habit_type": task.habit_type,
        "daily_target": task.daily_target,
        "daily_completed": task.daily_completed,
        "status": task.status,
        "urgency": task.urgency,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "time_spent": task.time_spent,
        "streak": task.streak,
        "last_completed_date": task.last_completed_date,
        "dependency_name": None,
        "dependency_completed": True
    }

    if task.depends_on:
        from backend.repositories.task_repository import TaskRepository
        from backend.constants import TASK_STATUS_COMPLETED
        dep = TaskRepository.get_by_id(db, task.depends_on)
        if dep:
            task_dict["dependency_name"] = dep.description
            task_dict["dependency_completed"] = dep.status == TASK_STATUS_COMPLETED

    return task_dict


def enrich_tasks_with_dependencies(db: Session, tasks: List[Task]) -> List[dict]:
    """Add dependency info to list of tasks"""
    return [enrich_task_with_dependency(db, task) for task in tasks]


def get_pending_tasks(db: Session) -> List[Task]:
    """Get pending tasks (excluding habits)"""
    from backend.repositories.task_repository import TaskRepository
    return TaskRepository.get_pending_tasks(db)


def get_active_task(db: Session) -> Optional[Task]:
    """Get currently active task"""
    from backend.repositories.task_repository import TaskRepository
    return TaskRepository.get_active_task(db)


def get_next_task(db: Session) -> Optional[Task]:
    """Get next task (non-habit, today, pending) sorted by urgency"""
    from backend.repositories.task_repository import TaskRepository
    return TaskRepository.get_next_task(db)


def get_next_habit(db: Session) -> Optional[Task]:
    """Get next habit for today"""
    settings = get_settings(db)
    today = DateService.get_effective_date(settings)
    from backend.repositories.task_repository import TaskRepository
    return TaskRepository.get_next_habit(db, today)


def get_all_habits(db: Session) -> List[Task]:
    """Get all pending habits"""
    from backend.repositories.task_repository import TaskRepository
    return TaskRepository.get_all_habits(db)


def get_today_habits(db: Session) -> List[Task]:
    """Get all habits for today"""
    settings = get_settings(db)
    today = DateService.get_effective_date(settings)
    from backend.repositories.task_repository import TaskRepository
    return TaskRepository.get_today_habits(db, today)


def get_today_tasks(db: Session) -> List[Task]:
    """Get today's tasks (non-habits with is_today=True)"""
    from backend.repositories.task_repository import TaskRepository
    return TaskRepository.get_today_tasks(db)


def get_stats(db: Session) -> dict:
    """Get daily statistics"""
    service = TaskService(db)
    return service.get_stats()


def create_task(db: Session, task: TaskCreate) -> Task:
    """Create a new task"""
    service = TaskService(db)
    return service.create_task(task)


def update_task(db: Session, task_id: int, task_update: TaskUpdate) -> Optional[Task]:
    """Update an existing task"""
    service = TaskService(db)
    return service.update_task(task_id, task_update)


def delete_task(db: Session, task_id: int) -> bool:
    """Delete a task"""
    service = TaskService(db)
    return service.delete_task(task_id)


def start_task(db: Session, task_id: Optional[int] = None) -> Optional[Task]:
    """Start a task (stop all active first)"""
    service = TaskService(db)
    return service.start_task(task_id)


def stop_task(db: Session) -> bool:
    """Stop active task and save elapsed time"""
    service = TaskService(db)
    return service.stop_task()


def complete_task(db: Session, task_id: Optional[int] = None) -> Optional[Task]:
    """Complete a task (active or specified)"""
    service = TaskService(db)
    return service.complete_task(task_id)


def task_dependencies_met(db: Session, task: Task) -> bool:
    """Check if all dependencies for a task are met (completed)"""
    service = TaskService(db)
    return service.check_dependencies_met(task)


def task_dependency_in_today_plan(db: Session, task: Task) -> bool:
    """Check if task's dependency is already scheduled for today"""
    service = TaskService(db)
    return service.check_dependency_in_today_plan(task)


def can_roll_now(db: Session) -> tuple[bool, str]:
    """Check if roll is available right now"""
    service = TaskService(db)
    return service.can_roll_now()


def roll_tasks(
    db: Session,
    mood: Optional[str] = None,
    daily_limit: int = 5,
    critical_days: int = 2
) -> dict:
    """Generate daily task plan"""
    service = TaskService(db)
    return service.roll_tasks(mood, daily_limit, critical_days)


# ====================
# SETTINGS FUNCTIONS
# ====================

def get_settings(db: Session) -> Settings:
    """Get settings (create with defaults if not exists)"""
    repo = SettingsRepository()
    return repo.get(db)


def update_settings(db: Session, settings_update: SettingsUpdate) -> Settings:
    """Update settings"""
    settings = get_settings(db)
    update_data = settings_update.model_dump()
    for key, value in update_data.items():
        setattr(settings, key, value)

    repo = SettingsRepository()
    return repo.update(db, settings)


# ====================
# POINTS FUNCTIONS
# ====================

def get_or_create_today_history(db: Session) -> PointHistory:
    """Get or create point history for today"""
    service = PointsService(db)
    return service.get_or_create_today_history()


def add_task_completion_points(db: Session, task: Task) -> None:
    """Add points when a task/habit is completed"""
    service = PointsService(db)
    service.add_task_completion_points(task)


def calculate_daily_penalties(db: Session) -> dict:
    """Calculate penalties for yesterday"""
    service = PenaltyService(db)
    return service.calculate_daily_penalties()


def get_point_history(db: Session, days: int = 30) -> List[PointHistory]:
    """Get point history for last N days"""
    service = PointsService(db)
    return service.get_point_history(days)


def get_current_points(db: Session) -> int:
    """Get current total points"""
    service = PointsService(db)
    return service.get_current_points()


def get_day_details(db: Session, target_date: date) -> dict:
    """Get detailed breakdown for a specific day"""
    service = PointsService(db)
    return service.get_day_details(target_date)


def calculate_projection(db: Session, target_date: date) -> dict:
    """Calculate point projections until target date"""
    service = PointsService(db)
    return service.calculate_projection(target_date)


# ====================
# GOAL FUNCTIONS
# ====================

def get_point_goals(db: Session, include_achieved: bool = False) -> List[PointGoal]:
    """Get point goals"""
    service = GoalService(db)
    return service.get_goals(include_achieved)


def create_point_goal(db: Session, goal: PointGoalCreate) -> PointGoal:
    """Create a new point goal"""
    service = GoalService(db)
    return service.create_goal(goal)


def update_point_goal(
    db: Session,
    goal_id: int,
    goal_update: PointGoalUpdate
) -> Optional[PointGoal]:
    """Update a point goal"""
    service = GoalService(db)
    return service.update_goal(goal_id, goal_update)


def delete_point_goal(db: Session, goal_id: int) -> bool:
    """Delete a point goal"""
    service = GoalService(db)
    return service.delete_goal(goal_id)


def claim_goal_reward(db: Session, goal_id: int) -> Optional[PointGoal]:
    """Claim reward for achieved goal"""
    service = GoalService(db)
    return service.claim_reward(goal_id)


def check_goal_achievements(db: Session) -> List[PointGoal]:
    """Check and mark achieved goals"""
    service = PointsService(db)
    return service.check_goal_achievements()


# ====================
# REST DAY FUNCTIONS
# ====================

def get_rest_days(db: Session) -> List[RestDay]:
    """Get all rest days"""
    service = RestDayService(db)
    return service.get_rest_days()


def create_rest_day(db: Session, rest_day: RestDayCreate) -> RestDay:
    """Create a rest day"""
    service = RestDayService(db)
    return service.create_rest_day(rest_day)


def delete_rest_day(db: Session, rest_day_id: int) -> bool:
    """Delete a rest day"""
    service = RestDayService(db)
    return service.delete_rest_day(rest_day_id)
