"""
Backup service for database with Google Drive integration.
Handles local backups and optional cloud upload.
"""
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models import Backup, Settings
from backend.database import SessionLocal

logger = logging.getLogger("task_manager.backup")

# Backup directory
BACKUP_DIR = os.getenv("TASK_MANAGER_BACKUP_DIR", "/var/lib/task-manager/backups")
DB_DIR = os.getenv("TASK_MANAGER_DB_DIR", "/var/lib/task-manager")
DB_FILE = "tasks.db"

# Try to create backup directory
try:
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
except PermissionError:
    # Fallback to local directory
    BACKUP_DIR = "./backups"
    Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)

# Database path
try:
    DB_PATH = Path(DB_DIR) / DB_FILE
    if not DB_PATH.exists():
        DB_PATH = Path("./tasks.db")
except:
    DB_PATH = Path("./tasks.db")


def get_backup_filepath(backup_type: str = "auto") -> tuple[str, str]:
    """Generate backup filename and full path"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"backup_{backup_type}_{timestamp}.db"
    filepath = os.path.join(BACKUP_DIR, filename)
    return filename, filepath


def create_local_backup(db: Session, backup_type: str = "auto") -> Optional[Backup]:
    """
    Create a local backup of the database.

    Args:
        db: Database session
        backup_type: "auto" or "manual"

    Returns:
        Backup object if successful, None otherwise
    """
    try:
        # Check if database exists
        if not DB_PATH.exists():
            logger.error(f"Database not found: {DB_PATH}")
            return None

        # Generate backup filename
        filename, filepath = get_backup_filepath(backup_type)

        # Copy database file
        logger.info(f"Creating backup: {filename}")
        shutil.copy2(DB_PATH, filepath)

        # Get file size
        size_bytes = os.path.getsize(filepath)

        # Create backup record
        backup = Backup(
            filename=filename,
            filepath=filepath,
            size_bytes=size_bytes,
            backup_type=backup_type,
            status="completed"
        )

        db.add(backup)
        db.commit()
        db.refresh(backup)

        logger.info(f"✓ Backup created: {filename} ({size_bytes} bytes)")

        # Update last_backup_date in settings
        settings = db.query(Settings).first()
        if settings:
            settings.last_backup_date = datetime.utcnow()
            db.commit()

        # Cleanup old backups
        cleanup_old_backups(db)

        return backup

    except Exception as e:
        logger.error(f"✗ Backup failed: {e}")
        db.rollback()
        return None


def cleanup_old_backups(db: Session):
    """Remove old local backups keeping only the last N"""
    try:
        settings = db.query(Settings).first()
        if not settings:
            return

        keep_count = settings.backup_keep_local_count

        # Get all backups ordered by creation date (newest first)
        all_backups = db.query(Backup).order_by(Backup.created_at.desc()).all()

        # Delete old backups beyond keep_count
        for i, backup in enumerate(all_backups):
            if i >= keep_count:
                # Delete physical file
                if os.path.exists(backup.filepath):
                    try:
                        os.remove(backup.filepath)
                        logger.info(f"Deleted old backup file: {backup.filename}")
                    except Exception as e:
                        logger.error(f"Failed to delete backup file {backup.filename}: {e}")

                # Delete database record
                db.delete(backup)

        db.commit()

    except Exception as e:
        logger.error(f"Failed to cleanup old backups: {e}")


def upload_to_google_drive(backup: Backup, credentials_path: str = None) -> bool:
    """
    Upload backup to Google Drive.

    Args:
        backup: Backup object to upload
        credentials_path: Path to Google service account credentials JSON

    Returns:
        True if successful, False otherwise
    """
    try:
        # Import Google Drive API (optional dependency)
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
        except ImportError:
            logger.error("Google Drive API not installed. Install: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
            return False

        # Get credentials path from env or parameter
        if not credentials_path:
            credentials_path = os.getenv("GOOGLE_DRIVE_CREDENTIALS")

        if not credentials_path or not os.path.exists(credentials_path):
            logger.error("Google Drive credentials not found. Set GOOGLE_DRIVE_CREDENTIALS environment variable.")
            return False

        # Authenticate
        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )

        service = build('drive', 'v3', credentials=credentials)

        # Get folder ID (or create folder)
        folder_id = get_or_create_drive_folder(service)

        # Upload file
        file_metadata = {
            'name': backup.filename,
            'parents': [folder_id] if folder_id else []
        }

        media = MediaFileUpload(backup.filepath, resumable=True)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        # Update backup record
        db = SessionLocal()
        try:
            db_backup = db.query(Backup).filter(Backup.id == backup.id).first()
            if db_backup:
                db_backup.google_drive_id = file.get('id')
                db_backup.uploaded_to_drive = True
                db.commit()

            logger.info(f"✓ Uploaded to Google Drive: {backup.filename}")
            return True

        finally:
            db.close()

    except Exception as e:
        logger.error(f"✗ Google Drive upload failed: {e}")
        return False


def get_or_create_drive_folder(service) -> Optional[str]:
    """Get or create 'TaskManager Backups' folder in Google Drive"""
    try:
        folder_name = "TaskManager Backups"

        # Search for existing folder
        response = service.files().list(
            q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces='drive',
            fields='files(id, name)'
        ).execute()

        files = response.get('files', [])

        if files:
            return files[0]['id']

        # Create folder
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        folder = service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()

        logger.info(f"Created Google Drive folder: {folder_name}")
        return folder.get('id')

    except Exception as e:
        logger.error(f"Failed to get/create Google Drive folder: {e}")
        return None


def get_all_backups(db: Session, limit: int = 50) -> List[Backup]:
    """Get all backups ordered by creation date (newest first)"""
    return db.query(Backup).order_by(Backup.created_at.desc()).limit(limit).all()


def delete_backup(db: Session, backup_id: int) -> bool:
    """Delete a backup (both file and database record)"""
    try:
        backup = db.query(Backup).filter(Backup.id == backup_id).first()
        if not backup:
            return False

        # Delete physical file
        if os.path.exists(backup.filepath):
            os.remove(backup.filepath)

        # TODO: Delete from Google Drive if uploaded
        # if backup.google_drive_id:
        #     delete_from_google_drive(backup.google_drive_id)

        # Delete database record
        db.delete(backup)
        db.commit()

        logger.info(f"Deleted backup: {backup.filename}")
        return True

    except Exception as e:
        logger.error(f"Failed to delete backup: {e}")
        db.rollback()
        return False


def get_backup_by_id(db: Session, backup_id: int) -> Optional[Backup]:
    """Get backup by ID"""
    return db.query(Backup).filter(Backup.id == backup_id).first()
