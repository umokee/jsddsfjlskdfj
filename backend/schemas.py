from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional

class TaskBase(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    project: Optional[str] = None
    priority: int = Field(default=5, ge=0, le=10)
    energy: int = Field(default=3, ge=0, le=5)
    is_habit: bool = False
    is_today: bool = False
    due_date: Optional[datetime] = None
    estimated_time: int = Field(default=0, ge=0)  # Estimated time in seconds
    depends_on: Optional[int] = None  # ID of task that must be completed first

    # Habit recurrence settings
    recurrence_type: str = Field(default="none")  # none, daily, every_n_days, weekly
    recurrence_interval: int = Field(default=1, ge=1, le=30)
    recurrence_days: Optional[str] = None  # JSON array for weekly: "[0,2,4]"
    habit_type: str = Field(default="skill")  # skill or routine
    daily_target: int = Field(default=1, ge=1, le=20)  # How many times per day

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    project: Optional[str] = None
    priority: Optional[int] = Field(None, ge=0, le=10)
    energy: Optional[int] = Field(None, ge=0, le=5)
    is_habit: Optional[bool] = None
    is_today: Optional[bool] = None
    due_date: Optional[datetime] = None
    status: Optional[str] = None
    estimated_time: Optional[int] = Field(None, ge=0)
    depends_on: Optional[int] = None

    # Habit recurrence settings
    recurrence_type: Optional[str] = None
    recurrence_interval: Optional[int] = Field(None, ge=1, le=30)
    recurrence_days: Optional[str] = None
    habit_type: Optional[str] = None
    daily_target: Optional[int] = Field(None, ge=1, le=20)
    daily_completed: Optional[int] = Field(None, ge=0, le=20)

class TaskResponse(TaskBase):
    id: int
    status: str
    urgency: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Time tracking
    time_spent: int = 0  # Total seconds spent on this task
    estimated_time: int = 0  # Estimated time in seconds

    # Habit-specific fields
    streak: int = 0
    last_completed_date: Optional[date] = None
    daily_target: int = 1
    daily_completed: int = 0

    # Dependency info (populated by API)
    dependency_name: Optional[str] = None
    dependency_completed: bool = True  # True if no dependency or dependency is done

    class Config:
        from_attributes = True

class StatsResponse(BaseModel):
    done_today: int
    pending_today: int
    total_pending: int
    habits_done: int = 0
    habits_total: int = 0
    active_task: Optional[TaskResponse]


# Settings schemas
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
    pending_roll: bool = Field(default=False)

    # Backup settings
    auto_backup_enabled: bool = Field(default=True)
    backup_time: str = Field(default="03:00", pattern=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
    backup_interval_days: int = Field(default=1, ge=1, le=30)
    backup_keep_local_count: int = Field(default=10, ge=1, le=100)
    google_drive_enabled: bool = Field(default=False)


class SettingsUpdate(SettingsBase):
    pass


class SettingsResponse(SettingsBase):
    id: int
    updated_at: datetime
    last_backup_date: Optional[datetime] = None
    effective_date: Optional[date] = None  # Current effective date based on day_start_time

    class Config:
        from_attributes = True


# Point History schemas
class PointHistoryBase(BaseModel):
    date: date
    points_earned: int = 0
    points_penalty: int = 0
    points_bonus: int = 0
    daily_total: int = 0
    cumulative_total: int = 0
    tasks_completed: int = 0
    habits_completed: int = 0
    tasks_planned: int = 0
    completion_rate: float = 0.0
    penalty_streak: int = 0
    details: Optional[str] = None


class PointHistoryResponse(PointHistoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Point Goal schemas
class PointGoalBase(BaseModel):
    goal_type: str = Field(default="points", pattern="^(points|project_completion)$")
    target_points: Optional[int] = Field(None, ge=1)  # Required for points goals
    project_name: Optional[str] = Field(None, max_length=200)  # Required for project_completion goals
    reward_description: str = Field(..., min_length=1, max_length=500)
    deadline: Optional[date] = None


class PointGoalCreate(PointGoalBase):
    pass


class PointGoalUpdate(BaseModel):
    goal_type: Optional[str] = Field(None, pattern="^(points|project_completion)$")
    target_points: Optional[int] = Field(None, ge=1)
    project_name: Optional[str] = Field(None, max_length=200)
    reward_description: Optional[str] = Field(None, min_length=1, max_length=500)
    deadline: Optional[date] = None
    achieved: Optional[bool] = None
    reward_claimed: Optional[bool] = None


class PointGoalResponse(PointGoalBase):
    id: int
    achieved: bool
    achieved_date: Optional[date]
    reward_claimed: bool
    reward_claimed_at: Optional[datetime]
    created_at: datetime
    # Project progress (only for project_completion goals)
    total_tasks: Optional[int] = None
    completed_tasks: Optional[int] = None

    class Config:
        from_attributes = True


# Rest Day schemas
class RestDayBase(BaseModel):
    date: date
    description: Optional[str] = None


class RestDayCreate(RestDayBase):
    pass


class RestDayResponse(RestDayBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Backup schemas
class BackupBase(BaseModel):
    filename: str
    size_bytes: int
    backup_type: str = "auto"


class BackupResponse(BackupBase):
    id: int
    filepath: str
    created_at: datetime
    uploaded_to_drive: bool = False
    google_drive_id: Optional[str] = None
    status: str = "completed"
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

