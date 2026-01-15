from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Date
from datetime import datetime, date
from backend.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    project = Column(String, nullable=True)
    priority = Column(Integer, default=5)  # 0-10
    energy = Column(Integer, default=3)    # 0-5
    status = Column(String, default="pending")  # pending, active, completed
    is_habit = Column(Boolean, default=False)
    is_today = Column(Boolean, default=False)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    urgency = Column(Float, default=0.0)

    # Time tracking (accumulated seconds)
    time_spent = Column(Integer, default=0)  # Total seconds spent on this task
    estimated_time = Column(Integer, default=0)  # Estimated time in seconds

    # Task dependencies
    depends_on = Column(Integer, nullable=True)  # ID of task that must be completed first

    # Habit-specific fields
    recurrence_type = Column(String, default="none")  # none, daily, every_n_days, weekly
    recurrence_interval = Column(Integer, default=1)   # For every_n_days: interval in days
    recurrence_days = Column(String, nullable=True)    # For weekly: JSON array like "[1,3,5]" (Mon,Wed,Fri)
    habit_type = Column(String, default="skill")  # skill (new habit) or routine (daily routine)
    streak = Column(Integer, default=0)                # Current streak count
    last_completed_date = Column(Date, nullable=True)  # Last completion date for streak tracking

    def calculate_urgency(self):
        """Calculate task urgency based on priority, due date, and energy"""
        urgency = 0.0

        # Priority coefficient (0-10) * 10
        urgency += self.priority * 10.0

        # Due date coefficient
        if self.due_date:
            # Handle both timezone-aware and timezone-naive datetimes
            due_date_naive = self.due_date.replace(tzinfo=None) if self.due_date.tzinfo else self.due_date
            now_naive = datetime.utcnow()

            days_until = (due_date_naive - now_naive).days
            if days_until <= 0:
                urgency += 50.0  # Overdue
            elif days_until <= 2:
                urgency += 25.0  # Critical
            elif days_until <= 7:
                urgency += 10.0  # Soon

        # Energy coefficient
        if self.energy >= 4:
            urgency += 5.0  # High energy
        elif self.energy <= 1:
            urgency -= 1.0  # Low energy

        self.urgency = urgency
        return urgency


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    # Task limits
    max_tasks_per_day = Column(Integer, default=10)

    # Base points (rebalanced - lower rewards)
    points_per_task_base = Column(Integer, default=10)
    points_per_habit_base = Column(Integer, default=10)  # Reduced from 15

    # Multipliers and weights
    streak_multiplier = Column(Float, default=1.0)  # Reduced from 2.0
    energy_weight = Column(Float, default=3.0)
    time_efficiency_weight = Column(Float, default=0.5)

    # Time estimation (automatic calculation)
    minutes_per_energy_unit = Column(Integer, default=30)  # 30 min per energy level

    # Penalties
    incomplete_day_penalty = Column(Integer, default=20)
    incomplete_day_threshold = Column(Float, default=0.8)  # 80% completion required (was 50%)
    missed_habit_penalty_base = Column(Integer, default=50)
    progressive_penalty_factor = Column(Float, default=0.5)  # Multiplier for penalty streak
    idle_tasks_penalty = Column(Integer, default=20)  # Penalty for 0 tasks completed
    idle_habits_penalty = Column(Integer, default=20)  # Penalty for 0 habits completed
    penalty_streak_reset_days = Column(Integer, default=3)  # Days without penalties to reset streak

    # Habit types
    routine_habit_multiplier = Column(Float, default=0.5)  # Points multiplier for routine habits

    # Roll limits
    last_roll_date = Column(Date, nullable=True)  # Track last roll to enforce 1/day

    # Time-based settings
    roll_available_time = Column(String, default="00:00")  # Time when Roll becomes available (HH:MM format)
    auto_penalties_enabled = Column(Boolean, default=True)  # Auto-apply penalties at midnight
    auto_roll_enabled = Column(Boolean, default=False)  # Enable automatic roll
    auto_roll_time = Column(String, default="06:00")  # Time for automatic roll (HH:MM format)

    # Updated timestamp
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PointHistory(Base):
    __tablename__ = "point_history"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)

    # Points breakdown
    points_earned = Column(Integer, default=0)  # Total earned from tasks/habits
    points_penalty = Column(Integer, default=0)  # Total penalties
    points_bonus = Column(Integer, default=0)   # Daily completion bonuses
    daily_total = Column(Integer, default=0)    # Net for the day
    cumulative_total = Column(Integer, default=0)  # Running total

    # Task statistics
    tasks_completed = Column(Integer, default=0)
    habits_completed = Column(Integer, default=0)
    tasks_planned = Column(Integer, default=0)  # Tasks that were in TODAY
    completion_rate = Column(Float, default=0.0)

    # Penalty streak tracking
    penalty_streak = Column(Integer, default=0)  # Consecutive days with penalties

    # Detailed breakdown (JSON)
    details = Column(String, nullable=True)  # JSON with per-task breakdown

    created_at = Column(DateTime, default=datetime.utcnow)


class PointGoal(Base):
    __tablename__ = "point_goals"

    id = Column(Integer, primary_key=True, index=True)
    target_points = Column(Integer, nullable=False)
    reward_description = Column(String, nullable=False)
    deadline = Column(Date, nullable=True)
    achieved = Column(Boolean, default=False)
    achieved_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RestDay(Base):
    __tablename__ = "rest_days"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)  # Optional reason (e.g., "New Year", "Rest day")
    created_at = Column(DateTime, default=datetime.utcnow)
