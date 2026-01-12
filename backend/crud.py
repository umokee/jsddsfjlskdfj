from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import datetime, timedelta, date
from typing import List, Optional
import random
import json

from backend.models import Task, Settings, PointHistory, PointGoal, RestDay
from backend.schemas import TaskCreate, TaskUpdate, SettingsUpdate, PointGoalCreate, PointGoalUpdate, RestDayCreate

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

def get_all_habits(db: Session) -> List[Task]:
    """Get all pending habits"""
    return db.query(Task).filter(
        and_(
            Task.status == "pending",
            Task.is_habit == True
        )
    ).order_by(Task.due_date).all()

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

    # For recurring habits without due_date, set it to today
    if db_task.is_habit and db_task.recurrence_type != "none" and not db_task.due_date:
        db_task.due_date = datetime.combine(date.today(), datetime.min.time())

    # Normalize due_date to midnight (remove time component) to avoid time-based deletions
    if db_task.due_date:
        db_task.due_date = datetime.combine(db_task.due_date.date(), datetime.min.time())

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
            elapsed = (datetime.utcnow() - task.started_at).total_seconds()
            task.time_spent = (task.time_spent or 0) + int(elapsed)
        task.status = "pending"
        task.started_at = None  # Important: clear old started_at

    if task_id:
        db_task = get_task(db, task_id)
        if db_task:
            db_task.status = "active"
            db_task.started_at = datetime.utcnow()  # Set fresh started_at
            db_task.is_today = True
    else:
        # Start next available task
        db_task = get_next_task(db) or get_next_habit(db)
        if db_task:
            db_task.status = "active"
            db_task.started_at = datetime.utcnow()  # Set fresh started_at

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
            elapsed = (datetime.utcnow() - active_task.started_at).total_seconds()
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

    completion_date = datetime.utcnow()
    db_task.status = "completed"
    db_task.completed_at = completion_date

    # Calculate elapsed time and add to time_spent
    if db_task.started_at:
        elapsed = (completion_date - db_task.started_at).total_seconds()
        db_task.time_spent = (db_task.time_spent or 0) + int(elapsed)

    # Handle habits: update streak and create next occurrence
    if db_task.is_habit and db_task.recurrence_type != "none":
        today = date.today()

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

def roll_tasks(db: Session, mood: Optional[str] = None, daily_limit: int = 5, critical_days: int = 2) -> dict:
    """Generate daily task plan (max once per day)"""
    today = datetime.utcnow().date()
    settings = get_settings(db)

    # Check if roll was already done today
    if settings.last_roll_date == today:
        return {
            "error": "Roll already done today",
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
    """Calculate points for completing a task (without priority bonus)"""
    base = settings.points_per_task_base

    # Bonus for energy (0-5)
    energy_bonus = task.energy * settings.energy_weight

    # Smart time tracking with automatic estimation
    actual_time = task.time_spent if task.time_spent else 0
    # Automatic estimated time based on energy: energy * minutes_per_unit * 60 seconds
    expected_time = task.energy * settings.minutes_per_energy_unit * 60

    time_modifier = 0.0

    if actual_time > 0 and expected_time > 0:
        # Calculate efficiency: expected / actual
        # > 1.0 means faster than expected (bonus)
        # < 1.0 means slower than expected (penalty)
        efficiency = expected_time / actual_time

        # If easy task (energy <= 2) done very slowly (efficiency < 0.3) - big penalty
        if task.energy <= 2 and efficiency < 0.3:
            time_modifier = -base * 0.5
        elif efficiency > 1.0:
            # Bonus for efficiency (max 50% of base)
            time_modifier = min(base * settings.time_efficiency_weight * (efficiency - 1), base * 0.5)
        else:
            # Penalty for inefficiency
            time_modifier = -base * settings.time_efficiency_weight * (1 - efficiency)

    total_points = base + energy_bonus + time_modifier

    # Minimum 20% of (base + energy) to ensure energy effort is rewarded
    minimum_points = int((base + energy_bonus) * 0.2)
    return max(int(total_points), minimum_points)


def calculate_habit_points(task: Task, settings: Settings) -> int:
    """Calculate points for completing a habit"""
    base = settings.points_per_habit_base
    # Cap streak bonus at 30 days (habit formation period)
    # With new defaults: 10 + 30*1 = 40 max points per habit
    capped_streak = min(task.streak, 30)
    streak_bonus = capped_streak * settings.streak_multiplier
    return int(base + streak_bonus)


def get_or_create_today_history(db: Session) -> PointHistory:
    """Get or create point history for today"""
    today = date.today()
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
        "time": datetime.utcnow().isoformat()
    })
    history.details = json.dumps(details)

    db.commit()


def _finalize_day_penalties(db: Session, target_date: date) -> dict:
    """Internal function to finalize penalties for a specific date"""
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

    # Set tasks_planned to actual count (fair completion rate)
    if day_history.tasks_planned == 0:
        day_history.tasks_planned = max(day_history.tasks_completed, 1)

    penalty = 0

    # Check if idle day (no tasks/habits completed at all)
    if day_history.tasks_completed == 0 and day_history.habits_completed == 0:
        penalty += settings.idle_day_penalty
    else:
        # Calculate completion rate
        completion_rate = min(day_history.tasks_completed / day_history.tasks_planned, 1.0)
        day_history.completion_rate = completion_rate

        # Penalty for incomplete day (threshold now 80% instead of 50%)
        if completion_rate < settings.incomplete_day_threshold:
            penalty += int(settings.incomplete_day_penalty * (1 - completion_rate))

    # Progressive penalty for missed habits based on streak
    # The longer the streak, the bigger the penalty for breaking it
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
            # Base penalty
            habit_penalty = settings.missed_habit_penalty_base
            # Add progressive penalty based on streak: penalty * (1 + factor * streak)
            # E.g., streak 20, factor 0.5: penalty * (1 + 0.5 * 20) = penalty * 11
            if habit.streak > 0:
                habit_penalty = int(habit_penalty * (1 + settings.progressive_penalty_factor * habit.streak))
            penalty += habit_penalty

    # Apply penalties (but never go below 0 cumulative)
    day_history.points_penalty = penalty
    day_history.daily_total = day_history.points_earned + day_history.points_bonus - day_history.points_penalty
    day_history.cumulative_total = max(0, day_history.cumulative_total - penalty)

    db.commit()

    return {
        "penalty": penalty,
        "completion_rate": day_history.completion_rate,
        "tasks_completed": day_history.tasks_completed,
        "tasks_planned": day_history.tasks_planned,
        "missed_habits": missed_habits
    }


def calculate_daily_penalties(db: Session) -> dict:
    """Calculate penalties for YESTERDAY (called during Roll for new day)"""
    yesterday = date.today() - timedelta(days=1)
    return _finalize_day_penalties(db, yesterday)


def get_point_history(db: Session, days: int = 30) -> List[PointHistory]:
    """Get point history for last N days"""
    start_date = date.today() - timedelta(days=days)
    return db.query(PointHistory).filter(
        PointHistory.date >= start_date
    ).order_by(PointHistory.date.desc()).all()


def get_current_points(db: Session) -> int:
    """Get current total points"""
    history = get_or_create_today_history(db)
    return history.cumulative_total


def calculate_projection(db: Session, target_date: date) -> dict:
    """Calculate point projections until target date"""
    # Get last 30 days average
    history = get_point_history(db, 30)

    if not history:
        avg_per_day = 0
    else:
        total_daily = sum(h.daily_total for h in history)
        avg_per_day = total_daily / len(history)

    current_total = get_current_points(db)
    days_until = (target_date - date.today()).days

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
