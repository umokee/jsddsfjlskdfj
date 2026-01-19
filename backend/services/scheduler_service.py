"""
Background scheduler for automatic task management
Handles:
- Automatic penalties at midnight
- Automatic roll at configured time
- Automatic database backups
- Resetting last_roll_date for new day
"""

import logging
from datetime import datetime, date, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
from backend.infrastructure.database import SessionLocal
from backend.models import Backup
import backend.crud as crud
from backend.services import backup_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("task_manager.scheduler")

# Statistics tracking
scheduler_stats = {
    'started_at': None,
    'jobs': {
        'check_auto_roll': {
            'checks': 0,
            'executions': 0,
            'last_check': None,
            'last_execution': None,
            'last_error': None
        },
        'check_auto_penalties': {
            'checks': 0,
            'executions': 0,
            'last_check': None,
            'last_execution': None,
            'last_error': None
        },
        'check_auto_backup': {
            'checks': 0,
            'executions': 0,
            'last_check': None,
            'last_execution': None,
            'last_error': None
        }
    }
}


def check_auto_roll():
    """Check if automatic roll should be executed (uses effective date for shifted schedules)"""
    db: Session = SessionLocal()
    stats = scheduler_stats['jobs']['check_auto_roll']
    stats['checks'] += 1
    stats['last_check'] = datetime.now()

    try:
        settings = crud.get_settings(db)

        # Only proceed if auto_roll is enabled
        if not settings.auto_roll_enabled:
            return

        now_utc = datetime.now()
        now_local = now_utc.astimezone()  # Convert to local timezone for time comparison
        today = crud.get_effective_date(settings)
        current_time = now_local.strftime("%H:%M")
        auto_roll_time = settings.auto_roll_time or "06:00"

        # Check if we haven't rolled today and it's time for auto-roll
        # If day_start is enabled, the effective date change handles the timing
        should_check_time = not settings.day_start_enabled
        if settings.last_roll_date != today and (not should_check_time or current_time >= auto_roll_time):
            logger.info(f"Executing automatic roll at {current_time}")
            result = crud.roll_tasks(db)

            if "error" not in result:
                stats['executions'] += 1
                stats['last_execution'] = datetime.now()
                logger.info(f"Auto-roll successful: {len(result['tasks'])} tasks, {len(result['habits'])} habits")
            else:
                logger.warning(f"Auto-roll failed: {result['error']}")
                stats['last_error'] = str(result['error'])

    except Exception as e:
        logger.error(f"Error in check_auto_roll: {e}")
        stats['last_error'] = str(e)
    finally:
        db.close()


def check_auto_penalties():
    """Check if automatic penalties should be applied"""
    db: Session = SessionLocal()
    stats = scheduler_stats['jobs']['check_auto_penalties']
    stats['checks'] += 1
    stats['last_check'] = datetime.now()

    try:
        settings = crud.get_settings(db)

        # Only proceed if auto_penalties is enabled
        if not settings.auto_penalties_enabled:
            return

        now_utc = datetime.now()
        now_local = now_utc.astimezone()  # Convert to local timezone for time comparison
        current_time = now_local.strftime("%H:%M")
        penalty_time = settings.penalty_time or "00:01"

        # Check if it's time for penalties (check for exact minute match)
        if current_time != penalty_time:
            return

        logger.info(f"Applying penalties for yesterday at {current_time}")

        # Apply penalties for yesterday
        penalty_info = crud.calculate_daily_penalties(db)

        stats['executions'] += 1
        stats['last_execution'] = datetime.now()
        logger.info(f"Penalties applied: {penalty_info.get('penalty', 0)} points")

    except Exception as e:
        logger.error(f"Error in check_auto_penalties: {e}")
        stats['last_error'] = str(e)
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
    stats = scheduler_stats['jobs']['check_auto_backup']
    stats['checks'] += 1
    stats['last_check'] = datetime.now()

    try:
        settings = crud.get_settings(db)

        # Only proceed if auto_backup is enabled
        if not settings.auto_backup_enabled:
            return

        now_utc = datetime.now()
        now_local = now_utc.astimezone()  # Convert to local timezone for time comparison
        current_time = now_local.strftime("%H:%M")
        backup_time = settings.backup_time or "03:00"

        # Check if it's time for backup (check for exact minute match)
        if current_time != backup_time:
            return

        # Check if we need to backup based on interval
        # Only check LAST AUTO backup, not manual backups
        last_auto_backup = db.query(Backup).filter(
            Backup.backup_type == "auto"
        ).order_by(Backup.created_at.desc()).first()

        if last_auto_backup:
            days_since_backup = (now_utc - last_auto_backup.created_at).days
            if days_since_backup < settings.backup_interval_days:
                logger.info(f"Auto backup not needed yet (last auto backup: {days_since_backup} days ago)")
                return

        logger.info(f"Executing automatic backup at {current_time}")

        # Create backup
        backup = backup_service.create_local_backup(db, backup_type="auto")

        if backup:
            stats['executions'] += 1
            stats['last_execution'] = datetime.now()
            logger.info(f"Auto-backup successful: {backup.filename}")

            # Upload to Google Drive if enabled
            if settings.google_drive_enabled:
                try:
                    backup_service.upload_to_google_drive(backup)
                    logger.info(f"Auto-backup uploaded to Google Drive")
                except Exception as e:
                    logger.error(f"Google Drive upload failed: {e}")
                    stats['last_error'] = f"Google Drive upload: {str(e)}"
        else:
            logger.error("Auto-backup failed")
            stats['last_error'] = "Backup creation failed"

    except Exception as e:
        logger.error(f"Error in check_auto_backup: {e}")
        stats['last_error'] = str(e)
    finally:
        db.close()


# Create scheduler instance
scheduler = BackgroundScheduler()


def start_scheduler():
    """Start the background scheduler"""
    print(">>> SCHEDULER: Starting Task Manager background scheduler")  # Direct print for debugging
    logger.info("Starting Task Manager background scheduler")

    # Record start time
    scheduler_stats['started_at'] = datetime.now()

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
    logger.info("Background scheduler started successfully")
    logger.info(f"Scheduled jobs: {[job.id for job in scheduler.get_jobs()]}")


def stop_scheduler():
    """Stop the background scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Background scheduler stopped")


def get_scheduler_status():
    """Get detailed scheduler status and statistics"""
    now = datetime.now()

    # Get current settings
    db: Session = SessionLocal()
    try:
        settings = crud.get_settings(db)
    finally:
        db.close()

    # Calculate uptime
    uptime_seconds = None
    if scheduler_stats['started_at']:
        uptime_seconds = (now - scheduler_stats['started_at']).total_seconds()

    # Get jobs info
    jobs_info = []
    for job in scheduler.get_jobs():
        job_stats = scheduler_stats['jobs'].get(job.id, {})

        # Get next run time
        next_run_time = job.next_run_time
        seconds_until_next = None
        if next_run_time:
            seconds_until_next = (next_run_time - now).total_seconds()

        last_check = job_stats.get('last_check')
        last_execution = job_stats.get('last_execution')

        jobs_info.append({
            'id': job.id,
            'name': job.name or job.id,
            'next_run_time': next_run_time.isoformat() if next_run_time else None,
            'seconds_until_next': int(seconds_until_next) if seconds_until_next else None,
            'checks': job_stats.get('checks', 0),
            'executions': job_stats.get('executions', 0),
            'last_check': last_check.isoformat() if last_check else None,
            'last_execution': last_execution.isoformat() if last_execution else None,
            'last_error': job_stats.get('last_error'),
        })

    return {
        'running': scheduler.running,
        'started_at': scheduler_stats['started_at'].isoformat() if scheduler_stats['started_at'] else None,
        'uptime_seconds': int(uptime_seconds) if uptime_seconds else None,
        'uptime_human': _format_uptime(uptime_seconds) if uptime_seconds else None,
        'current_time': now.isoformat(),
        'jobs': jobs_info,
        'settings': {
            'auto_roll_enabled': settings.auto_roll_enabled,
            'auto_roll_time': settings.auto_roll_time,
            'auto_penalties_enabled': settings.auto_penalties_enabled,
            'penalty_time': settings.penalty_time,
            'auto_backup_enabled': settings.auto_backup_enabled,
            'backup_time': settings.backup_time,
            'backup_interval_days': settings.backup_interval_days,
        }
    }


def _format_uptime(seconds):
    """Format uptime in human-readable format"""
    if not seconds:
        return "0s"

    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)
