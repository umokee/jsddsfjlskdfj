"""
Background scheduler for automatic task management
Handles:
- Automatic penalties at midnight
- Automatic roll at configured time
- Automatic database backups
- Resetting last_roll_date for new day
"""

import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.infrastructure.database import SessionLocal
from backend.models import Backup
import backend.crud as crud
from backend.services import backup_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("task_manager.scheduler")

# Create scheduler instance
scheduler = AsyncIOScheduler()


def _normalize_time(time_str: str | None) -> str:
    """
    Приводит время к формату HHMM.
    Примеры: '06:00' -> '0600', '0600' -> '0600', None -> '0000'
    """
    if not time_str:
        return "0000"
    return time_str.replace(":", "")


async def run_auto_roll():
    """Задача: Автоматический перенос задач (Roll)"""
    db = SessionLocal()
    try:
        settings = crud.get_settings(db)
        if not settings.auto_roll_enabled:
            return

        # Получаем текущее время в формате HHMM
        current_time = datetime.now().strftime("%H%M")
        target_time = _normalize_time(settings.auto_roll_time or "0600")
        
        # Проверяем эффективную дату
        today = crud.get_effective_date(settings)
        
        # Запускаем roll, если:
        # 1. Время уже наступило (или прошло)
        # 2. Сегодня еще не роллили
        if int(current_time) >= int(target_time) and settings.last_roll_date != today:
            logger.info(f"Executing Auto-Roll (Current: {current_time}, Target: {target_time})")
            result = crud.roll_tasks(db)
            
            if "error" not in result:
                logger.info(f"Auto-roll successful: {len(result.get('tasks', []))} tasks, {len(result.get('habits', []))} habits")
            else:
                logger.warning(f"Auto-roll failed: {result['error']}")
        
    except Exception as e:
        logger.error(f"Scheduler Error (Auto-Roll): {e}")
    finally:
        db.close()


async def run_auto_penalties():
    """Задача: Начисление штрафов"""
    db = SessionLocal()
    try:
        settings = crud.get_settings(db)
        if not settings.auto_penalties_enabled:
            return

        current_time = datetime.now().strftime("%H%M")
        target_time = _normalize_time(settings.penalty_time or "0001")

        # Получаем эффективную дату
        today = crud.get_effective_date(settings)
        yesterday = today - timedelta(days=1)

        # Выполняем штрафы если время уже наступило и еще не применяли
        if int(current_time) >= int(target_time):
            # Проверяем, не применяли ли уже штрафы за вчера
            # Штрафы применяются за вчерашний день
            from backend.models import PointHistory
            yesterday_history = db.query(PointHistory).filter(
                PointHistory.date == yesterday
            ).first()

            # Если истории за вчера нет, или пенальти уже установлены - пропускаем
            if not yesterday_history:
                logger.info(f"No history for {yesterday}, skipping penalties")
                return

            # Проверяем флаг финализации через completion_rate
            # Если completion_rate уже рассчитан, значит день финализирован
            if yesterday_history.completion_rate > 0 or yesterday_history.points_penalty > 0:
                logger.info(f"Penalties already applied for {yesterday}")
                return

            logger.info(f"Applying penalties at {current_time} for {yesterday}")
            penalty_info = crud.calculate_daily_penalties(db)
            logger.info(f"Penalties applied: {penalty_info.get('penalty', 0)} points")

    except Exception as e:
        logger.error(f"Scheduler Error (Penalties): {e}")
    finally:
        db.close()


async def run_auto_backup():
    """Задача: Автоматический бэкап"""
    db = SessionLocal()
    try:
        settings = crud.get_settings(db)
        logger.info(f"[AUTO_BACKUP] Checking... enabled={settings.auto_backup_enabled}")

        if not settings.auto_backup_enabled:
            logger.info(f"[AUTO_BACKUP] Disabled, skipping")
            return

        current_time = datetime.now().strftime("%H%M")
        target_time = _normalize_time(settings.backup_time or "0300")
        logger.info(f"[AUTO_BACKUP] Time check: current={current_time}, target={target_time}")

        # Выполняем бэкап если время уже наступило (или прошло)
        if int(current_time) >= int(target_time):
            # Проверяем, не делали ли уже бэкап сегодня
            today = datetime.now().date()
            last_auto_backup = db.query(Backup).filter(
                Backup.backup_type == "auto"
            ).order_by(Backup.created_at.desc()).first()

            if last_auto_backup:
                last_backup_date = last_auto_backup.created_at.date()
                logger.info(f"[AUTO_BACKUP] Last backup: {last_backup_date}, today: {today}")

                # Если уже делали бэкап сегодня, пропускаем
                if last_backup_date == today:
                    logger.info(f"[AUTO_BACKUP] Already done today, skipping")
                    return

                # Проверяем интервал в днях
                days_since = (today - last_backup_date).days
                logger.info(f"[AUTO_BACKUP] Days since last: {days_since}, interval: {settings.backup_interval_days}")

                if days_since < settings.backup_interval_days:
                    logger.info(f"[AUTO_BACKUP] Skipped - interval not reached (last was {days_since} days ago, need {settings.backup_interval_days})")
                    return
            else:
                logger.info(f"[AUTO_BACKUP] No previous backups found, creating first one")

            logger.info(f"[AUTO_BACKUP] Creating backup at {current_time}")
            backup = backup_service.create_local_backup(db, backup_type="auto")

            if backup:
                logger.info(f"Auto-backup successful: {backup.filename}")

                # Загрузка в Google Drive (если включено)
                if settings.google_drive_enabled:
                    try:
                        backup_service.upload_to_google_drive(backup)
                        logger.info("Auto-backup uploaded to Google Drive")
                    except Exception as e:
                        logger.error(f"Google Drive upload failed: {e}")
            else:
                logger.error("Auto-backup failed")

    except Exception as e:
        logger.error(f"Scheduler Error (Backup): {e}")
    finally:
        db.close()


def start_scheduler():
    """Запуск планировщика"""
    if not scheduler.running:
        # Создаём задачи, которые проверяются каждую минуту
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
    """Остановка планировщика"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler stopped")