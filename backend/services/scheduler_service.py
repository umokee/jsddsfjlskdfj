"""
Background scheduler for automatic task management
Handles:
- Automatic penalties at midnight
- Automatic roll at configured time
- Automatic database backups
- Resetting last_roll_date for new day
"""

import logging
import asyncio
from datetime import datetime
from rocketry import Rocketry
from rocketry.conds import every
from sqlalchemy.orm import Session
from backend.infrastructure.database import SessionLocal
from backend.models import Backup
import backend.crud as crud
from backend.services import backup_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("task_manager.scheduler")

# Create Rocketry app with async execution
app = Rocketry(config={"task_execution": "async"})

# --- Helper Functions ---

def get_settings_sync():
    """Get settings from DB in a fresh session"""
    db = SessionLocal()
    try:
        return crud.get_settings(db)
    finally:
        db.close()

# --- Conditions ---
# These run every cycle (default is often) to check if a task should start

@app.cond()
def is_roll_time():
    """Check if it matches the configured roll time"""
    settings = get_settings_sync()
    if not settings.auto_roll_enabled:
        return False
    
    current_time = datetime.now().strftime("%H:%M")
    target_time = settings.auto_roll_time or "06:00"
    return current_time == target_time

@app.cond()
def is_penalty_time():
    """Check if it matches the configured penalty time"""
    settings = get_settings_sync()
    if not settings.auto_penalties_enabled:
        return False
        
    current_time = datetime.now().strftime("%H:%M")
    target_time = settings.penalty_time or "00:01"
    return current_time == target_time

@app.cond()
def is_backup_time():
    """Check if it matches the configured backup time"""
    settings = get_settings_sync()
    if not settings.auto_backup_enabled:
        return False
        
    current_time = datetime.now().strftime("%H:%M")
    target_time = settings.backup_time or "03:00"
    return current_time == target_time

# --- Tasks ---

@app.task(every("1 minute") & is_roll_time)
async def task_auto_roll():
    """Execute auto-roll"""
    logger.info("Starting auto-roll task...")
    
    # Run synchronous DB operations in a thread executor
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _run_sync_roll)

def _run_sync_roll():
    db = SessionLocal()
    try:
        settings = crud.get_settings(db)
        today = crud.get_effective_date(settings)
        
        # Double-check logic from original service
        if settings.last_roll_date != today:
             logger.info(f"Executing automatic roll")
             result = crud.roll_tasks(db)
             if "error" not in result:
                 logger.info(f"Auto-roll successful: {len(result.get('tasks', []))} tasks")
             else:
                 logger.warning(f"Auto-roll failed: {result['error']}")
        else:
            logger.info("Auto-roll already done for today")
    except Exception as e:
        logger.error(f"Error in auto-roll: {e}")
    finally:
        db.close()

@app.task(every("1 minute") & is_penalty_time)
async def task_auto_penalties():
    """Execute auto-penalties"""
    logger.info("Starting auto-penalties task...")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _run_sync_penalties)

def _run_sync_penalties():
    db = SessionLocal()
    try:
        penalty_info = crud.calculate_daily_penalties(db)
        logger.info(f"Penalties applied: {penalty_info.get('penalty', 0)} points")
    except Exception as e:
        logger.error(f"Error in auto-penalties: {e}")
    finally:
        db.close()

@app.task(every("1 minute") & is_backup_time)
async def task_auto_backup():
    """Execute auto-backup"""
    logger.info("Starting auto-backup task...")
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _run_sync_backup)

def _run_sync_backup():
    db = SessionLocal()
    try:
        settings = crud.get_settings(db)
        
        # Check interval logic
        last_auto_backup = db.query(Backup).filter(
            Backup.backup_type == "auto"
        ).order_by(Backup.created_at.desc()).first()
        
        should_run = True
        if last_auto_backup:
            days_since = (datetime.now() - last_auto_backup.created_at).days
            if days_since < settings.backup_interval_days:
                should_run = False
                logger.info(f"Auto backup skipped (last was {days_since} days ago)")
        
        if should_run:
            backup = backup_service.create_local_backup(db, backup_type="auto")
            if backup:
                logger.info(f"Auto-backup successful: {backup.filename}")
                if settings.google_drive_enabled:
                    try:
                        backup_service.upload_to_google_drive(backup)
                        logger.info("Auto-backup uploaded to Google Drive")
                    except Exception as e:
                        logger.error(f"GDrive upload failed: {e}")
    except Exception as e:
        logger.error(f"Error in auto-backup: {e}")
    finally:
        db.close()

# Export 'app' so main.py can import it
scheduler_app = app
