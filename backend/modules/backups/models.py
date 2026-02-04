"""
Backup database model.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime

from backend.core.database import Base


class Backup(Base):
    __tablename__ = "backups"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)  # e.g., "backup_2024-01-15_14-30-00.db"
    filepath = Column(String, nullable=False)  # Local path
    size_bytes = Column(Integer, nullable=False)  # File size in bytes
    created_at = Column(DateTime, default=datetime.now, index=True)

    # Google Drive info
    google_drive_id = Column(String, nullable=True)  # Google Drive file ID
    uploaded_to_drive = Column(Boolean, default=False)

    # Backup type
    backup_type = Column(String, default="auto")  # "auto" or "manual"

    # Status
    status = Column(String, default="completed")  # "completed", "failed", "uploading"
    error_message = Column(String, nullable=True)
