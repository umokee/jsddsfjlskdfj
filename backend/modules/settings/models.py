"""
Settings database model.
PRIVATE - do not import from outside this module.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Date
from datetime import datetime

from core.database import Base


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
