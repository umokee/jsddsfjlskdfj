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

    class Config:
        from_attributes = True

class StatsResponse(BaseModel):
    done_today: int
    pending_today: int
    total_pending: int
    active_task: Optional[TaskResponse]


# Settings schemas
class SettingsBase(BaseModel):
    max_tasks_per_day: int = Field(default=10, ge=1, le=100)
    points_per_task_base: int = Field(default=10, ge=1, le=1000)
    points_per_habit_base: int = Field(default=10, ge=1, le=1000)
    streak_multiplier: float = Field(default=1.0, ge=0.0, le=10.0)
    energy_weight: float = Field(default=3.0, ge=0.0, le=20.0)
    time_efficiency_weight: float = Field(default=0.5, ge=0.0, le=5.0)
    minutes_per_energy_unit: int = Field(default=30, ge=5, le=180)
    incomplete_day_penalty: int = Field(default=20, ge=0, le=500)
    incomplete_day_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    missed_habit_penalty_base: int = Field(default=50, ge=0, le=500)
    progressive_penalty_factor: float = Field(default=0.5, ge=0.0, le=5.0)
    idle_tasks_penalty: int = Field(default=20, ge=0, le=500)
    idle_habits_penalty: int = Field(default=20, ge=0, le=500)
    penalty_streak_reset_days: int = Field(default=3, ge=1, le=30)
    routine_habit_multiplier: float = Field(default=0.5, ge=0.0, le=1.0)


class SettingsUpdate(SettingsBase):
    pass


class SettingsResponse(SettingsBase):
    id: int
    updated_at: datetime

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
    target_points: int = Field(..., ge=1)
    reward_description: str = Field(..., min_length=1, max_length=500)
    deadline: Optional[date] = None


class PointGoalCreate(PointGoalBase):
    pass


class PointGoalUpdate(BaseModel):
    target_points: Optional[int] = Field(None, ge=1)
    reward_description: Optional[str] = Field(None, min_length=1, max_length=500)
    deadline: Optional[date] = None
    achieved: Optional[bool] = None


class PointGoalResponse(PointGoalBase):
    id: int
    achieved: bool
    achieved_date: Optional[date]
    created_at: datetime

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
