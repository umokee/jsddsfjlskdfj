from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta, date
from typing import List, Optional
import random
import json
import math

from backend.models import Task, Settings, PointHistory, PointGoal, RestDay
from backend.schemas import TaskCreate, TaskUpdate, SettingsUpdate, PointGoalCreate, PointGoalUpdate, RestDayCreate


def get_effective_date(settings: Settings) -> date:
    """
    Get the effective current date based on day_start_time setting.

    If day_start_enabled is True and current time is before day_start_time,
    returns yesterday's date. Otherwise returns today's date.

    Example: If day_start_time = "06:00" and current time is 03:00,
    the effective date is still yesterday because the user hasn't
    started their "new day" yet.
    """
    now = datetime.now()
    today = now.date()

    if not settings.day_start_enabled:
        return today

    # Parse day_start_time
    try:
        parts = settings.day_start_time.split(":")
        day_start_hour = int(parts[0])
        day_start_minute = int(parts[1])
    except (ValueError, IndexError):
        return today

    # If current time is before day_start_time, we're still in "yesterday"
    current_minutes = now.hour * 60 + now.minute
    start_minutes = day_start_hour * 60 + day_start_minute

    if current_minutes < start_minutes:
        return today - timedelta(days=1)

    return today


def get_effective_today(db: Session) -> date:
    """Convenience function: get settings and return effective date"""
    settings = db.query(Settings).first()
    if not settings:
        return date.today()
    return get_effective_date(settings)


def calculate_next_occurrence(start_date: datetime, recurrence_type: str, recurrence_interval: int = 1) -> datetime:
    """
    Calculate next occurrence date for recurring habits.
    If start_date is in the past, calculates the next future occurrence.

    Args:
        start_date: Initial/start date for the habit
        recurrence_type: "daily", "every_n_days", "weekly", or "none"
        recurrence_interval: For "every_n_days", the number of days between occurrences

    Returns:
        Next occurrence date (today or in the future)
    """
    if recurrence_type == "none" or not start_date:
        return start_date

    now = datetime.now()
    current_date = start_date

    # If start_date is already in the future, return it as-is
    if current_date.replace(tzinfo=None) >= now:
        return current_date

    # Calculate next occurrence based on recurrence type
    if recurrence_type == "daily":
        # Daily recurrence
        days_diff = (now.date() - current_date.date()).days
        current_date = current_date + timedelta(days=days_diff)

        # If we're past today's time, move to tomorrow
        if current_date.replace(tzinfo=None) < now:
            current_date = current_date + timedelta(days=1)

    elif recurrence_type == "every_n_days":
        # Every N days recurrence
        days_diff = (now.date() - current_date.date()).days
        # Calculate how many intervals have passed
        intervals_passed = days_diff // recurrence_interval
        # Add one more interval to get the next future date
        next_interval = (intervals_passed + 1) * recurrence_interval
        current_date = current_date + timedelta(days=next_interval)

    elif recurrence_type == "weekly":
        # Weekly recurrence (every 7 days)
        days_diff = (now.date() - current_date.date()).days
        weeks_passed = days_diff // 7
        # Add one more week to get the next future date
        current_date = current_date + timedelta(days=(weeks_passed + 1) * 7)

    return current_date


def get_task(db: Session, task_id: int) -> Optional[Task]:
    return db.query(Task).filter(Task.id == task_id).first()

def get_tasks(db: Session, skip: int = 0, limit: int = 100) -> List[Task]:
    return db.query(Task).offset(skip).limit(limit).all()

def get_pending_tasks(db: Session) -> List[Task]:
    """Get pending tasks (excluding habits)"""
    return db.query(Task).filter(
        and_(
            Task.status == "pending",
            Task.is_habit == False
        )
    ).order_by(Task.urgency.desc()).all()

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
    """Get next habit for today (using effective date for shifted schedules)"""
    today = get_effective_today(db)
    return db.query(Task).filter(
        and_(
            Task.status == "pending",
            Task.is_habit == True,
            Task.due_date >= datetime.combine(today, datetime.min.time()),
            Task.due_date < datetime.combine(today + timedelta(days=1), datetime.min.time())
        )
    ).first()

def get_all_habits(db: Session) -> List[Task]:
    """Get all pending habits"""
    return db.query(Task).filter(
        and_(
            Task.status == "pending",
            Task.is_habit == True
        )
    ).order_by(Task.due_date).all()

def get_today_habits(db: Session) -> List[Task]:
    """Get all habits for today (using effective date for shifted schedules)"""
    today = get_effective_today(db)
    return db.query(Task).filter(
        and_(
            Task.status == "pending",
            Task.is_habit == True,
            Task.due_date >= datetime.combine(today, datetime.min.time()),
            Task.due_date < datetime.combine(today + timedelta(days=1), datetime.min.time())
        )
    ).all()

def get_today_tasks(db: Session) -> List[Task]:
    """Get today's tasks (non-habits with is_today=True)"""
    return db.query(Task).filter(
        and_(
            Task.status == "pending",
            Task.is_habit == False,
            Task.is_today == True
        )
    ).order_by(Task.urgency.desc()).all()

def get_stats(db: Session) -> dict:
    """Get daily statistics (using effective date for shifted schedules)"""
    today = get_effective_today(db)
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

    # For recurring habits without due_date, set it to today
    if db_task.is_habit and db_task.recurrence_type != "none" and not db_task.due_date:
        db_task.due_date = datetime.combine(date.today(), datetime.min.time())

    # Normalize due_date to midnight (remove time component) to avoid time-based deletions
    if db_task.due_date:
        db_task.due_date = datetime.combine(db_task.due_date.date(), datetime.min.time())

    # For recurring habits, calculate next occurrence if due_date is in the past
    if db_task.is_habit and db_task.recurrence_type != "none" and db_task.due_date:
        db_task.due_date = calculate_next_occurrence(
            db_task.due_date,
            db_task.recurrence_type,
            db_task.recurrence_interval
        )

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

    # Normalize due_date to midnight (remove time component)
    if db_task.due_date:
        db_task.due_date = datetime.combine(db_task.due_date.date(), datetime.min.time())

    # For recurring habits, calculate next occurrence if due_date is in the past
    if db_task.is_habit and db_task.recurrence_type != "none" and db_task.due_date:
        db_task.due_date = calculate_next_occurrence(
            db_task.due_date,
            db_task.recurrence_type,
            db_task.recurrence_interval
        )

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
    # Stop all active tasks (save elapsed time and clear started_at)
    active_tasks = db.query(Task).filter(Task.status == "active").all()
    for task in active_tasks:
        if task.started_at:
            elapsed = (datetime.now() - task.started_at).total_seconds()
            task.time_spent = (task.time_spent or 0) + int(elapsed)
        task.status = "pending"
        task.started_at = None  # Important: clear old started_at

    if task_id:
        db_task = get_task(db, task_id)
        if db_task:
            db_task.status = "active"
            db_task.started_at = datetime.now()  # Set fresh started_at
            db_task.is_today = True
    else:
        # Start next available TASK ONLY (not habits)
        # Habits should be started manually by user
        db_task = get_next_task(db)
        if db_task:
            db_task.status = "active"
            db_task.started_at = datetime.now()  # Set fresh started_at

    db.commit()
    if db_task:
        db.refresh(db_task)
    return db_task

def stop_task(db: Session) -> bool:
    """Stop active task and save elapsed time"""
    active_task = get_active_task(db)
    if active_task:
        # Calculate elapsed time and add to time_spent
        if active_task.started_at:
            elapsed = (datetime.now() - active_task.started_at).total_seconds()
            active_task.time_spent = (active_task.time_spent or 0) + int(elapsed)

        active_task.status = "pending"
        active_task.started_at = None  # Clear started_at when stopping
        db.commit()
        return True
    return False

def _calculate_next_due_date(task: Task, from_date: date) -> Optional[date]:
    """Calculate next due date based on recurrence settings"""
    if task.recurrence_type == "none":
        return None

    if task.recurrence_type == "daily":
        return from_date + timedelta(days=1)

    if task.recurrence_type == "every_n_days":
        interval = max(1, task.recurrence_interval or 1)
        return from_date + timedelta(days=interval)

    if task.recurrence_type == "weekly":
        # Parse recurrence_days JSON array like "[0,2,4]" (Mon, Wed, Fri)
        try:
            days = json.loads(task.recurrence_days) if task.recurrence_days else []
            if not days:
                return from_date + timedelta(days=7)

            # Find next occurrence
            current_weekday = from_date.weekday()
            for offset in range(1, 8):
                next_date = from_date + timedelta(days=offset)
                if next_date.weekday() in days:
                    return next_date

            # Fallback to next week
            return from_date + timedelta(days=7)
        except (json.JSONDecodeError, ValueError):
            return from_date + timedelta(days=7)

    return None

def complete_task(db: Session, task_id: Optional[int] = None) -> Optional[Task]:
    """Complete a task (active or specified)"""
    if task_id:
        db_task = get_task(db, task_id)
    else:
        db_task = get_active_task(db)

    if not db_task:
        return None

    # Prevent completing already completed tasks (prevents duplicates on fast clicks)
    if db_task.status == "completed":
        return db_task

    completion_date = datetime.now()
    db_task.status = "completed"
    db_task.completed_at = completion_date

    # Calculate elapsed time and add to time_spent
    if db_task.started_at:
        elapsed = (completion_date - db_task.started_at).total_seconds()
        db_task.time_spent = (db_task.time_spent or 0) + int(elapsed)

    # Handle habits: update streak and create next occurrence
    if db_task.is_habit and db_task.recurrence_type != "none":
        settings = get_settings(db)
        today = get_effective_date(settings)

        # Use habit's due_date as reference, or today if no due_date
        habit_due = db_task.due_date.date() if db_task.due_date else today

        # Update streak
        if db_task.last_completed_date:
            # Calculate expected occurrence based on recurrence
            if db_task.recurrence_type == "daily":
                expected_diff = 1
            elif db_task.recurrence_type == "every_n_days":
                expected_diff = max(1, db_task.recurrence_interval or 1)
            elif db_task.recurrence_type == "weekly":
                # For weekly, just check if not too old (within 2 weeks)
                expected_diff = 14
            else:
                expected_diff = 1

            days_since_last = (today - db_task.last_completed_date).days

            if days_since_last <= expected_diff:
                # On time or early - increment streak
                db_task.streak = (db_task.streak or 0) + 1
            else:
                # Missed expected completion - reset streak
                db_task.streak = 1
        else:
            # First completion
            db_task.streak = 1

        db_task.last_completed_date = today

        # Create next occurrence starting from habit's due_date (not today)
        next_due = _calculate_next_due_date(db_task, habit_due)
        if next_due:
            next_habit = Task(
                description=db_task.description,
                project=db_task.project,
                priority=db_task.priority,
                energy=db_task.energy,
                is_habit=True,
                is_today=False,
                due_date=datetime.combine(next_due, datetime.min.time()),
                recurrence_type=db_task.recurrence_type,
                recurrence_interval=db_task.recurrence_interval,
                recurrence_days=db_task.recurrence_days,
                streak=db_task.streak,  # Carry over streak
                last_completed_date=db_task.last_completed_date
            )
            next_habit.calculate_urgency()
            db.add(next_habit)

    db.commit()
    db.refresh(db_task)

    # Award points for completion
    add_task_completion_points(db, db_task)

    # Check if any goals were achieved
    check_goal_achievements(db)

    return db_task

def task_dependencies_met(db: Session, task: Task) -> bool:
    """Check if all dependencies for a task are met (completed)"""
    if not task.depends_on:
        return True  # No dependencies

    dependency = db.query(Task).filter(Task.id == task.depends_on).first()
    if not dependency:
        return True  # Dependency doesn't exist anymore, consider it met

    return dependency.status == "completed"


def task_dependency_in_today_plan(db: Session, task: Task) -> bool:
    """Check if task's dependency is already scheduled for today.
    This means the task could be completed today after its dependency.
    """
    if not task.depends_on:
        return False  # No dependency to check

    dependency = db.query(Task).filter(Task.id == task.depends_on).first()
    if not dependency:
        return False  # Dependency doesn't exist

    # Dependency is in today's plan (pending and scheduled for today)
    return dependency.status == "pending" and dependency.is_today == True


def can_roll_now(db: Session) -> tuple[bool, str]:
    """Check if roll is available right now (considering both date and time)

    Uses effective date for users with shifted schedules.

    Returns:
        (can_roll, reason) - tuple of boolean and error message if any
    """
    settings = get_settings(db)
    now = datetime.now()
    effective_today = get_effective_date(settings)
    current_time = now.strftime("%H:%M")

    # Check if already rolled today (using effective date)
    if settings.last_roll_date == effective_today:
        return False, "Roll already done today"

    # Check if current time is after roll_available_time
    # Only check time if day_start is disabled (otherwise effective_date handles it)
    if not settings.day_start_enabled and settings.last_roll_date != effective_today:
        roll_time = settings.roll_available_time or "00:00"
        if current_time < roll_time:
            return False, f"Roll will be available at {roll_time}"

    return True, ""


def roll_tasks(db: Session, mood: Optional[str] = None, daily_limit: int = 5, critical_days: int = 2) -> dict:
    """Generate daily task plan (max once per day, using effective date for shifted schedules)"""
    settings = get_settings(db)
    today = get_effective_date(settings)

    # Check if roll is available (considering time)
    can_roll, error_msg = can_roll_now(db)
    if not can_roll:
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

    today_start = datetime.combine(today, datetime.min.time())

    # 1. Delete overdue habits (only delete habits from BEFORE today, not today)
    overdue_habits = db.query(Task).filter(
        and_(
            Task.is_habit == True,
            Task.status == "pending",
            Task.due_date < today_start  # This correctly deletes only past days, not today
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
    # Two-pass approach:
    # Pass 1: Select tasks whose dependencies are already completed
    # Pass 2: If slots remain, select tasks whose dependency is in today's plan
    slots = max(0, daily_limit - len(critical_tasks))
    if slots > 0:
        # Get all available pending tasks
        available_tasks = db.query(Task).filter(
            and_(
                Task.status == "pending",
                Task.is_habit == False,
                Task.is_today == False
            )
        ).all()

        # Pass 1: Tasks with completed dependencies (or no dependencies)
        ready_tasks = [t for t in available_tasks if task_dependencies_met(db, t)]

        # Apply mood/energy filter if specified
        if mood and mood.isdigit():
            energy_level = int(mood)
            if 0 <= energy_level <= 5:
                ready_tasks = [t for t in ready_tasks if t.energy <= energy_level]

        # Shuffle for randomness
        random.shuffle(ready_tasks)

        # Select tasks up to available slots
        selected_count = 0
        for task in ready_tasks:
            if selected_count >= slots:
                break
            if not task.is_today:
                task.is_today = True
                selected_count += 1

        # Pass 2: If slots remain, select tasks whose dependency is in today's plan
        # These can be completed today after their dependency is done
        if selected_count < slots:
            # Tasks whose dependency is scheduled for today
            dependent_tasks = [t for t in available_tasks
                             if not t.is_today and task_dependency_in_today_plan(db, t)]

            # Apply mood/energy filter
            if mood and mood.isdigit():
                energy_level = int(mood)
                if 0 <= energy_level <= 5:
                    dependent_tasks = [t for t in dependent_tasks if t.energy <= energy_level]

            # Shuffle and select
            random.shuffle(dependent_tasks)
            remaining_slots = slots - selected_count
            for task in dependent_tasks[:remaining_slots]:
                task.is_today = True

    db.commit()

    # Calculate penalties for yesterday (before rolling to new day)
    penalty_info = calculate_daily_penalties(db)

    # Update last_roll_date to prevent multiple rolls per day
    settings.last_roll_date = today
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
        "deleted_habits": len(overdue_habits),
        "penalty_info": penalty_info
    }


# ===== SETTINGS FUNCTIONS =====

def get_settings(db: Session) -> Settings:
    """Get settings (create with defaults if not exists)"""
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


def update_settings(db: Session, settings_update: SettingsUpdate) -> Settings:
    """Update settings"""
    settings = get_settings(db)
    update_data = settings_update.model_dump()
    for key, value in update_data.items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return settings


# ===== POINTS CALCULATION FUNCTIONS =====

def calculate_task_points(task: Task, settings: Settings) -> int:
    """
    Calculate points for completing a task using Balanced Progress v2.0 formula.

    Formula: Points = Base × EnergyMultiplier × TimeQualityFactor × FocusFactor

    EnergyMultiplier = energy_mult_base + (energy × energy_mult_step)
        E0 -> 0.6, E1 -> 0.8, E2 -> 1.0, E3 -> 1.2, E4 -> 1.4, E5 -> 1.6

    TimeQualityFactor based on actual_time / expected_time ratio:
        - ActualTime < min_work_time: 0.5 (suspiciously fast)
        - Ratio < 0.5: 0.8 (too fast, maybe task is simpler than stated)
        - 0.5 ≤ Ratio ≤ 1.5: 1.0 (normal range)
        - 1.5 < Ratio ≤ 3.0: 0.9 (slightly slow)
        - Ratio > 3.0: 0.7 (very slow or distracted)

    FocusFactor:
        - Task was active without pauses: 1.1
        - Had pauses: 1.0
        - Completed without start: 0.8
    """
    base = settings.points_per_task_base

    # 1. Energy Multiplier
    energy_multiplier = settings.energy_mult_base + (task.energy * settings.energy_mult_step)

    # 2. Time Quality Factor
    actual_time = task.time_spent if task.time_spent else 0
    expected_time = task.energy * settings.minutes_per_energy_unit * 60  # in seconds

    if actual_time < settings.min_work_time_seconds:
        # Suspiciously fast (< 2 min by default)
        time_quality_factor = 0.5
    elif expected_time > 0:
        ratio = actual_time / expected_time
        if ratio < 0.5:
            time_quality_factor = 0.8  # Too fast
        elif ratio <= 1.5:
            time_quality_factor = 1.0  # Normal range
        elif ratio <= 3.0:
            time_quality_factor = 0.9  # Slightly slow
        else:
            time_quality_factor = 0.7  # Very slow
    else:
        # Energy = 0, no expected time
        time_quality_factor = 1.0

    # 3. Focus Factor
    if task.started_at is None:
        # Completed without starting - suspicious
        focus_factor = 0.8
    else:
        # Normal completion with tracking
        focus_factor = 1.0

    # Calculate total points
    total_points = base * energy_multiplier * time_quality_factor * focus_factor

    # Minimum 1 point for any completed task
    return max(1, int(total_points))


def calculate_habit_points(task: Task, settings: Settings) -> int:
    """
    Calculate points for completing a habit using Balanced Progress v2.0 formula.

    Skill habits: Base × StreakBonus
        StreakBonus = 1 + log₂(streak + 1) × streak_log_factor

        Examples with streak_log_factor = 0.15:
        Streak 0  -> 1.00 (first time)
        Streak 1  -> 1.15
        Streak 3  -> 1.30
        Streak 7  -> 1.45
        Streak 14 -> 1.59
        Streak 30 -> 1.74
        Streak 60 -> 1.89
        Streak 100 -> 2.00 (practical maximum)

    Routine habits: Fixed points (routine_points_fixed), no streak bonus
        Default: 6 points
    """
    # Routine habits get fixed points, no streak
    if task.habit_type != "skill":
        return settings.routine_points_fixed

    # Skill habits: base + streak bonus
    base = settings.points_per_habit_base
    streak = task.streak if task.streak else 0

    # Cap streak for calculation
    capped_streak = min(streak, settings.max_streak_bonus_days)

    # Calculate streak bonus using log₂
    # StreakBonus = 1 + log₂(streak + 1) × factor
    streak_bonus = 1 + math.log2(capped_streak + 1) * settings.streak_log_factor

    total = base * streak_bonus
    return max(1, int(total))


def get_or_create_today_history(db: Session) -> PointHistory:
    """Get or create point history for today (using effective date for shifted schedules)"""
    today = get_effective_today(db)
    history = db.query(PointHistory).filter(PointHistory.date == today).first()

    if not history:
        # Apply penalties to yesterday before creating today
        # This ensures yesterday is finalized before starting today
        yesterday = today - timedelta(days=1)
        yesterday_history = db.query(PointHistory).filter(PointHistory.date == yesterday).first()

        if yesterday_history and yesterday_history.points_penalty == 0:
            # Yesterday hasn't been finalized yet - calculate penalties
            _finalize_day_penalties(db, yesterday)
            db.refresh(yesterday_history)  # Reload after finalization

        # Get most recent history entry (handles gaps in days)
        last_history = db.query(PointHistory).filter(
            PointHistory.date < today
        ).order_by(PointHistory.date.desc()).first()
        previous_total = last_history.cumulative_total if last_history else 0

        history = PointHistory(
            date=today,
            cumulative_total=previous_total
        )
        db.add(history)
        db.commit()
        db.refresh(history)

    return history


def add_task_completion_points(db: Session, task: Task) -> None:
    """Add points when a task/habit is completed"""
    settings = get_settings(db)
    history = get_or_create_today_history(db)

    # Calculate points
    if task.is_habit:
        points = calculate_habit_points(task, settings)
        history.habits_completed += 1
    else:
        points = calculate_task_points(task, settings)
        history.tasks_completed += 1

    # Add to earned points
    history.points_earned += points

    # Update daily and cumulative totals
    history.daily_total = history.points_earned + history.points_bonus - history.points_penalty
    history.cumulative_total += points

    # Store details
    details = json.loads(history.details) if history.details else []
    details.append({
        "task_id": task.id,
        "description": task.description,
        "is_habit": task.is_habit,
        "points": points,
        "time": datetime.now().isoformat()
    })
    history.details = json.dumps(details)

    db.commit()


def _finalize_day_penalties(db: Session, target_date: date) -> dict:
    """
    Finalize penalties for a specific date using Balanced Progress v2.0 formula.

    Penalty types:
    1. Idle Penalty: 30 points for 0 tasks AND 0 habits completed
    2. Incomplete Day Penalty: % of missed task potential
       - For each incomplete task: potential = Base × EnergyMultiplier
       - Penalty = total_missed_potential × incomplete_penalty_percent (50%)
    3. Missed Habit Penalty:
       - Skill: 15 points
       - Routine: ~8 points (about half)

    Progressive multiplier:
    - Formula: 1 + min(penalty_streak × 0.1, 0.5)
    - Max multiplier: 1.5
    - Reset after 2 consecutive days without penalties
    """
    settings = get_settings(db)

    # Check if this is a rest day - no penalties
    rest_day = db.query(RestDay).filter(RestDay.date == target_date).first()
    if rest_day:
        return {
            "penalty": 0,
            "completion_rate": 1.0,
            "tasks_completed": 0,
            "tasks_planned": 0,
            "missed_habits": 0,
            "is_rest_day": True
        }

    # Get history for target date
    day_history = db.query(PointHistory).filter(PointHistory.date == target_date).first()

    # If no history for that day, no penalties
    if not day_history:
        return {
            "penalty": 0,
            "completion_rate": 0,
            "tasks_completed": 0,
            "tasks_planned": 0,
            "missed_habits": 0
        }

    # Count tasks that were completed on target date
    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

    tasks_completed = db.query(Task).filter(
        and_(
            Task.status == "completed",
            Task.completed_at >= day_start,
            Task.completed_at < day_end,
            Task.is_habit == False
        )
    ).count()

    habits_completed = db.query(Task).filter(
        and_(
            Task.status == "completed",
            Task.completed_at >= day_start,
            Task.completed_at < day_end,
            Task.is_habit == True
        )
    ).count()

    # Update completion counts (if not already set)
    if day_history.tasks_completed == 0:
        day_history.tasks_completed = tasks_completed
    if day_history.habits_completed == 0:
        day_history.habits_completed = habits_completed

    # Count habits that were due on target date
    habits_due = db.query(Task).filter(
        and_(
            Task.is_habit == True,
            Task.due_date >= day_start,
            Task.due_date < day_end
        )
    ).count()

    # Set tasks_planned (use actual completed if not tracked)
    if day_history.tasks_planned == 0:
        day_history.tasks_planned = max(day_history.tasks_completed, 1)

    penalty = 0
    missed_habits = []

    # === PENALTY 1: IDLE PENALTY ===
    # Only apply if BOTH tasks and habits are 0
    if day_history.tasks_completed == 0 and day_history.habits_completed == 0:
        penalty += settings.idle_penalty

    # === PENALTY 2: INCOMPLETE DAY PENALTY (% of missed potential) ===
    completion_rate = 0.0
    missed_task_potential = 0

    if day_history.tasks_planned > 0:
        completion_rate = min(day_history.tasks_completed / day_history.tasks_planned, 1.0)
        day_history.completion_rate = completion_rate

        # Find incomplete tasks that were scheduled for that day
        # (tasks that had is_today=True but weren't completed)
        incomplete_tasks = db.query(Task).filter(
            and_(
                Task.is_habit == False,
                Task.is_today == True,
                Task.status != "completed"
            )
        ).all()

        # Calculate potential points for each missed task
        for task in incomplete_tasks:
            # Potential = Base × EnergyMultiplier (assume perfect time/focus)
            energy_mult = settings.energy_mult_base + (task.energy * settings.energy_mult_step)
            potential = settings.points_per_task_base * energy_mult
            missed_task_potential += potential

        # Penalty = missed potential × penalty percent
        if missed_task_potential > 0:
            penalty += int(missed_task_potential * settings.incomplete_penalty_percent)

    # === DAILY CONSISTENCY BONUS ===
    # Only apply bonus if there's something earned and good completion
    if day_history.points_earned > 0:
        if completion_rate >= 1.0:
            # 100% completion: 10% bonus
            day_history.points_bonus = int(day_history.points_earned * settings.completion_bonus_full)
        elif completion_rate >= 0.8:
            # 80%+ completion: 5% bonus
            day_history.points_bonus = int(day_history.points_earned * settings.completion_bonus_good)

    # === PENALTY 3: MISSED HABITS PENALTY ===
    missed_habits_count = max(0, habits_due - day_history.habits_completed)
    if missed_habits_count > 0:
        # Get all habits that were due but not completed
        missed_habits = db.query(Task).filter(
            and_(
                Task.is_habit == True,
                Task.due_date >= day_start,
                Task.due_date < day_end,
                Task.status != "completed"
            )
        ).all()

        for habit in missed_habits:
            if habit.habit_type == "skill":
                # Full penalty for skill habits
                penalty += settings.missed_habit_penalty_base
            else:
                # Reduced penalty for routines (about half)
                penalty += int(settings.missed_habit_penalty_base * 0.5)

    # === PROGRESSIVE PENALTY MULTIPLIER ===
    yesterday_date = target_date - timedelta(days=1)
    yesterday_history = db.query(PointHistory).filter(PointHistory.date == yesterday_date).first()

    if penalty > 0:
        # Got penalties today - increment streak
        if yesterday_history and yesterday_history.penalty_streak > 0:
            day_history.penalty_streak = yesterday_history.penalty_streak + 1
        else:
            day_history.penalty_streak = 1

        # Apply progressive penalty with cap
        # Formula: 1 + min(penalty_streak × factor, max - 1)
        progressive_multiplier = 1 + min(
            day_history.penalty_streak * settings.progressive_penalty_factor,
            settings.progressive_penalty_max - 1
        )
        penalty = int(penalty * progressive_multiplier)
    else:
        # No penalties today - check if we should reset streak
        if yesterday_history:
            days_without_penalty = 1  # Today has no penalty

            # Count consecutive days without penalty
            check_date = yesterday_date
            for _ in range(settings.penalty_streak_reset_days - 1):
                hist = db.query(PointHistory).filter(PointHistory.date == check_date).first()
                if hist and hist.points_penalty == 0:
                    days_without_penalty += 1
                    check_date -= timedelta(days=1)
                else:
                    break

            if days_without_penalty >= settings.penalty_streak_reset_days:
                day_history.penalty_streak = 0  # Reset streak
            else:
                day_history.penalty_streak = yesterday_history.penalty_streak  # Keep current
        else:
            day_history.penalty_streak = 0

    # Apply bonus and penalties (cumulative never goes below 0)
    day_history.points_penalty = penalty
    day_history.daily_total = day_history.points_earned + day_history.points_bonus - day_history.points_penalty

    # Update cumulative: add bonus, subtract penalty
    net_change = day_history.points_bonus - penalty
    day_history.cumulative_total = max(0, day_history.cumulative_total + net_change)

    db.commit()

    return {
        "penalty": penalty,
        "completion_rate": day_history.completion_rate,
        "tasks_completed": day_history.tasks_completed,
        "tasks_planned": day_history.tasks_planned,
        "missed_habits": missed_habits,
        "missed_task_potential": missed_task_potential
    }


def calculate_daily_penalties(db: Session) -> dict:
    """Calculate penalties for YESTERDAY (called during Roll for new day, uses effective date)"""
    today = get_effective_today(db)
    yesterday = today - timedelta(days=1)
    return _finalize_day_penalties(db, yesterday)


def get_point_history(db: Session, days: int = 30) -> List[PointHistory]:
    """Get point history for last N days (uses effective date)"""
    today = get_effective_today(db)
    start_date = today - timedelta(days=days)
    return db.query(PointHistory).filter(
        PointHistory.date >= start_date
    ).order_by(PointHistory.date.desc()).all()


def get_current_points(db: Session) -> int:
    """Get current total points"""
    history = get_or_create_today_history(db)
    return history.cumulative_total


def calculate_projection(db: Session, target_date: date) -> dict:
    """Calculate point projections until target date (uses effective date)"""
    # Get last 30 days average
    history = get_point_history(db, 30)

    if not history:
        avg_per_day = 0
    else:
        total_daily = sum(h.daily_total for h in history)
        avg_per_day = total_daily / len(history)

    current_total = get_current_points(db)
    today = get_effective_today(db)
    days_until = (target_date - today).days

    if days_until <= 0:
        return {
            "current_total": current_total,
            "days_until": days_until,
            "avg_per_day": avg_per_day,
            "projection": current_total
        }

    # Projections
    min_projection = current_total + int(avg_per_day * 0.7 * days_until)
    avg_projection = current_total + int(avg_per_day * days_until)
    max_projection = current_total + int(avg_per_day * 1.3 * days_until)

    return {
        "current_total": current_total,
        "days_until": days_until,
        "avg_per_day": round(avg_per_day, 2),
        "min_projection": max(min_projection, current_total),
        "avg_projection": max(avg_projection, current_total),
        "max_projection": max(max_projection, current_total)
    }


# ===== POINT GOALS FUNCTIONS =====

def get_point_goals(db: Session, include_achieved: bool = False) -> List[PointGoal]:
    """Get point goals"""
    query = db.query(PointGoal)
    if not include_achieved:
        query = query.filter(PointGoal.achieved == False)
    return query.order_by(PointGoal.target_points).all()


def create_point_goal(db: Session, goal: PointGoalCreate) -> PointGoal:
    """Create a new point goal"""
    db_goal = PointGoal(**goal.model_dump())
    db.add(db_goal)
    db.commit()
    db.refresh(db_goal)
    return db_goal


def update_point_goal(db: Session, goal_id: int, goal_update: PointGoalUpdate) -> Optional[PointGoal]:
    """Update a point goal"""
    db_goal = db.query(PointGoal).filter(PointGoal.id == goal_id).first()
    if not db_goal:
        return None

    update_data = goal_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_goal, key, value)

    db.commit()
    db.refresh(db_goal)
    return db_goal


def delete_point_goal(db: Session, goal_id: int) -> bool:
    """Delete a point goal"""
    db_goal = db.query(PointGoal).filter(PointGoal.id == goal_id).first()
    if not db_goal:
        return False
    db.delete(db_goal)
    db.commit()
    return True


def check_goal_achievements(db: Session) -> List[PointGoal]:
    """Check and mark achieved goals"""
    current_total = get_current_points(db)
    goals = get_point_goals(db, include_achieved=False)

    achieved_goals = []
    for goal in goals:
        if current_total >= goal.target_points:
            goal.achieved = True
            goal.achieved_date = date.today()
            achieved_goals.append(goal)

    if achieved_goals:
        db.commit()

    return achieved_goals


# ===== REST DAY FUNCTIONS =====

def get_rest_days(db: Session) -> List[RestDay]:
    """Get all rest days"""
    return db.query(RestDay).order_by(RestDay.date).all()


def create_rest_day(db: Session, rest_day: RestDayCreate) -> RestDay:
    """Create a rest day"""
    db_rest_day = RestDay(**rest_day.model_dump())
    db.add(db_rest_day)
    db.commit()
    db.refresh(db_rest_day)
    return db_rest_day


def delete_rest_day(db: Session, rest_day_id: int) -> bool:
    """Delete a rest day"""
    db_rest_day = db.query(RestDay).filter(RestDay.id == rest_day_id).first()
    if not db_rest_day:
        return False
    db.delete(db_rest_day)
    db.commit()
    return True
