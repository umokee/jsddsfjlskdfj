"""
Backup Pydantic schemas.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class BackupBase(BaseModel):
    filename: str
    size_bytes: int
    backup_type: str = "auto"


class BackupResponse(BackupBase):
    id: int
    filepath: str
    created_at: datetime
    uploaded_to_drive: bool = False
    google_drive_id: Optional[str] = None
    status: str = "completed"
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
