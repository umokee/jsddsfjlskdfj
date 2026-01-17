"""
Background scheduler for automatic task management
Handles:
- Automatic penalties at midnight
- Automatic roll at configured time
- Automatic database backups
- Resetting last_roll_date for new day
"""

import logging
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import Backup
import backend.crud as crud
import backend.backup_service as backup_service

# Get logger (configuration is done in main.py)
logger = logging.getLogger("task_manager.scheduler")


def check_auto_roll():
    """Check if automatic roll should be executed (uses effective date for shifted schedules)"""
    db: Session = SessionLocal()
    try:
        settings = crud.get_settings(db)

        # Only proceed if auto_roll is enabled
        if not settings.auto_roll_enabled:
            return

        now = datetime.now()
        today = crud.get_effective_date(settings)
        current_time = now.strftime("%H:%M")
        auto_roll_time = settings.auto_roll_time or "06:00"

        # Check if we haven't rolled today and it's time for auto-roll
        # If day_start is enabled, the effective date change handles the timing
        should_check_time = not settings.day_start_enabled
        if settings.last_roll_date != today and (not should_check_time or current_time >= auto_roll_time):
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


def check_auto_penalties():
    """Check if automatic penalties should be applied"""
    db: Session = SessionLocal()
    try:
        settings = crud.get_settings(db)

        # Only proceed if auto_penalties is enabled
        if not settings.auto_penalties_enabled:
            return

        now = datetime.now()
        current_time = now.strftime("%H:%M")
        penalty_time = settings.penalty_time or "00:01"

        # Check if it's time for penalties
        if current_time != penalty_time:
            return

        logger.info(f"Applying penalties for yesterday at {current_time}")

        # Apply penalties for yesterday
        penalty_info = crud.calculate_daily_penalties(db)

        logger.info(f"Penalties applied: {penalty_info.get('penalty', 0)} points")

    except Exception as e:
        logger.error(f"Error in check_auto_penalties: {e}")
    finally:
        db.close()


def reset_roll_availability():
    """Reset roll availability at configured time (uses effective date for shifted schedules)"""
    db: Session = SessionLocal()
    try:
        settings = crud.get_settings(db)
        today = crud.get_effective_date(settings)

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


def check_auto_backup():
    """Check if automatic backup should be executed"""
    db: Session = SessionLocal()
    try:
        settings = crud.get_settings(db)

        # Only proceed if auto_backup is enabled
        if not settings.auto_backup_enabled:
            logger.info("❌ Auto backup is DISABLED in settings")
            return

        now = datetime.now()
        current_time = now.strftime("%H:%M")
        backup_time = settings.backup_time or "03:00"

        # ALWAYS log at INFO level for debugging
        logger.info(f"🔍 Auto backup check: enabled={settings.auto_backup_enabled}, current={current_time}, target={backup_time}, interval={settings.backup_interval_days}d")

        # Check if it's time for backup
        if current_time != backup_time:
            logger.info(f"⏳ Waiting for backup time (current={current_time}, need={backup_time})")
            return

        logger.info(f"⏰ BACKUP TIME MATCHED! current={current_time}, target={backup_time}")

        # Check if we need to backup based on interval
        # Only check LAST AUTO backup, not manual backups
        last_auto_backup = db.query(Backup).filter(
            Backup.backup_type == "auto"
        ).order_by(Backup.created_at.desc()).first()

        if last_auto_backup:
            time_since_backup = now - last_auto_backup.created_at
            days_since = time_since_backup.days
            hours_since = time_since_backup.total_seconds() / 3600

            logger.info(f"📊 Last auto backup: {last_auto_backup.created_at}")
            logger.info(f"📊 Time since: {days_since} days ({hours_since:.1f} hours)")
            logger.info(f"📊 Interval required: {settings.backup_interval_days} days")

            if days_since < settings.backup_interval_days:
                logger.info(f"⏸️  SKIPPING: Last auto backup was {days_since} days ago ({hours_since:.1f}h), need {settings.backup_interval_days} days interval")
                return
            else:
                logger.info(f"✅ Interval passed: {days_since} days >= {settings.backup_interval_days} days required")
        else:
            logger.info("✨ No previous auto backup found, will create first backup")

        logger.info(f"🔄 Executing automatic backup at {current_time}")

        # Create backup
        backup = backup_service.create_local_backup(db, backup_type="auto")

        if backup:
            logger.info(f"Auto-backup successful: {backup.filename}")

            # Upload to Google Drive if enabled
            if settings.google_drive_enabled:
                try:
                    backup_service.upload_to_google_drive(backup)
                    logger.info(f"Auto-backup uploaded to Google Drive")
                except Exception as e:
                    logger.error(f"Google Drive upload failed: {e}")
        else:
            logger.error("Auto-backup failed")

    except Exception as e:
        logger.error(f"Error in check_auto_backup: {e}")
    finally:
        db.close()


# Create scheduler instance
scheduler = BackgroundScheduler()


def start_scheduler():
    """Start the background scheduler"""
    print(">>> SCHEDULER: Starting Task Manager background scheduler")  # Direct print for debugging
    logger.info("Starting Task Manager background scheduler")

    # Check for auto-roll every minute
    # (the function itself checks if it's time to roll)
    scheduler.add_job(
        check_auto_roll,
        CronTrigger(minute='*'),  # Every minute
        id='check_auto_roll',
        replace_existing=True
    )

    # Check for auto-penalties every minute
    # (the function itself checks if it's time to apply penalties)
    scheduler.add_job(
        check_auto_penalties,
        CronTrigger(minute='*'),  # Every minute
        id='check_auto_penalties',
        replace_existing=True
    )

    # Check for auto-backup every minute
    # (the function itself checks if it's time to backup)
    scheduler.add_job(
        check_auto_backup,
        CronTrigger(minute='*'),  # Every minute
        id='check_auto_backup',
        replace_existing=True
    )

    # Start the scheduler
    scheduler.start()
    logger.info("=" * 50)
    logger.info("Background scheduler started successfully")
    logger.info(f"Scheduled jobs: {[job.id for job in scheduler.get_jobs()]}")
    logger.info("Auto backup job will run every minute")
    logger.info("=" * 50)


def stop_scheduler():
    """Stop the background scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")
