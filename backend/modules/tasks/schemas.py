"""
Task Pydantic schemas for API request/response.
"""
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List, Any


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
    """Schema for creating a task."""
    pass


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    project: Optional[str] = None
    priority: Optional[int] = Field(None, ge=0, le=10)
    energy: Optional[int] = Field(None, ge=0, le=5)
    is_habit: Optional[bool] = None
    is_today: Optional[bool] = None
    due_date: Optional[datetime] = None
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
    """Schema for task response."""
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
    """Schema for daily statistics."""
    done_today: int
    pending_today: int
    total_pending: int
    habits_done: int = 0
    habits_total: int = 0
    active_task: Optional[TaskResponse] = None


class TaskResult(BaseModel):
    """Internal DTO for task completion result - used by workflows."""
    id: int
    description: str
    energy: int
    priority: int
    is_habit: bool
    habit_type: str
    streak: int
    time_spent: int
    started_at: Optional[datetime]
    daily_target: int
    daily_completed: int
    fully_completed: bool  # True if task is fully done (or habit reached daily_target)


class RollResult(BaseModel):
    """Result of rolling tasks for the day."""
    tasks: List[Any]  # TaskResponse objects
    habits: List[Any]  # TaskResponse objects
    deleted_habits: int
    error: Optional[str] = None
