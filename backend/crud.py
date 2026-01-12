from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta
from typing import List, Optional
import random

from backend.models import Task
from backend.schemas import TaskCreate, TaskUpdate

def get_task(db: Session, task_id: int) -> Optional[Task]:
    return db.query(Task).filter(Task.id == task_id).first()

def get_tasks(db: Session, skip: int = 0, limit: int = 100) -> List[Task]:
    return db.query(Task).offset(skip).limit(limit).all()

def get_pending_tasks(db: Session) -> List[Task]:
    return db.query(Task).filter(Task.status == "pending").order_by(Task.urgency.desc()).all()

def get_active_task(db: Session) -> Optional[Task]:
    return db.query(Task).filter(Task.status == "active").first()

def get_next_task(db: Session) -> Optional[Task]:
    """Get next task (non-habit, today, pending) sorted by urgency"""
    return db.query(Task).filter(
        and_(
            Task.status == "pending",
            Task.is_today == True,
            Task.is_habit == False
        )
    ).order_by(Task.urgency.desc()).first()

def get_next_habit(db: Session) -> Optional[Task]:
    """Get next habit for today"""
    today = datetime.utcnow().date()
    return db.query(Task).filter(
        and_(
            Task.status == "pending",
            Task.is_habit == True,
            Task.due_date >= datetime.combine(today, datetime.min.time()),
            Task.due_date < datetime.combine(today + timedelta(days=1), datetime.min.time())
        )
    ).first()

def get_today_habits(db: Session) -> List[Task]:
    """Get all habits for today"""
    today = datetime.utcnow().date()
    return db.query(Task).filter(
        and_(
            Task.status == "pending",
            Task.is_habit == True,
            Task.due_date >= datetime.combine(today, datetime.min.time()),
            Task.due_date < datetime.combine(today + timedelta(days=1), datetime.min.time())
        )
    ).all()

def get_stats(db: Session) -> dict:
    """Get daily statistics"""
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today + timedelta(days=1), datetime.min.time())

    done_today = db.query(Task).filter(
        and_(
            Task.status == "completed",
            Task.completed_at >= today_start,
            Task.completed_at < today_end
        )
    ).count()

    pending_today = db.query(Task).filter(
        and_(
            Task.status == "pending",
            or_(
                Task.is_today == True,
                and_(
                    Task.due_date >= today_start,
                    Task.due_date < today_end
                )
            )
        )
    ).count()

    total_pending = db.query(Task).filter(Task.status == "pending").count()

    return {
        "done_today": done_today,
        "pending_today": pending_today,
        "total_pending": total_pending
    }

def create_task(db: Session, task: TaskCreate) -> Task:
    db_task = Task(**task.model_dump())
    db_task.calculate_urgency()
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_task(db: Session, task_id: int, task_update: TaskUpdate) -> Optional[Task]:
    db_task = get_task(db, task_id)
    if not db_task:
        return None

    update_data = task_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)

    db_task.calculate_urgency()
    db.commit()
    db.refresh(db_task)
    return db_task

def delete_task(db: Session, task_id: int) -> bool:
    db_task = get_task(db, task_id)
    if not db_task:
        return False
    db.delete(db_task)
    db.commit()
    return True

def start_task(db: Session, task_id: Optional[int] = None) -> Optional[Task]:
    """Start a task (stop all active first)"""
    # Stop all active tasks
    active_tasks = db.query(Task).filter(Task.status == "active").all()
    for task in active_tasks:
        task.status = "pending"

    if task_id:
        db_task = get_task(db, task_id)
        if db_task:
            db_task.status = "active"
            db_task.started_at = datetime.utcnow()
            db_task.is_today = True
    else:
        # Start next available task
        db_task = get_next_task(db) or get_next_habit(db)
        if db_task:
            db_task.status = "active"
            db_task.started_at = datetime.utcnow()

    db.commit()
    if db_task:
        db.refresh(db_task)
    return db_task

def stop_task(db: Session) -> bool:
    """Stop active task"""
    active_task = get_active_task(db)
    if active_task:
        active_task.status = "pending"
        db.commit()
        return True
    return False

def complete_task(db: Session, task_id: Optional[int] = None) -> Optional[Task]:
    """Complete a task (active or specified)"""
    if task_id:
        db_task = get_task(db, task_id)
    else:
        db_task = get_active_task(db)

    if db_task:
        db_task.status = "completed"
        db_task.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(db_task)
    return db_task

def roll_tasks(db: Session, mood: Optional[str] = None, daily_limit: int = 5, critical_days: int = 2) -> dict:
    """Generate daily task plan"""
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())

    # 1. Delete overdue habits
    overdue_habits = db.query(Task).filter(
        and_(
            Task.is_habit == True,
            Task.status == "pending",
            Task.due_date < today_start
        )
    ).all()
    for habit in overdue_habits:
        db.delete(habit)

    # 2. Clear today tag from regular tasks
    db.query(Task).filter(
        and_(
            Task.is_habit == False,
            Task.is_today == True
        )
    ).update({Task.is_today: False})

    # 3. Add critical tasks (due soon)
    critical_date = today_start + timedelta(days=critical_days)
    critical_tasks = db.query(Task).filter(
        and_(
            Task.status == "pending",
            Task.is_habit == False,
            Task.due_date <= critical_date,
            Task.due_date >= today_start
        )
    ).all()

    for task in critical_tasks:
        task.is_today = True

    # 4. Add random tasks to fill daily limit
    slots = max(0, daily_limit - len(critical_tasks))
    if slots > 0:
        query = db.query(Task).filter(
            and_(
                Task.status == "pending",
                Task.is_habit == False,
                Task.is_today == False
            )
        )

        if mood and mood.isdigit():
            energy_level = int(mood)
            if 0 <= energy_level <= 5:
                query = query.filter(Task.energy <= energy_level)  # До N включительно

        available_tasks = query.limit(20).all()
        random.shuffle(available_tasks)

        for task in available_tasks[:slots]:
            task.is_today = True

    db.commit()

    # Get plan summary
    habits = get_today_habits(db)
    today_tasks = db.query(Task).filter(
        and_(
            Task.status == "pending",
            Task.is_today == True,
            Task.is_habit == False
        )
    ).order_by(Task.urgency.desc()).all()

    return {
        "habits": habits,
        "tasks": today_tasks,
        "deleted_habits": len(overdue_habits)
    }
