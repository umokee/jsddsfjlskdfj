"""
Task Manager API - Modular Monolith Architecture.

This is the main entry point that assembles all modules and starts the application.
"""

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.database import engine, Base
from backend.core.migrations import auto_migrate
from backend.scheduler import start_scheduler, stop_scheduler

# Import all models to register them with Base
from backend.modules.settings.models import Settings
from backend.modules.tasks.models import Task
from backend.modules.points.models import PointHistory
from backend.modules.goals.models import PointGoal
from backend.modules.rest_days.models import RestDay
from backend.modules.backups.models import Backup

# Import routes
from backend.modules.settings.routes import router as settings_router
from backend.modules.tasks.routes import router as tasks_router
from backend.modules.points.routes import router as points_router
from backend.modules.goals.routes import router as goals_router
from backend.modules.rest_days.routes import router as rest_days_router
from backend.modules.backups.routes import router as backups_router

# Configure logging
from backend.shared.constants import DEFAULT_LOG_DIRECTORY_PROD, DEFAULT_LOG_DIRECTORY_DEV

LOG_DIR = os.getenv("TASK_MANAGER_LOG_DIR", DEFAULT_LOG_DIRECTORY_PROD)
LOG_FILE = os.getenv("TASK_MANAGER_LOG_FILE", "app.log")

try:
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    log_path = Path(LOG_DIR) / LOG_FILE
except PermissionError:
    LOG_DIR = DEFAULT_LOG_DIRECTORY_DEV
    Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
    log_path = Path(LOG_DIR) / LOG_FILE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_path),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("task_manager")

# Create database tables
Base.metadata.create_all(bind=engine)

# Run automatic schema migrations
try:
    auto_migrate()
except Exception as e:
    logger.error(f"Auto-migration failed: {e}")

# Create FastAPI application
app = FastAPI(
    title="Task Manager API",
    description="Minimalist task manager with gamification - Modular Monolith Architecture",
    version="2.0.0"
)

# CORS settings
from backend.shared.constants import CORS_ALLOWED_ORIGINS

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
    start_scheduler()


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Task Manager API")
    stop_scheduler()


# Health check (no auth required)
@app.get("/")
async def root():
    return {"message": "Task Manager API", "status": "active", "version": "2.0.0"}


# Include routers
app.include_router(settings_router)
app.include_router(tasks_router)
app.include_router(points_router)
app.include_router(goals_router)
app.include_router(rest_days_router)
app.include_router(backups_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
