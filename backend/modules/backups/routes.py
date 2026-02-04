"""
Backup API routes.
"""

import os
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import verify_api_key
from .schemas import BackupResponse
from .service import BackupService

router = APIRouter(prefix="/api/backups", tags=["backups"])


def get_backup_service(db: Session = Depends(get_db)) -> BackupService:
    return BackupService(db)


@router.get("", response_model=List[BackupResponse], dependencies=[Depends(verify_api_key)])
async def get_backups(
    limit: int = 50,
    service: BackupService = Depends(get_backup_service),
):
    """Get all backups (newest first)."""
    return service.get_all_backups(limit)


@router.post(
    "/create",
    response_model=BackupResponse,
    dependencies=[Depends(verify_api_key)],
)
async def create_backup(
    db: Session = Depends(get_db),
):
    """Create a manual backup (with Google Drive upload if enabled)."""
    from backend.workflows import CreateBackupWorkflow

    workflow = CreateBackupWorkflow(db)
    backup = workflow.execute(backup_type="manual")

    if not backup:
        raise HTTPException(status_code=500, detail="Failed to create backup")

    return backup


@router.get(
    "/{backup_id}/download",
    dependencies=[Depends(verify_api_key)],
)
async def download_backup(
    backup_id: int,
    service: BackupService = Depends(get_backup_service),
):
    """Download a backup file."""
    backup = service.get_backup_by_id(backup_id)

    if not backup:
        raise HTTPException(status_code=404, detail="Backup not found")

    if not os.path.exists(backup.filepath):
        raise HTTPException(status_code=404, detail="Backup file not found on disk")

    return FileResponse(
        path=backup.filepath,
        filename=backup.filename,
        media_type="application/x-sqlite3",
    )


@router.delete(
    "/{backup_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(verify_api_key)],
)
async def delete_backup(
    backup_id: int,
    service: BackupService = Depends(get_backup_service),
):
    """Delete a backup."""
    if not service.delete_backup(backup_id):
        raise HTTPException(status_code=404, detail="Backup not found")
