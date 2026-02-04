"""
Backup repository - data access layer.
"""

from typing import List, Optional
from sqlalchemy.orm import Session

from .models import Backup


class BackupRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, backup_id: int) -> Optional[Backup]:
        """Get backup by ID."""
        return self.db.query(Backup).filter(Backup.id == backup_id).first()

    def get_all(self, limit: int = 50) -> List[Backup]:
        """Get all backups ordered by creation date (newest first)."""
        return (
            self.db.query(Backup)
            .order_by(Backup.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_last_auto_backup(self) -> Optional[Backup]:
        """Get the most recent auto backup."""
        return (
            self.db.query(Backup)
            .filter(Backup.backup_type == "auto")
            .order_by(Backup.created_at.desc())
            .first()
        )

    def create(
        self,
        filename: str,
        filepath: str,
        size_bytes: int,
        backup_type: str = "auto",
        status: str = "completed",
    ) -> Backup:
        """Create a new backup record."""
        backup = Backup(
            filename=filename,
            filepath=filepath,
            size_bytes=size_bytes,
            backup_type=backup_type,
            status=status,
        )
        self.db.add(backup)
        self.db.commit()
        self.db.refresh(backup)
        return backup

    def update_drive_info(
        self, backup_id: int, google_drive_id: str
    ) -> Optional[Backup]:
        """Update backup with Google Drive info."""
        backup = self.get_by_id(backup_id)
        if backup:
            backup.google_drive_id = google_drive_id
            backup.uploaded_to_drive = True
            self.db.commit()
            self.db.refresh(backup)
        return backup

    def delete(self, backup_id: int) -> bool:
        """Delete backup record."""
        backup = self.get_by_id(backup_id)
        if not backup:
            return False
        self.db.delete(backup)
        self.db.commit()
        return True

    def get_backups_beyond_count(self, keep_count: int) -> List[Backup]:
        """Get backups beyond the keep count (for cleanup)."""
        all_backups = (
            self.db.query(Backup)
            .order_by(Backup.created_at.desc())
            .all()
        )
        return all_backups[keep_count:] if len(all_backups) > keep_count else []
