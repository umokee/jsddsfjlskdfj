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
    import json
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

    # Parse details JSON for penalties and planned tasks
    details = {}
    if history.details:
        try:
            details = json.loads(history.details)
            if isinstance(details, list):
                details = {"task_completions": details}
        except json.JSONDecodeError:
            details = {}

    penalty_breakdown = details.get("penalty_breakdown", {})
    penalties = {
        "idle_penalty": penalty_breakdown.get("idle_penalty", 0),
        "incomplete_penalty": penalty_breakdown.get("incomplete_penalty", 0),
        "missed_habits_penalty": penalty_breakdown.get("missed_habits_penalty", 0),
        "progressive_multiplier": penalty_breakdown.get("progressive_multiplier", 1.0),
        "penalty_streak": penalty_breakdown.get("penalty_streak", 0),
        "total": penalty_breakdown.get("total_penalty", 0),
        "missed_habits": penalty_breakdown.get("missed_habits", []),
        "incomplete_tasks": penalty_breakdown.get("incomplete_tasks", [])
    }

    # Get points for each task/habit from details
    task_completions = details.get("task_completions", [])
    points_map = {
        item["task_id"]: item["points"]
        for item in task_completions
        if "task_id" in item and "points" in item
    }

    return {
        "date": history.date,
        "summary": {
            "points_earned": history.points_earned,
            "points_penalty": history.points_penalty,
            "points_bonus": history.points_bonus,
            "daily_total": history.daily_total,
            "cumulative_total": history.cumulative_total,
            "tasks_completed": history.tasks_completed,
            "habits_completed": history.habits_completed,
            "tasks_planned": history.tasks_planned,
            "completion_rate": history.completion_rate,
        },
        "completed_tasks": [
            {
                "id": t.id,
                "description": t.description,
                "project": t.project,
                "energy": t.energy,
                "time_spent": t.time_spent,
                "completed_at": t.completed_at,
                "points": points_map.get(t.id, 0)
            }
            for t in completed_tasks
        ],
        "completed_habits": [
            {
                "id": h.id,
                "description": h.description,
                "habit_type": h.habit_type,
                "energy": h.energy,
                "streak": h.streak,
                "completed_at": h.completed_at,
                "points": points_map.get(h.id, 0)
            }
            for h in completed_habits
        ],
        "penalties": penalties,
        "planned_tasks": details.get("planned_tasks", [])
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
