"""
Task repository - Data access layer.
PRIVATE - do not import from outside this module.
"""
from datetime import datetime, date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.shared.constants import (
    TASK_STATUS_PENDING,
    TASK_STATUS_ACTIVE,
    TASK_STATUS_COMPLETED,
)
from .models import Task


class TaskRepository:
    """Repository for Task data access."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, task_id: int) -> Optional[Task]:
        """Get task by ID."""
        return self.db.query(Task).filter(Task.id == task_id).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Task]:
        """Get all tasks with pagination."""
        return self.db.query(Task).offset(skip).limit(limit).all()

    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks (excluding habits)."""
        return self.db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_habit == False
            )
        ).order_by(Task.urgency.desc()).all()

    def get_active_task(self) -> Optional[Task]:
        """Get currently active task."""
        return self.db.query(Task).filter(Task.status == TASK_STATUS_ACTIVE).first()

    def get_all_active_tasks(self) -> List[Task]:
        """Get all active tasks."""
        return self.db.query(Task).filter(Task.status == TASK_STATUS_ACTIVE).all()

    def get_next_task(self) -> Optional[Task]:
        """Get next pending task for today (non-habit) sorted by urgency."""
        return self.db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_today == True,
                Task.is_habit == False
            )
        ).order_by(Task.urgency.desc()).first()

    def get_next_habit(self, today: date) -> Optional[Task]:
        """Get next pending habit for today."""
        day_start = datetime.combine(today, datetime.min.time())
        day_end = datetime.combine(today + timedelta(days=1), datetime.min.time())

        return self.db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_habit == True,
                Task.due_date >= day_start,
                Task.due_date < day_end
            )
        ).first()

    def get_all_habits(self) -> List[Task]:
        """Get all pending habits."""
        return self.db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_habit == True
            )
        ).order_by(Task.due_date).all()

    def get_today_habits(self, today: date) -> List[Task]:
        """Get all habits due today."""
        day_start = datetime.combine(today, datetime.min.time())
        day_end = datetime.combine(today + timedelta(days=1), datetime.min.time())

        return self.db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_habit == True,
                Task.due_date >= day_start,
                Task.due_date < day_end
            )
        ).all()

    def get_today_tasks(self) -> List[Task]:
        """Get today's tasks (non-habits with is_today=True)."""
        return self.db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_habit == False,
                Task.is_today == True
            )
        ).order_by(Task.urgency.desc()).all()

    def get_completed_count(
        self,
        start_time: datetime,
        end_time: datetime,
        is_habit: Optional[bool] = None
    ) -> int:
        """Get count of completed tasks in time range."""
        query = self.db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_COMPLETED,
                Task.completed_at >= start_time,
                Task.completed_at < end_time
            )
        )

        if is_habit is not None:
            query = query.filter(Task.is_habit == is_habit)

        return query.count()

    def get_completed_tasks(
        self,
        start_time: datetime,
        end_time: datetime,
        is_habit: Optional[bool] = None
    ) -> List[Task]:
        """Get completed tasks in time range."""
        query = self.db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_COMPLETED,
                Task.completed_at >= start_time,
                Task.completed_at < end_time
            )
        )

        if is_habit is not None:
            query = query.filter(Task.is_habit == is_habit)

        return query.all()

    def get_pending_count(self, today: date) -> int:
        """Get count of pending tasks for today."""
        day_start = datetime.combine(today, datetime.min.time())
        day_end = datetime.combine(today + timedelta(days=1), datetime.min.time())

        return self.db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                or_(
                    Task.is_today == True,
                    and_(
                        Task.due_date >= day_start,
                        Task.due_date < day_end
                    )
                )
            )
        ).count()

    def get_total_pending_count(self) -> int:
        """Get total count of all pending tasks."""
        return self.db.query(Task).filter(Task.status == TASK_STATUS_PENDING).count()

    def get_overdue_habits(self, before_date: datetime) -> List[Task]:
        """Get habits that are overdue (due before specified date)."""
        return self.db.query(Task).filter(
            and_(
                Task.is_habit == True,
                Task.status == TASK_STATUS_PENDING,
                Task.due_date < before_date
            )
        ).all()

    def get_critical_tasks(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Task]:
        """Get critical tasks (due within date range)."""
        return self.db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_habit == False,
                Task.due_date <= end_date,
                Task.due_date >= start_date
            )
        ).all()

    def get_available_tasks(self) -> List[Task]:
        """Get all available pending non-habit tasks."""
        return self.db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_habit == False,
                Task.is_today == False
            )
        ).all()

    def get_incomplete_today_tasks(self) -> List[Task]:
        """Get tasks scheduled for today that haven't been completed."""
        return self.db.query(Task).filter(
            and_(
                Task.is_habit == False,
                Task.is_today == True,
                Task.status != TASK_STATUS_COMPLETED
            )
        ).all()

    def get_habits_due_in_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Task]:
        """Get habits due within date range."""
        return self.db.query(Task).filter(
            and_(
                Task.is_habit == True,
                Task.due_date >= start_time,
                Task.due_date < end_time
            )
        ).all()

    def count_habits_due_in_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """Count habits due within date range."""
        return self.db.query(Task).filter(
            and_(
                Task.is_habit == True,
                Task.due_date >= start_time,
                Task.due_date < end_time
            )
        ).count()

    def get_missed_habits(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Task]:
        """Get habits due but not completed in date range."""
        return self.db.query(Task).filter(
            and_(
                Task.is_habit == True,
                Task.due_date >= start_time,
                Task.due_date < end_time,
                Task.status != TASK_STATUS_COMPLETED
            )
        ).all()

    def get_project_tasks(self, project_name: str, is_habit: bool = False) -> List[Task]:
        """Get all tasks for a project."""
        return self.db.query(Task).filter(
            and_(
                Task.project == project_name,
                Task.is_habit == is_habit
            )
        ).all()

    def get_project_task_counts(self, project_name: str) -> dict:
        """Get task counts for a project."""
        total = self.db.query(Task).filter(
            and_(
                Task.project == project_name,
                Task.is_habit == False
            )
        ).count()

        completed = self.db.query(Task).filter(
            and_(
                Task.project == project_name,
                Task.is_habit == False,
                Task.status == TASK_STATUS_COMPLETED
            )
        ).count()

        return {"total_tasks": total, "completed_tasks": completed}

    def create(self, task: Task) -> Task:
        """Create a new task."""
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def update(self, task: Task) -> Task:
        """Update existing task."""
        self.db.commit()
        self.db.refresh(task)
        return task

    def delete(self, task: Task) -> None:
        """Delete a task."""
        self.db.delete(task)
        self.db.commit()

    def clear_today_flag(self) -> None:
        """Clear is_today flag from all non-habit tasks."""
        self.db.query(Task).filter(
            and_(
                Task.is_habit == False,
                Task.is_today == True
            )
        ).update({Task.is_today: False})
        self.db.commit()

    # Alias methods for scheduler/workflows
    def get_completed_in_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Task]:
        """Alias for get_completed_tasks (non-habits)."""
        return self.get_completed_tasks(start_time, end_time, is_habit=False)

    def get_completed_habits_in_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Task]:
        """Alias for get_completed_tasks (habits)."""
        return self.get_completed_tasks(start_time, end_time, is_habit=True)

