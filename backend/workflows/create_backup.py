"""
Create Backup Workflow - Orchestrates backup creation with optional Google Drive upload.

This workflow coordinates:
1. BackupService - creates local backup
2. SettingsService - checks Google Drive settings
3. BackupService - uploads to Google Drive if enabled
"""

from typing import Optional
from sqlalchemy.orm import Session

from backend.modules.backups import BackupService, BackupResponse
from backend.modules.settings import SettingsService


class CreateBackupWorkflow:
    """Orchestrator for backup creation."""

    def __init__(self, db: Session):
        self.db = db
        self.backup_service = BackupService(db)
        self.settings_service = SettingsService(db)

    def execute(self, backup_type: str = "manual") -> Optional[BackupResponse]:
        """
        Create a backup and optionally upload to Google Drive.

        Args:
            backup_type: "auto" or "manual"

        Returns:
            BackupResponse if successful, None otherwise
        """
        # Create local backup
        backup = self.backup_service.create_local_backup(backup_type)

        if not backup:
            return None

        # Get settings to check if Google Drive is enabled
        settings = self.settings_service.get_data()

        # Upload to Google Drive if enabled
        if settings.google_drive_enabled:
            self.backup_service.upload_to_google_drive(backup)

        # Cleanup old backups
        self.backup_service.cleanup_old_backups(settings.backup_keep_local_count)

        # Update last backup date
        self.settings_service.update_last_backup_date()

        # Return the backup (refresh to get updated drive info)
        return self.backup_service.get_backup_by_id(backup.id)
