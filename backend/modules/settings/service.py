"""
Settings service - Business logic for settings management.
"""
from datetime import date, datetime
from sqlalchemy.orm import Session

from backend.shared import get_effective_date
from .repository import SettingsRepository
from .schemas import SettingsUpdate, SettingsResponse, SettingsData


class SettingsService:
    """Service for settings operations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = SettingsRepository(db)

    def get(self) -> SettingsResponse:
        """
        Get current settings with effective date.

        Returns:
            SettingsResponse with all settings and computed effective_date
        """
        settings = self.repo.get()

        # Calculate effective date
        effective = get_effective_date(
            settings.day_start_enabled,
            settings.day_start_time
        )

        # Convert to response with effective_date
        response = SettingsResponse.model_validate(settings)
        response.effective_date = effective

        return response

    def get_data(self) -> SettingsData:
        """
        Get settings as internal DTO for other modules.

        Returns:
            SettingsData DTO
        """
        settings = self.repo.get()
        return SettingsData.model_validate(settings)

    def get_effective_date(self) -> date:
        """
        Get current effective date based on day_start settings.

        Returns:
            Effective date (today or yesterday based on day_start_time)
        """
        settings = self.repo.get()
        return get_effective_date(
            settings.day_start_enabled,
            settings.day_start_time
        )

    def update(self, update_data: SettingsUpdate) -> SettingsResponse:
        """
        Update settings.

        Args:
            update_data: New settings values

        Returns:
            Updated SettingsResponse
        """
        settings = self.repo.get()

        # Update all provided fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        settings = self.repo.update(settings)

        # Calculate effective date for response
        effective = get_effective_date(
            settings.day_start_enabled,
            settings.day_start_time
        )

        response = SettingsResponse.model_validate(settings)
        response.effective_date = effective

        return response

    def set_last_roll_date(self, roll_date: date) -> None:
        """
        Update the last roll date.

        Args:
            roll_date: Date of the roll
        """
        settings = self.repo.get()
        settings.last_roll_date = roll_date
        self.repo.update(settings)

    def set_pending_roll(self, pending: bool, started_at=None) -> None:
        """
        Set pending roll status.

        Args:
            pending: Whether roll is pending
            started_at: When pending started (optional)
        """
        settings = self.repo.get()
        settings.pending_roll = pending
        settings.pending_roll_started_at = started_at
        self.repo.update(settings)

    def set_last_backup_date(self, backup_date) -> None:
        """
        Update the last backup date.

        Args:
            backup_date: Datetime of the backup
        """
        settings = self.repo.get()
        settings.last_backup_date = backup_date
        self.repo.update(settings)

    # Alias methods for workflows
    def update_last_roll_date(self, roll_date: date) -> None:
        """Alias for set_last_roll_date."""
        self.set_last_roll_date(roll_date)

    def clear_pending_roll(self) -> None:
        """Clear pending roll flag and timestamp."""
        settings = self.repo.get()
        settings.pending_roll = False
        settings.pending_roll_started_at = None
        self.repo.update(settings)

    def update_last_backup_date(self) -> None:
        """Update last backup date to current time."""
        self.set_last_backup_date(datetime.now())
