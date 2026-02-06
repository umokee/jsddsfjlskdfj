"""
Task HTTP routes.
Note: Some complex operations (complete, roll) use workflows.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.core.database import get_db
from backend.core.security import verify_api_key
from backend.core.exceptions import NotFoundError
from .service import TaskService
from .schemas import TaskCreate, TaskUpdate, TaskResponse, StatsResponse
from .exceptions import TaskNotFoundError, DependencyNotMetError

# Import settings for getting effective date
from backend.modules.settings import SettingsService

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("", response_model=List[TaskResponse])
def get_tasks(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get all tasks."""
    service = TaskService(db)
    return service.get_all(skip, limit)


@router.get("/pending", response_model=List[TaskResponse])
def get_pending_tasks(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get all pending tasks (excluding habits)."""
    service = TaskService(db)
    return service.get_pending()


@router.get("/current", response_model=Optional[TaskResponse])
def get_current_task(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get currently active task."""
    service = TaskService(db)
    return service.get_active()


@router.get("/habits", response_model=List[TaskResponse])
def get_habits(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get all pending habits."""
    service = TaskService(db)
    return service.get_habits()


@router.get("/today", response_model=List[TaskResponse])
def get_today_tasks(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get today's scheduled tasks (non-habits)."""
    service = TaskService(db)
    return service.get_today_tasks()


@router.get("/today-habits", response_model=List[TaskResponse])
def get_today_habits(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get habits due today."""
    task_service = TaskService(db)
    settings_service = SettingsService(db)
    today = settings_service.get_effective_date()
    return task_service.get_today_habits(today)


@router.get("/can-roll")
def can_roll(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Check if roll is available."""
    task_service = TaskService(db)
    settings_service = SettingsService(db)
    settings = settings_service.get()

    can, error_msg = task_service.can_roll(
        effective_today=settings.effective_date,
        last_roll_date=settings.last_roll_date,
        day_start_enabled=settings.day_start_enabled,
        roll_available_time=settings.roll_available_time
    )

    return {"can_roll": can, "error_message": error_msg}


@router.get("/stats", response_model=StatsResponse)
def get_stats(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get daily statistics."""
    task_service = TaskService(db)
    settings_service = SettingsService(db)
    settings = settings_service.get()

    return task_service.get_stats(
        today=settings.effective_date,
        day_start_enabled=settings.day_start_enabled,
        day_start_time=settings.day_start_time
    )


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get a specific task."""
    service = TaskService(db)
    try:
        return service.get(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@router.post("", response_model=TaskResponse)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Create a new task."""
    task_service = TaskService(db)
    settings_service = SettingsService(db)
    settings = settings_service.get()

    return task_service.create(
        task_data,
        effective_today=settings.effective_date,
        last_roll_date=settings.last_roll_date
    )


@router.put("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Update an existing task."""
    service = TaskService(db)
    try:
        return service.update(task_id, task_update)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@router.delete("/{task_id}")
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Delete a task."""
    service = TaskService(db)
    try:
        service.delete(task_id)
        return {"message": "Task deleted successfully"}
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@router.post("/start", response_model=Optional[TaskResponse])
def start_task(
    task_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Start a task (stop all active first)."""
    service = TaskService(db)
    try:
        return service.start(task_id)
    except DependencyNotMetError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Task {e.task_id} cannot be started: dependency {e.dependency_id} not completed"
        )


@router.post("/stop")
def stop_task(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Stop active task."""
    service = TaskService(db)
    stopped = service.stop()
    return {"stopped": stopped}


# Cross-module operations using workflows

@router.post("/done", response_model=Optional[TaskResponse])
def complete_task(
    task_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Complete a task (active or specified)."""
    from backend.workflows import CompleteTaskWorkflow

    workflow = CompleteTaskWorkflow(db)
    try:
        return workflow.execute(task_id)
    except TaskNotFoundError:
        raise HTTPException(status_code=404, detail="No task to complete")
    except DependencyNotMetError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Task {e.task_id} cannot be completed: dependency {e.dependency_id} not completed"
        )


@router.post("/roll")
def roll_tasks(
    mood: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Generate daily task plan."""
    from backend.workflows import RollDayWorkflow

    workflow = RollDayWorkflow(db)
    result = workflow.execute(mood)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return {
        "message": "Daily plan generated",
        "habits_count": len(result["habits"]),
        "tasks_count": len(result["tasks"]),
        "deleted_habits": result["deleted_habits"],
        "habits": result["habits"],
        "tasks": result["tasks"],
        "penalty_info": result.get("penalty_info")
    }


@router.post("/complete-roll")
def complete_roll(
    mood: str = Query(...),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Complete morning check-in with selected mood."""
    from backend.workflows import RollDayWorkflow

    workflow = RollDayWorkflow(db)
    result = workflow.complete_roll(mood)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result
