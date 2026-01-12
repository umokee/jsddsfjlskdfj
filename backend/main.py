from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import os
from pathlib import Path

from backend.database import engine, get_db, Base
from backend.models import Task
from backend.schemas import TaskCreate, TaskUpdate, TaskResponse, StatsResponse
from backend.auth import verify_api_key
from backend import crud

# Configure logging for fail2ban integration
LOG_DIR = os.getenv("TASK_MANAGER_LOG_DIR", "/var/log/task-manager")
LOG_FILE = os.getenv("TASK_MANAGER_LOG_FILE", "app.log")

# Create log directory if it doesn't exist (for development)
try:
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    log_path = Path(LOG_DIR) / LOG_FILE
except PermissionError:
    # Fallback to local directory if no permissions for /var/log
    LOG_DIR = "./logs"
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

app = FastAPI(
    title="Task Manager API",
    description="Minimalist task manager with priorities and energy levels",
    version="1.0.0"
)

# CORS settings for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info(f"Task Manager API started. Logging to: {log_path}")

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
        tasks = db.query(Task).filter(Task.status == status_filter).offset(skip).limit(limit).all()
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

@app.post("/api/tasks/roll", dependencies=[Depends(verify_api_key)])
async def roll_tasks(mood: Optional[str] = None, db: Session = Depends(get_db)):
    """Generate daily task plan"""
    result = crud.roll_tasks(db, mood)
    return {
        "message": "Daily plan generated",
        "habits_count": len(result["habits"]),
        "tasks_count": len(result["tasks"]),
        "deleted_habits": result["deleted_habits"],
        "habits": result["habits"],
        "tasks": result["tasks"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
