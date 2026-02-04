"""
Points HTTP routes.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import List

from backend.core.database import get_db
from backend.core.security import verify_api_key
from backend.modules.settings import SettingsService
from .service import PointsService
from .schemas import PointHistoryResponse

router = APIRouter(prefix="/api/points", tags=["points"])


@router.get("")
@router.get("/current")
def get_current_points(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get current total points."""
    settings_service = SettingsService(db)
    points_service = PointsService(db)
    today = settings_service.get_effective_date()
    return {"points": points_service.get_current_points(today)}


@router.get("/history", response_model=List[PointHistoryResponse])
def get_point_history(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get point history for last N days."""
    settings_service = SettingsService(db)
    points_service = PointsService(db)
    today = settings_service.get_effective_date()
    return points_service.get_history(days, today)


@router.get("/history/{target_date}")
def get_day_details(
    target_date: date,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get detailed breakdown for a specific day."""
    from backend.modules.tasks import TaskService
    from backend.shared.date_utils import get_day_range

    settings_service = SettingsService(db)
    points_service = PointsService(db)
    task_service = TaskService(db)

    settings = settings_service.get()

    # Get history for the date
    history = points_service.get_history_for_date(target_date)

    if not history:
        raise HTTPException(status_code=404, detail=f"No history for {target_date}")

    # Get day range for task query
    day_start, day_end = get_day_range(
        target_date,
        settings.day_start_enabled,
        settings.day_start_time
    )

    # Get completed tasks for the day
    completed_tasks = task_service._get_completed_in_range(day_start, day_end)
    completed_habits = task_service._get_completed_habits_in_range(day_start, day_end)

    return {
        "date": history.date,
        "points_earned": history.points_earned,
        "points_penalty": history.points_penalty,
        "points_bonus": history.points_bonus,
        "daily_total": history.daily_total,
        "cumulative_total": history.cumulative_total,
        "tasks_completed": history.tasks_completed,
        "habits_completed": history.habits_completed,
        "tasks_planned": history.tasks_planned,
        "completion_rate": history.completion_rate,
        "penalty_streak": history.penalty_streak,
        "completed_tasks": [
            {
                "id": t.id,
                "description": t.description,
                "energy": t.energy,
                "time_spent": t.time_spent,
                "completed_at": t.completed_at
            }
            for t in completed_tasks
        ],
        "completed_habits": [
            {
                "id": h.id,
                "description": h.description,
                "energy": h.energy,
                "streak": h.streak,
                "completed_at": h.completed_at
            }
            for h in completed_habits
        ]
    }


@router.get("/projection")
def get_projection(
    target_date: date = Query(...),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Calculate point projections until target date."""
    settings_service = SettingsService(db)
    points_service = PointsService(db)
    today = settings_service.get_effective_date()
    current_total = points_service.get_current_points(today)
    return points_service.calculate_projection(today, target_date, current_total)
