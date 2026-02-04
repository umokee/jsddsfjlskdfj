"""
Settings repository - Data access layer.
PRIVATE - do not import from outside this module.
"""
from sqlalchemy.orm import Session

from .models import Settings


class SettingsRepository:
    """Repository for Settings data access."""

    def __init__(self, db: Session):
        self.db = db

    def get(self) -> Settings:
        """
        Get settings (creates with defaults if not exists).

        Returns:
            Settings object
        """
        settings = self.db.query(Settings).first()
        if not settings:
            settings = Settings()
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)
        return settings

    def update(self, settings: Settings) -> Settings:
        """
        Update settings.

        Args:
            settings: Settings object with updated values

        Returns:
            Updated settings
        """
        self.db.commit()
        self.db.refresh(settings)
        return settings
