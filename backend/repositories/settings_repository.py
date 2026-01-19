"""
Settings repository - Data access layer for Settings model.
Handles all database queries related to settings.
"""
from sqlalchemy.orm import Session
from backend.models import Settings


class SettingsRepository:
    """Repository for Settings data access"""

    @staticmethod
    def get(db: Session) -> Settings:
        """
        Get settings (creates with defaults if not exists).

        Returns:
            Settings object
        """
        settings = db.query(Settings).first()
        if not settings:
            settings = Settings()
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    @staticmethod
    def update(db: Session, settings: Settings) -> Settings:
        """
        Update settings.

        Args:
            db: Database session
            settings: Settings object with updated values

        Returns:
            Updated settings
        """
        db.commit()
        db.refresh(settings)
        return settings
