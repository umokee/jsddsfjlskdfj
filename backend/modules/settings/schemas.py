"""
Settings Pydantic schemas for API request/response.
"""
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional


class SettingsBase(BaseModel):
    max_tasks_per_day: int = Field(default=10, ge=1, le=100)
    points_per_task_base: int = Field(default=10, ge=1, le=1000)
    points_per_habit_base: int = Field(default=10, ge=1, le=1000)

    # === BALANCED PROGRESS v2.0 ===

    # Energy multiplier settings
    energy_mult_base: float = Field(default=0.6, ge=0.1, le=2.0)
    energy_mult_step: float = Field(default=0.2, ge=0.0, le=1.0)

    # Time quality settings
    minutes_per_energy_unit: int = Field(default=20, ge=5, le=120)
    min_work_time_seconds: int = Field(default=120, ge=0, le=600)

    # Streak settings for skill habits
    streak_log_factor: float = Field(default=0.15, ge=0.0, le=1.0)

    # Routine habits
    routine_points_fixed: int = Field(default=6, ge=1, le=50)

    # Daily completion bonus
    completion_bonus_full: float = Field(default=0.10, ge=0.0, le=0.5)
    completion_bonus_good: float = Field(default=0.05, ge=0.0, le=0.3)

    # Penalties
    idle_penalty: int = Field(default=30, ge=0, le=500)
    incomplete_penalty_percent: float = Field(default=0.5, ge=0.0, le=1.0)  # 50% of missed potential

    missed_habit_penalty_base: int = Field(default=15, ge=0, le=500)
    progressive_penalty_factor: float = Field(default=0.1, ge=0.0, le=1.0)
    progressive_penalty_max: float = Field(default=1.5, ge=1.0, le=5.0)
    penalty_streak_reset_days: int = Field(default=2, ge=1, le=30)

    # Legacy fields (kept for backward compatibility)
    streak_multiplier: float = Field(default=1.0, ge=0.0, le=10.0)
    energy_weight: float = Field(default=3.0, ge=0.0, le=20.0)
    time_efficiency_weight: float = Field(default=0.5, ge=0.0, le=5.0)
    idle_tasks_penalty: int = Field(default=20, ge=0, le=500)
    idle_habits_penalty: int = Field(default=20, ge=0, le=500)
    routine_habit_multiplier: float = Field(default=0.5, ge=0.0, le=1.0)

    # Day boundary settings
    day_start_enabled: bool = Field(default=False)
    day_start_time: str = Field(default="06:00", pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")

    # Time-based settings
    roll_available_time: str = Field(default="00:00", pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
    auto_penalties_enabled: bool = Field(default=True)
    penalty_time: str = Field(default="00:01", pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
    auto_roll_enabled: bool = Field(default=False)
    auto_roll_time: str = Field(default="06:00", pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
    auto_mood_timeout_hours: int = Field(default=4, ge=1, le=24)  # Hours to wait before auto-completing roll
    pending_roll: bool = Field(default=False)

    # Backup settings
    auto_backup_enabled: bool = Field(default=True)
    backup_time: str = Field(default="03:00", pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
    backup_interval_days: int = Field(default=1, ge=1, le=30)
    backup_keep_local_count: int = Field(default=10, ge=1, le=100)
    google_drive_enabled: bool = Field(default=False)


class SettingsUpdate(SettingsBase):
    """Schema for updating settings."""
    pass


class SettingsResponse(SettingsBase):
    """Schema for settings response."""
    id: int
    updated_at: datetime
    last_roll_date: Optional[date] = None  # Track last roll to enforce 1/day
    last_backup_date: Optional[datetime] = None
    effective_date: Optional[date] = None  # Current effective date based on day_start_time
    pending_roll_started_at: Optional[datetime] = None  # When pending_roll was set (read-only)

    class Config:
        from_attributes = True


class SettingsData(BaseModel):
    """Internal DTO for passing settings data between modules."""
    day_start_enabled: bool
    day_start_time: str
    max_tasks_per_day: int
    points_per_task_base: int
    points_per_habit_base: int
    energy_mult_base: float
    energy_mult_step: float
    minutes_per_energy_unit: int
    min_work_time_seconds: int
    streak_log_factor: float
    routine_points_fixed: int
    completion_bonus_full: float
    completion_bonus_good: float
    idle_penalty: int
    incomplete_penalty_percent: float
    missed_habit_penalty_base: int
    progressive_penalty_factor: float
    progressive_penalty_max: float
    penalty_streak_reset_days: int
    roll_available_time: str
    auto_penalties_enabled: bool
    penalty_time: str
    auto_roll_enabled: bool
    auto_roll_time: str
    auto_mood_timeout_hours: int
    pending_roll: bool
    pending_roll_started_at: Optional[datetime]
    last_roll_date: Optional[date]
    auto_backup_enabled: bool
    backup_time: str
    backup_interval_days: int
    backup_keep_local_count: int
    google_drive_enabled: bool
    last_backup_date: Optional[datetime]

    class Config:
        from_attributes = True
