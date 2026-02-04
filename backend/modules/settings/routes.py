"""
Settings HTTP routes.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import verify_api_key
from .service import SettingsService
from .schemas import SettingsUpdate, SettingsResponse

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Get current settings."""
    service = SettingsService(db)
    return service.get()


@router.put("", response_model=SettingsResponse)
def update_settings(
    settings_update: SettingsUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key)
):
    """Update settings."""
    service = SettingsService(db)
    return service.update(settings_update)
