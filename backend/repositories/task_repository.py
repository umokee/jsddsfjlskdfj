"""
Task repository - Data access layer for Task model.
Handles all database queries related to tasks.
"""
from datetime import datetime, date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from backend.models import Task
from backend.constants import (
    TASK_STATUS_PENDING, TASK_STATUS_ACTIVE, TASK_STATUS_COMPLETED
)


class TaskRepository:
    """Repository for Task data access"""

    @staticmethod
    def get_by_id(db: Session, task_id: int) -> Optional[Task]:
        """Get task by ID"""
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Task]:
        """Get all tasks with pagination"""
        return db.query(Task).offset(skip).limit(limit).all()

    @staticmethod
    def get_pending_tasks(db: Session) -> List[Task]:
        """Get all pending tasks (excluding habits)"""
        return db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_habit == False
            )
        ).order_by(Task.urgency.desc()).all()

    @staticmethod
    def get_active_task(db: Session) -> Optional[Task]:
        """Get currently active task"""
        return db.query(Task).filter(Task.status == TASK_STATUS_ACTIVE).first()

    @staticmethod
    def get_all_active_tasks(db: Session) -> List[Task]:
        """Get all active tasks"""
        return db.query(Task).filter(Task.status == TASK_STATUS_ACTIVE).all()

    @staticmethod
    def get_next_task(db: Session) -> Optional[Task]:
        """Get next pending task for today (non-habit) sorted by urgency"""
        return db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_today == True,
                Task.is_habit == False
            )
        ).order_by(Task.urgency.desc()).first()

    @staticmethod
    def get_next_habit(db: Session, today: date) -> Optional[Task]:
        """Get next pending habit for today"""
        day_start = datetime.combine(today, datetime.min.time())
        day_end = datetime.combine(today + timedelta(days=1), datetime.min.time())

        return db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_habit == True,
                Task.due_date >= day_start,
                Task.due_date < day_end
            )
        ).first()

    @staticmethod
    def get_all_habits(db: Session) -> List[Task]:
        """Get all pending habits"""
        return db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_habit == True
            )
        ).order_by(Task.due_date).all()

    @staticmethod
    def get_today_habits(db: Session, today: date) -> List[Task]:
        """Get all habits due today"""
        day_start = datetime.combine(today, datetime.min.time())
        day_end = datetime.combine(today + timedelta(days=1), datetime.min.time())

        return db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_habit == True,
                Task.due_date >= day_start,
                Task.due_date < day_end
            )
        ).all()

    @staticmethod
    def get_today_tasks(db: Session) -> List[Task]:
        """Get today's tasks (non-habits with is_today=True)"""
        return db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_habit == False,
                Task.is_today == True
            )
        ).order_by(Task.urgency.desc()).all()

    @staticmethod
    def get_completed_count(
        db: Session,
        start_time: datetime,
        end_time: datetime,
        is_habit: Optional[bool] = None
    ) -> int:
        """Get count of completed tasks in time range"""
        query = db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_COMPLETED,
                Task.completed_at >= start_time,
                Task.completed_at < end_time
            )
        )

        if is_habit is not None:
            query = query.filter(Task.is_habit == is_habit)

        return query.count()

    @staticmethod
    def get_completed_tasks(
        db: Session,
        start_time: datetime,
        end_time: datetime,
        is_habit: Optional[bool] = None
    ) -> List[Task]:
        """Get completed tasks in time range"""
        query = db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_COMPLETED,
                Task.completed_at >= start_time,
                Task.completed_at < end_time
            )
        )

        if is_habit is not None:
            query = query.filter(Task.is_habit == is_habit)

        return query.all()

    @staticmethod
    def get_pending_count(db: Session, today: date) -> int:
        """Get count of pending tasks for today"""
        day_start = datetime.combine(today, datetime.min.time())
        day_end = datetime.combine(today + timedelta(days=1), datetime.min.time())

        return db.query(Task).filter(
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

    @staticmethod
    def get_total_pending_count(db: Session) -> int:
        """Get total count of all pending tasks"""
        return db.query(Task).filter(Task.status == TASK_STATUS_PENDING).count()

    @staticmethod
    def get_overdue_habits(db: Session, before_date: datetime) -> List[Task]:
        """Get habits that are overdue (due before specified date)"""
        return db.query(Task).filter(
            and_(
                Task.is_habit == True,
                Task.status == TASK_STATUS_PENDING,
                Task.due_date < before_date
            )
        ).all()

    @staticmethod
    def get_critical_tasks(
        db: Session,
        start_date: datetime,
        end_date: datetime
    ) -> List[Task]:
        """Get critical tasks (due within date range)"""
        return db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_habit == False,
                Task.due_date <= end_date,
                Task.due_date >= start_date
            )
        ).all()

    @staticmethod
    def get_available_tasks(db: Session) -> List[Task]:
        """Get all available pending non-habit tasks"""
        return db.query(Task).filter(
            and_(
                Task.status == TASK_STATUS_PENDING,
                Task.is_habit == False,
                Task.is_today == False
            )
        ).all()

    @staticmethod
    def get_incomplete_today_tasks(db: Session) -> List[Task]:
        """Get tasks scheduled for today that haven't been completed"""
        return db.query(Task).filter(
            and_(
                Task.is_habit == False,
                Task.is_today == True,
                Task.status != TASK_STATUS_COMPLETED
            )
        ).all()

    @staticmethod
    def get_habits_due_in_range(
        db: Session,
        start_time: datetime,
        end_time: datetime
    ) -> List[Task]:
        """Get habits due within date range"""
        return db.query(Task).filter(
            and_(
                Task.is_habit == True,
                Task.due_date >= start_time,
                Task.due_date < end_time
            )
        ).all()

    @staticmethod
    def count_habits_due_in_range(
        db: Session,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """Count habits due within date range"""
        return db.query(Task).filter(
            and_(
                Task.is_habit == True,
                Task.due_date >= start_time,
                Task.due_date < end_time
            )
        ).count()

    @staticmethod
    def get_missed_habits(
        db: Session,
        start_time: datetime,
        end_time: datetime
    ) -> List[Task]:
        """Get habits due but not completed in date range"""
        return db.query(Task).filter(
            and_(
                Task.is_habit == True,
                Task.due_date >= start_time,
                Task.due_date < end_time,
                Task.status != TASK_STATUS_COMPLETED
            )
        ).all()

    @staticmethod
    def create(db: Session, task: Task) -> Task:
        """Create a new task"""
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def update(db: Session, task: Task) -> Task:
        """Update existing task"""
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def delete(db: Session, task: Task) -> None:
        """Delete a task"""
        db.delete(task)
        db.commit()

    @staticmethod
    def clear_today_flag(db: Session) -> None:
        """Clear is_today flag from all non-habit tasks"""
        db.query(Task).filter(
            and_(
                Task.is_habit == False,
                Task.is_today == True
            )
        ).update({Task.is_today: False})
        db.commit()
