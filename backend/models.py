"""
Unified database models.
All models are defined here to ensure single SQLAlchemy Base is used.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Date
from datetime import datetime, date
from backend.core.database import Base

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
    created_at = Column(DateTime, default=datetime.now)
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
    daily_target = Column(Integer, default=1)          # How many times per day habit should be completed
    daily_completed = Column(Integer, default=0)       # How many times completed today

    def calculate_urgency(self):
        """
        Calculate task urgency for weighted random selection.

        Formula: urgency = priority × 10 + due_date_bonus + energy_bonus

        Higher urgency = higher probability of being selected for today's plan.
        """
        urgency = 0.0

        # Priority component (0-10) × 10 = 0-100
        urgency += self.priority * 10.0

        # Due date component
        if self.due_date:
            # Handle both timezone-aware and timezone-naive datetimes
            due_date_naive = self.due_date.replace(tzinfo=None) if self.due_date.tzinfo else self.due_date
            now_naive = datetime.now()

            days_until = (due_date_naive - now_naive).days
            if days_until <= 0:
                urgency += 100.0  # Overdue - maximum priority
            elif days_until <= 2:
                urgency += 75.0   # Critical - very high probability (~90-99%)
            elif days_until <= 7:
                urgency += 30.0   # Soon - noticeably higher probability

        # Energy component
        if self.energy >= 4:
            urgency += 5.0   # High energy - slightly increases probability
        elif self.energy <= 1:
            urgency -= 5.0   # Low energy - slightly decreases probability

        self.urgency = urgency
        return urgency


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    # Task limits
    max_tasks_per_day = Column(Integer, default=10)

    # Base points
    points_per_task_base = Column(Integer, default=10)
    points_per_habit_base = Column(Integer, default=10)

    # === BALANCED PROGRESS v2.0 ===

    # Energy multiplier: EnergyMult = energy_mult_base + (energy * energy_mult_step)
    # E0 -> 0.6, E1 -> 0.8, E2 -> 1.0, E3 -> 1.2, E4 -> 1.4, E5 -> 1.6
    energy_mult_base = Column(Float, default=0.6)
    energy_mult_step = Column(Float, default=0.2)

    # Time quality: expected_time = energy * minutes_per_energy_unit
    minutes_per_energy_unit = Column(Integer, default=20)  # 20 min per energy level
    min_work_time_seconds = Column(Integer, default=120)   # Min 2 min for full points

    # Streak bonus for skill habits: 1 + log2(streak+1) * streak_log_factor
    streak_log_factor = Column(Float, default=0.15)

    # Routine habits: fixed points, no streak
    routine_points_fixed = Column(Integer, default=6)

    # Daily completion bonus
    completion_bonus_full = Column(Float, default=0.10)   # 10% bonus for 100% completion
    completion_bonus_good = Column(Float, default=0.05)   # 5% bonus for 80%+ completion

    # Penalties
    idle_penalty = Column(Integer, default=30)  # Penalty for 0 tasks AND 0 habits
    incomplete_penalty_percent = Column(Float, default=0.5)  # 50% of missed potential points

    missed_habit_penalty_base = Column(Integer, default=15)  # Base penalty for missed habit
    progressive_penalty_factor = Column(Float, default=0.1)  # Step per penalty_streak day
    progressive_penalty_max = Column(Float, default=1.5)     # Max progressive multiplier
    penalty_streak_reset_days = Column(Integer, default=2)   # Days without penalty to reset

    # Legacy fields (kept for backward compatibility, not used in v2.0)
    streak_multiplier = Column(Float, default=1.0)
    energy_weight = Column(Float, default=3.0)
    time_efficiency_weight = Column(Float, default=0.5)
    idle_tasks_penalty = Column(Integer, default=20)
    idle_habits_penalty = Column(Integer, default=20)
    routine_habit_multiplier = Column(Float, default=0.5)

    # Roll limits
    last_roll_date = Column(Date, nullable=True)  # Track last roll to enforce 1/day

    # Day boundary settings
    day_start_enabled = Column(Boolean, default=False)  # Enable custom day start time
    day_start_time = Column(String, default="06:00")  # When new day starts (for shifted schedules)

    # Time-based settings
    roll_available_time = Column(String, default="00:00")  # Time when Roll becomes available (HH:MM format)
    auto_penalties_enabled = Column(Boolean, default=True)  # Auto-apply penalties at midnight
    penalty_time = Column(String, default="00:01")  # Time when penalties are calculated (HH:MM format)
    auto_roll_enabled = Column(Boolean, default=False)  # Enable automatic roll
    auto_roll_time = Column(String, default="06:00")  # Time for automatic roll (HH:MM format)
    pending_roll = Column(Boolean, default=False)  # Auto-roll triggered, waiting for user mood selection
    pending_roll_started_at = Column(DateTime, nullable=True)  # When pending_roll was set to True
    auto_mood_timeout_hours = Column(Integer, default=4)  # Hours after which to auto-complete roll with max energy

    # Backup settings
    auto_backup_enabled = Column(Boolean, default=True)  # Enable automatic backups
    backup_time = Column(String, default="03:00")  # Time for automatic backup (HH:MM format)
    backup_interval_days = Column(Integer, default=1)  # Backup every N days
    backup_keep_local_count = Column(Integer, default=10)  # Keep last N local backups
    google_drive_enabled = Column(Boolean, default=False)  # Upload to Google Drive
    last_backup_date = Column(DateTime, nullable=True)  # Last successful backup timestamp

    # Updated timestamp
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


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

    created_at = Column(DateTime, default=datetime.now)


class PointGoal(Base):
    __tablename__ = "point_goals"

    id = Column(Integer, primary_key=True, index=True)
    goal_type = Column(String, default="points")  # "points" or "project_completion"
    target_points = Column(Integer, nullable=True)  # For points goals
    project_name = Column(String, nullable=True)  # For project_completion goals
    reward_description = Column(String, nullable=False)  # What you'll reward yourself
    reward_claimed = Column(Boolean, default=False)  # Did you claim the reward?
    reward_claimed_at = Column(DateTime, nullable=True)  # When claimed
    deadline = Column(Date, nullable=True)
    achieved = Column(Boolean, default=False)
    achieved_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class RestDay(Base):
    __tablename__ = "rest_days"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)  # Optional reason (e.g., "New Year", "Rest day")
    created_at = Column(DateTime, default=datetime.now)


class Backup(Base):
    __tablename__ = "backups"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)  # e.g., "backup_2024-01-15_14-30-00.db"
    filepath = Column(String, nullable=False)  # Local path
    size_bytes = Column(Integer, nullable=False)  # File size in bytes
    created_at = Column(DateTime, default=datetime.now, index=True)

    # Google Drive info
    google_drive_id = Column(String, nullable=True)  # Google Drive file ID
    uploaded_to_drive = Column(Boolean, default=False)

    # Backup type
    backup_type = Column(String, default="auto")  # "auto" or "manual"

    # Status
    status = Column(String, default="completed")  # "completed", "failed", "uploading"
    error_message = Column(String, nullable=True)
