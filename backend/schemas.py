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

    # Habit recurrence settings
    recurrence_type: str = Field(default="none")  # none, daily, every_n_days, weekly
    recurrence_interval: int = Field(default=1, ge=1, le=30)
    recurrence_days: Optional[str] = None  # JSON array for weekly: "[0,2,4]"

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

    # Habit recurrence settings
    recurrence_type: Optional[str] = None
    recurrence_interval: Optional[int] = Field(None, ge=1, le=30)
    recurrence_days: Optional[str] = None

class TaskResponse(TaskBase):
    id: int
    status: str
    urgency: float
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

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
