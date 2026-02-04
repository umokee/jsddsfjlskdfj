"""
Goal Pydantic schemas for API request/response.
"""
from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional


class PointGoalBase(BaseModel):
    goal_type: str = Field(default="points", pattern="^(points|project_completion)$")
    target_points: Optional[int] = Field(None, ge=1)  # Required for points goals
    project_name: Optional[str] = Field(None, max_length=200)  # Required for project_completion goals
    reward_description: str = Field(..., min_length=1, max_length=500)
    deadline: Optional[date] = None


class PointGoalCreate(PointGoalBase):
    """Schema for creating a goal."""
    pass


class PointGoalUpdate(BaseModel):
    """Schema for updating a goal."""
    goal_type: Optional[str] = Field(None, pattern="^(points|project_completion)$")
    target_points: Optional[int] = Field(None, ge=1)
    project_name: Optional[str] = Field(None, max_length=200)
    reward_description: Optional[str] = Field(None, min_length=1, max_length=500)
    deadline: Optional[date] = None
    achieved: Optional[bool] = None
    reward_claimed: Optional[bool] = None


class PointGoalResponse(PointGoalBase):
    """Schema for goal response."""
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
