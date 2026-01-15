"""
Background scheduler for automatic task management
Handles:
- Automatic penalties at midnight
- Automatic roll at configured time
- Resetting last_roll_date for new day
"""

import logging
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from backend.models import SessionLocal
import backend.crud as crud

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("task_manager.scheduler")


def check_auto_roll():
    """Check if automatic roll should be executed"""
    db: Session = SessionLocal()
    try:
        settings = crud.get_settings(db)

        # Only proceed if auto_roll is enabled
        if not settings.auto_roll_enabled:
            return

        now = datetime.utcnow()
        today = now.date()
        current_time = now.strftime("%H:%M")
        auto_roll_time = settings.auto_roll_time or "06:00"

        # Check if we haven't rolled today and it's time for auto-roll
        if settings.last_roll_date != today and current_time >= auto_roll_time:
            logger.info(f"Executing automatic roll at {current_time}")
            result = crud.roll_tasks(db)

            if "error" not in result:
                logger.info(f"Auto-roll successful: {len(result['tasks'])} tasks, {len(result['habits'])} habits")
            else:
                logger.warning(f"Auto-roll failed: {result['error']}")

    except Exception as e:
        logger.error(f"Error in check_auto_roll: {e}")
    finally:
        db.close()


def apply_midnight_penalties():
    """Apply penalties for yesterday at midnight"""
    db: Session = SessionLocal()
    try:
        settings = crud.get_settings(db)

        # Only proceed if auto_penalties is enabled
        if not settings.auto_penalties_enabled:
            logger.info("Auto penalties disabled, skipping")
            return

        logger.info("Applying midnight penalties for yesterday")

        # This will be called daily, so apply penalties for yesterday
        penalty_info = crud.calculate_daily_penalties(db)

        logger.info(f"Midnight penalties applied: {penalty_info.get('penalty', 0)} points")

    except Exception as e:
        logger.error(f"Error in apply_midnight_penalties: {e}")
    finally:
        db.close()


def reset_roll_availability():
    """Reset roll availability at configured time"""
    db: Session = SessionLocal()
    try:
        settings = crud.get_settings(db)
        today = date.today()

        # If last_roll_date is not today, it's already reset
        # This function ensures the reset happens at the configured time
        if settings.last_roll_date == today:
            logger.info(f"Roll availability already set for today")
        else:
            logger.info(f"Roll is available for {today}")

    except Exception as e:
        logger.error(f"Error in reset_roll_availability: {e}")
    finally:
        db.close()


# Create scheduler instance
scheduler = BackgroundScheduler()


def start_scheduler():
    """Start the background scheduler"""
    logger.info("Starting Task Manager background scheduler")

    # Check for auto-roll every minute
    # (the function itself checks if it's time to roll)
    scheduler.add_job(
        check_auto_roll,
        CronTrigger(minute='*'),  # Every minute
        id='check_auto_roll',
        replace_existing=True
    )

    # Apply penalties at midnight (00:01 to ensure it's a new day)
    scheduler.add_job(
        apply_midnight_penalties,
        CronTrigger(hour=0, minute=1),
        id='midnight_penalties',
        replace_existing=True
    )

    # Start the scheduler
    scheduler.start()
    logger.info("Background scheduler started successfully")


def stop_scheduler():
    """Stop the background scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
