from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import os
from pathlib import Path

from backend.infrastructure.database import engine, get_db, Base
from backend import models  # Import all models to register them with Base
from backend.schemas import (
    TaskCreate, TaskUpdate, TaskResponse, StatsResponse,
    SettingsUpdate, SettingsResponse,
    PointHistoryResponse,
    PointGoalCreate, PointGoalUpdate, PointGoalResponse,
    RestDayCreate, RestDayResponse,
    BackupResponse
)
from backend.middleware.auth import verify_api_key
from backend import crud
from backend.services.scheduler_service import start_scheduler, stop_scheduler
from backend.infrastructure.migrations import auto_migrate
from backend.services import backup_service
from datetime import date

# Configure logging for fail2ban integration
from backend.constants import DEFAULT_LOG_DIRECTORY_PROD, DEFAULT_LOG_DIRECTORY_DEV

LOG_DIR = os.getenv("TASK_MANAGER_LOG_DIR", DEFAULT_LOG_DIRECTORY_PROD)
LOG_FILE = os.getenv("TASK_MANAGER_LOG_FILE", "app.log")

# Create log directory if it doesn't exist (for development)
try:
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    log_path = Path(LOG_DIR) / LOG_FILE
except PermissionError:
    # Fallback to local directory if no permissions for /var/log
    LOG_DIR = DEFAULT_LOG_DIRECTORY_DEV
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    log_path = Path(LOG_DIR) / LOG_FILE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler()  # Also log to console
    ]
)

logger = logging.getLogger("task_manager")

# Create database tables
Base.metadata.create_all(bind=engine)

# Run automatic schema migrations (add missing columns)
try:
    auto_migrate()
except Exception as e:
    logger.error(f"Auto-migration failed: {e}")
    # Don't crash the app - continue with existing schema

app = FastAPI(
    title="Task Manager API",
    description="Minimalist task manager with priorities and energy levels",
    version="1.0.0"
)

# CORS settings for React frontend
from backend.constants import CORS_ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Task Manager API started. Logging to: {log_path}")
    # Start background scheduler for automatic tasks
    start_scheduler()
    logger.info("Background scheduler started")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Task Manager API")
    stop_scheduler()
    logger.info("Background scheduler stopped")

# Health check (no auth required)
@app.get("/")
async def root():
    return {"message": "Task Manager API", "status": "active"}

# Auth-required endpoints
@app.get("/api/tasks", response_model=List[TaskResponse], dependencies=[Depends(verify_api_key)])
async def get_tasks(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all tasks with optional filtering"""
    if status_filter:
        tasks = db.query(models.Task).filter(models.Task.status == status_filter).offset(skip).limit(limit).all()
    else:
        tasks = crud.get_tasks(db, skip, limit)
    return tasks

@app.get("/api/tasks/pending", response_model=List[TaskResponse], dependencies=[Depends(verify_api_key)])
async def get_pending_tasks(db: Session = Depends(get_db)):
    """Get all pending tasks sorted by urgency"""
    return crud.get_pending_tasks(db)

@app.get("/api/tasks/current", response_model=Optional[TaskResponse], dependencies=[Depends(verify_api_key)])
async def get_current_task(db: Session = Depends(get_db)):
    """Get current task (active or next available)"""
    task = crud.get_active_task(db)
    if not task:
        task = crud.get_next_task(db)
    if not task:
        task = crud.get_next_habit(db)
    return task

@app.get("/api/tasks/habits", response_model=List[TaskResponse], dependencies=[Depends(verify_api_key)])
async def get_habits(db: Session = Depends(get_db)):
    """Get all pending habits"""
    return crud.get_all_habits(db)

@app.get("/api/tasks/today", response_model=List[TaskResponse], dependencies=[Depends(verify_api_key)])
async def get_today_tasks_endpoint(db: Session = Depends(get_db)):
    """Get today's tasks (is_today=True)"""
    return crud.get_today_tasks(db)

@app.get("/api/tasks/today-habits", response_model=List[TaskResponse], dependencies=[Depends(verify_api_key)])
async def get_today_habits_endpoint(db: Session = Depends(get_db)):
    """Get today's habits"""
    return crud.get_today_habits(db)

@app.get("/api/stats", response_model=StatsResponse, dependencies=[Depends(verify_api_key)])
async def get_stats(db: Session = Depends(get_db)):
    """Get daily statistics"""
    stats = crud.get_stats(db)
    active_task = crud.get_active_task(db)
    return {
        **stats,
        "active_task": active_task
    }

@app.get("/api/tasks/{task_id}", response_model=TaskResponse, dependencies=[Depends(verify_api_key)])
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """Get a specific task"""
    task = crud.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.post("/api/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_key)])
async def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task"""
    return crud.create_task(db, task)

@app.put("/api/tasks/{task_id}", response_model=TaskResponse, dependencies=[Depends(verify_api_key)])
async def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db)):
    """Update a task"""
    task = crud.update_task(db, task_id, task_update)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_api_key)])
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task"""
    if not crud.delete_task(db, task_id):
        raise HTTPException(status_code=404, detail="Task not found")

@app.post("/api/tasks/start", response_model=Optional[TaskResponse], dependencies=[Depends(verify_api_key)])
async def start_task(task_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Start a task (or next available if no ID provided)"""
    task = crud.start_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="No task available to start")
    return task

@app.post("/api/tasks/stop", dependencies=[Depends(verify_api_key)])
async def stop_task(db: Session = Depends(get_db)):
    """Stop active task"""
    if not crud.stop_task(db):
        raise HTTPException(status_code=404, detail="No active task")
    return {"message": "Task stopped"}

@app.post("/api/tasks/done", response_model=Optional[TaskResponse], dependencies=[Depends(verify_api_key)])
async def complete_task(task_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Complete a task (active or specified)"""
    task = crud.complete_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="No task to complete")
    return task

@app.get("/api/tasks/can-roll", dependencies=[Depends(verify_api_key)])
async def can_roll_today(db: Session = Depends(get_db)):
    """Check if roll is available right now (considering time)"""
    can_roll, error_msg = crud.can_roll_now(db)
    settings = crud.get_settings(db)
    return {
        "can_roll": can_roll,
        "error_message": error_msg if not can_roll else None,
        "roll_available_time": settings.roll_available_time,
        "last_roll_date": settings.last_roll_date.isoformat() if settings.last_roll_date else None
    }

@app.post("/api/tasks/roll", dependencies=[Depends(verify_api_key)])
async def roll_tasks(mood: Optional[str] = None, db: Session = Depends(get_db)):
    """Generate daily task plan"""
    result = crud.roll_tasks(db, mood)

    # Check if there was an error (already rolled today)
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


# ===== SETTINGS ENDPOINTS =====

@app.get("/api/settings", response_model=SettingsResponse, dependencies=[Depends(verify_api_key)])
async def get_settings_endpoint(db: Session = Depends(get_db)):
    """Get settings"""
    return crud.get_settings(db)


@app.put("/api/settings", response_model=SettingsResponse, dependencies=[Depends(verify_api_key)])
async def update_settings_endpoint(settings_update: SettingsUpdate, db: Session = Depends(get_db)):
    """Update settings"""
    return crud.update_settings(db, settings_update)


# ===== POINTS ENDPOINTS =====

@app.get("/api/points/current", dependencies=[Depends(verify_api_key)])
async def get_current_points_endpoint(db: Session = Depends(get_db)):
    """Get current total points"""
    return {"points": crud.get_current_points(db)}


@app.get("/api/points/history", response_model=List[PointHistoryResponse], dependencies=[Depends(verify_api_key)])
async def get_points_history_endpoint(days: int = 30, db: Session = Depends(get_db)):
    """Get point history for last N days"""
    return crud.get_point_history(db, days)


@app.get("/api/points/projection", dependencies=[Depends(verify_api_key)])
async def get_points_projection_endpoint(target_date: str, db: Session = Depends(get_db)):
    """Calculate point projection until target date (format: YYYY-MM-DD)"""
    try:
        target = date.fromisoformat(target_date)
        return crud.calculate_projection(db, target)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")


# ===== GOALS ENDPOINTS =====

@app.get("/api/goals", response_model=List[PointGoalResponse], dependencies=[Depends(verify_api_key)])
async def get_goals_endpoint(include_achieved: bool = False, db: Session = Depends(get_db)):
    """Get point goals"""
    return crud.get_point_goals(db, include_achieved)


@app.post("/api/goals", response_model=PointGoalResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_key)])
async def create_goal_endpoint(goal: PointGoalCreate, db: Session = Depends(get_db)):
    """Create a new point goal"""
    return crud.create_point_goal(db, goal)


@app.put("/api/goals/{goal_id}", response_model=PointGoalResponse, dependencies=[Depends(verify_api_key)])
async def update_goal_endpoint(goal_id: int, goal_update: PointGoalUpdate, db: Session = Depends(get_db)):
    """Update a point goal"""
    goal = crud.update_point_goal(db, goal_id, goal_update)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@app.delete("/api/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_api_key)])
async def delete_goal_endpoint(goal_id: int, db: Session = Depends(get_db)):
    """Delete a point goal"""
    if not crud.delete_point_goal(db, goal_id):
        raise HTTPException(status_code=404, detail="Goal not found")


# ===== REST DAYS ENDPOINTS =====

@app.get("/api/rest-days", response_model=List[RestDayResponse], dependencies=[Depends(verify_api_key)])
async def get_rest_days_endpoint(db: Session = Depends(get_db)):
    """Get all rest days"""
    return crud.get_rest_days(db)


@app.post("/api/rest-days", response_model=RestDayResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(verify_api_key)])
async def create_rest_day_endpoint(rest_day: RestDayCreate, db: Session = Depends(get_db)):
    """Create a rest day"""
    return crud.create_rest_day(db, rest_day)


@app.delete("/api/rest-days/{rest_day_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_api_key)])
async def delete_rest_day_endpoint(rest_day_id: int, db: Session = Depends(get_db)):
    """Delete a rest day"""
    if not crud.delete_rest_day(db, rest_day_id):
        raise HTTPException(status_code=404, detail="Rest day not found")


# ===== BACKUP ENDPOINTS =====

@app.get("/api/backups", response_model=List[BackupResponse], dependencies=[Depends(verify_api_key)])
async def get_backups_endpoint(limit: int = 50, db: Session = Depends(get_db)):
    """Get all backups (newest first)"""
    return backup_service.get_all_backups(db, limit)


@app.post("/api/backups/create", response_model=BackupResponse, dependencies=[Depends(verify_api_key)])
async def create_backup_endpoint(db: Session = Depends(get_db)):
    """Create a manual backup"""
    backup = backup_service.create_local_backup(db, backup_type="manual")

    if not backup:
        raise HTTPException(status_code=500, detail="Failed to create backup")

    # Upload to Google Drive if enabled
    settings = crud.get_settings(db)
    if settings.google_drive_enabled:
        try:
            backup_service.upload_to_google_drive(backup)
        except Exception as e:
            logger.error(f"Google Drive upload failed: {e}")
            # Continue anyway - local backup exists

    return backup


@app.get("/api/backups/{backup_id}/download", dependencies=[Depends(verify_api_key)])
async def download_backup_endpoint(backup_id: int, db: Session = Depends(get_db)):
    """Download a backup file"""
    backup = backup_service.get_backup_by_id(db, backup_id)

    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")

    if not os.path.exists(backup.filepath):
        raise HTTPException(status_code=404, detail="Backup file not found on disk")

    return FileResponse(
        path=backup.filepath,
        filename=backup.filename,
        media_type='application/x-sqlite3'
    )


@app.delete("/api/backups/{backup_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(verify_api_key)])
async def delete_backup_endpoint(backup_id: int, db: Session = Depends(get_db)):
    """Delete a backup"""
    if not backup_service.delete_backup(db, backup_id):
        raise HTTPException(status_code=404, detail="Backup not found")

if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
