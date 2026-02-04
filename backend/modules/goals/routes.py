"""
Goals HTTP routes.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from backend.core.database import get_db
from backend.core.security import verify_api_key
from backend.modules.tasks import TaskService
from .service import GoalService
from .schemas import PointGoalCreate, PointGoalUpdate, PointGoalResponse
from .exceptions import GoalNotFoundError, InvalidGoalError

router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.get("", response_model=List[PointGoalResponse])
def get_goals(
    include_achieved: bool = Query(False),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get all goals with optional project progress."""
    goal_service = GoalService(db)
    task_service = TaskService(db)

    goals = goal_service.get_all(include_achieved)

    # Enrich with project progress
    for i, goal in enumerate(goals):
        goals[i] = goal_service.enrich_with_progress(
            goal,
            task_service.get_project_progress
        )

    return goals


@router.post("", response_model=PointGoalResponse)
def create_goal(
    goal_data: PointGoalCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Create a new goal."""
    goal_service = GoalService(db)
    task_service = TaskService(db)

    # Check if project has tasks (for project_completion goals)
    project_has_tasks = True
    if goal_data.goal_type == "project_completion" and goal_data.project_name:
        progress = task_service.get_project_progress(goal_data.project_name)
        project_has_tasks = progress.get("total_tasks", 0) > 0

    try:
        return goal_service.create(goal_data, project_has_tasks)
    except InvalidGoalError as e:
        raise HTTPException(status_code=400, detail=str(e.message))


@router.put("/{goal_id}", response_model=PointGoalResponse)
def update_goal(
    goal_id: int,
    goal_update: PointGoalUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Update a goal."""
    service = GoalService(db)
    try:
        return service.update(goal_id, goal_update)
    except GoalNotFoundError:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")


@router.delete("/{goal_id}")
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Delete a goal."""
    service = GoalService(db)
    try:
        service.delete(goal_id)
        return {"message": "Goal deleted successfully"}
    except GoalNotFoundError:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")


@router.post("/{goal_id}/claim", response_model=PointGoalResponse)
def claim_reward(
    goal_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Claim reward for an achieved goal."""
    service = GoalService(db)
    try:
        return service.claim_reward(goal_id)
    except GoalNotFoundError:
        raise HTTPException(status_code=404, detail=f"Goal {goal_id} not found")
    except InvalidGoalError as e:
        raise HTTPException(status_code=400, detail=str(e.message))
