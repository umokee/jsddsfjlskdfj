"""
Background scheduler jobs.

Handles:
- Automatic penalties at midnight
- Automatic roll at configured time
- Automatic database backups
- Auto-completing roll after timeout
"""

import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from backend.core.database import SessionLocal
from backend.modules.settings import SettingsService
from backend.modules.backups import BackupService
from backend.modules.penalties import PenaltyService
from backend.modules.rest_days import RestDayService
from backend.modules.tasks import TaskService
from backend.modules.points import PointsService
from backend.workflows import RollDayWorkflow, CreateBackupWorkflow
from backend.shared.date_utils import get_effective_date

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("task_manager.scheduler")

scheduler = AsyncIOScheduler()


def _normalize_time(time_str: str | None) -> str:
    """Convert time string to HHMM format."""
    if not time_str:
        return "0000"
    return time_str.replace(":", "")


async def run_auto_roll():
    """
    Automatic daily preparation task.

    Morning Check-in Mode:
    - Applies penalties for yesterday
    - Sets pending_roll = True
    - Actual roll happens after user selects mood
    - If user doesn't select mood within timeout, auto-roll with max energy
    """
    db = SessionLocal()
    try:
        settings_service = SettingsService(db)
        settings = settings_service.get_data()

        if not settings.auto_roll_enabled:
            return

        now = datetime.now()
        current_time = now.strftime("%H%M")
        target_time = _normalize_time(settings.auto_roll_time or "0600")
        today = get_effective_date(settings.day_start_enabled, settings.day_start_time)

        # Safety: if pending_roll is stuck (roll already done today), clear it
        if settings.pending_roll and settings.last_roll_date == today:
            logger.info("Clearing stuck pending_roll flag (roll already done today)")
            settings_service.clear_pending_roll()
            return

        # Check if timeout reached for pending_roll
        if settings.pending_roll and settings.pending_roll_started_at:
            timeout_hours = settings.auto_mood_timeout_hours or 4
            timeout_delta = timedelta(hours=timeout_hours)

            if now - settings.pending_roll_started_at >= timeout_delta:
                logger.info(f"Auto-roll timeout ({timeout_hours}h) reached - completing with max energy")

                workflow = RollDayWorkflow(db)
                result = workflow.execute(mood="5")

                # Always clear pending_roll after timeout attempt
                settings_service.clear_pending_roll()

                if "error" not in result:
                    logger.info(f"Auto-roll completed: {len(result.get('tasks', []))} tasks")
                else:
                    logger.error(f"Auto-roll failed: {result.get('error')}")
                return

        # Start morning preparation if time reached and not already pending
        if (int(current_time) >= int(target_time) and
            not settings.pending_roll and
            settings.last_roll_date != today):

            logger.info(f"Starting morning preparation (Current: {current_time}, Target: {target_time})")

            # Calculate penalties for yesterday
            penalty_service = PenaltyService(db)
            rest_day_service = RestDayService(db)
            points_service = PointsService(db)
            task_service = TaskService(db)

            penalty_info = penalty_service.calculate_daily_penalties(
                effective_today=today,
                is_rest_day_fn=rest_day_service.is_rest_day,
                settings=settings,
                get_yesterday_history=lambda d: points_service.get_history_for_date(d),
                get_yesterday_completed_tasks=lambda s, e: task_service._get_completed_in_range(s, e),
                get_yesterday_completed_habits=lambda s, e: task_service._get_completed_habits_in_range(s, e),
                get_missed_habits_fn=lambda s, e: task_service.get_missed_habits(s, e),
                count_habits_due_fn=lambda s, e: task_service.count_habits_due(s, e),
                roll_forward_habit_fn=lambda h, d: task_service.roll_forward_missed_habit(h, d),
            )
            logger.info(f"Penalties applied: {penalty_info.get('penalty', 0)} points")

            # Set pending_roll flag
            settings_service.set_pending_roll(True, datetime.now())
            logger.info(f"Waiting for user mood selection (timeout: {settings.auto_mood_timeout_hours}h)")

    except Exception as e:
        logger.error(f"Scheduler Error (Auto-Roll): {e}")
    finally:
        db.close()


async def run_auto_penalties():
    """Apply penalties at configured time."""
    db = SessionLocal()
    try:
        settings_service = SettingsService(db)
        settings = settings_service.get_data()

        if not settings.auto_penalties_enabled:
            return

        current_time = datetime.now().strftime("%H%M")
        target_time = _normalize_time(settings.penalty_time or "0001")
        today = get_effective_date(settings.day_start_enabled, settings.day_start_time)
        yesterday = today - timedelta(days=1)

        if int(current_time) >= int(target_time):
            points_service = PointsService(db)
            yesterday_history = points_service.get_history_for_date(yesterday)

            if not yesterday_history:
                logger.info(f"No history for {yesterday}, skipping penalties")
                return

            # Check if already finalized
            if yesterday_history.completion_rate > 0 or yesterday_history.points_penalty > 0:
                logger.info(f"Penalties already applied for {yesterday}")
                return

            logger.info(f"Applying penalties for {yesterday}")

            penalty_service = PenaltyService(db)
            rest_day_service = RestDayService(db)
            task_service = TaskService(db)

            penalty_info = penalty_service.calculate_daily_penalties(
                effective_today=today,
                is_rest_day_fn=rest_day_service.is_rest_day,
                settings=settings,
                get_yesterday_history=lambda d: points_service.get_history_for_date(d),
                get_yesterday_completed_tasks=lambda s, e: task_service._get_completed_in_range(s, e),
                get_yesterday_completed_habits=lambda s, e: task_service._get_completed_habits_in_range(s, e),
                get_missed_habits_fn=lambda s, e: task_service.get_missed_habits(s, e),
                count_habits_due_fn=lambda s, e: task_service.count_habits_due(s, e),
                roll_forward_habit_fn=lambda h, d: task_service.roll_forward_missed_habit(h, d),
            )
            logger.info(f"Penalties applied: {penalty_info.get('penalty', 0)} points")

    except Exception as e:
        logger.error(f"Scheduler Error (Penalties): {e}")
    finally:
        db.close()


async def run_auto_backup():
    """Create automatic backup at configured time."""
    db = SessionLocal()
    try:
        settings_service = SettingsService(db)
        settings = settings_service.get_data()

        logger.info(f"[AUTO_BACKUP] Checking... enabled={settings.auto_backup_enabled}")

        if not settings.auto_backup_enabled:
            logger.info("[AUTO_BACKUP] Disabled, skipping")
            return

        current_time = datetime.now().strftime("%H%M")
        target_time = _normalize_time(settings.backup_time or "0300")
        today = get_effective_date(settings.day_start_enabled, settings.day_start_time)

        logger.info(f"[AUTO_BACKUP] Time check: current={current_time}, target={target_time}")

        if int(current_time) >= int(target_time):
            backup_service = BackupService(db)
            last_auto = backup_service.get_last_auto_backup()

            if last_auto:
                last_backup_date = last_auto.created_at.date()
                logger.info(f"[AUTO_BACKUP] Last: {last_backup_date}, today: {today}")

                if last_backup_date == today:
                    logger.info("[AUTO_BACKUP] Already done today")
                    return

                days_since = (today - last_backup_date).days
                if days_since < settings.backup_interval_days:
                    logger.info(f"[AUTO_BACKUP] Interval not reached ({days_since}/{settings.backup_interval_days} days)")
                    return

            logger.info(f"[AUTO_BACKUP] Creating backup")

            workflow = CreateBackupWorkflow(db)
            backup = workflow.execute(backup_type="auto")

            if backup:
                logger.info(f"Auto-backup successful: {backup.filename}")
            else:
                logger.error("Auto-backup failed")

    except Exception as e:
        logger.error(f"Scheduler Error (Backup): {e}")
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler."""
    if not scheduler.running:
        trigger = CronTrigger(minute='*')

        scheduler.add_job(
            run_auto_roll,
            trigger,
            id='auto_roll',
            replace_existing=True
        )

        scheduler.add_job(
            run_auto_penalties,
            trigger,
            id='auto_penalties',
            replace_existing=True
        )

        scheduler.add_job(
            run_auto_backup,
            trigger,
            id='auto_backup',
            replace_existing=True
        )

        scheduler.start()
        logger.info(">>> APScheduler STARTED <<<")
        logger.info(f"Scheduled jobs: {[job.id for job in scheduler.get_jobs()]}")


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler stopped")
