"""
Points Pydantic schemas for API request/response.
"""
from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional, List, Any


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
    """Schema for point history response."""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PointsCalculationResult(BaseModel):
    """Result of points calculation for a task."""
    points: int
    energy_multiplier: float
    time_quality_factor: float
    focus_factor: float


class DayDetailsResponse(BaseModel):
    """Detailed breakdown for a specific day."""
    date: str
    summary: dict
    completed_tasks: List[dict]
    completed_habits: List[dict]
    penalties: dict
    planned_tasks: List[dict] = []
    error: Optional[str] = None


class ProjectionResponse(BaseModel):
    """Point projection response."""
    current_total: int
    days_until: int
    avg_per_day: float
    min_projection: Optional[int] = None
    avg_projection: Optional[int] = None
    max_projection: Optional[int] = None
    projection: Optional[int] = None  # For same-day requests
