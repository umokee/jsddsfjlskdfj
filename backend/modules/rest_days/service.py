"""
RestDay service - Business logic for rest day management.
"""
from sqlalchemy.orm import Session
from datetime import date
from typing import List

from backend.core.exceptions import NotFoundError
from .repository import RestDayRepository
from .models import RestDay
from .schemas import RestDayCreate, RestDayResponse


class RestDayService:
    """Service for rest day operations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = RestDayRepository(db)

    def get_all(self) -> List[RestDayResponse]:
        """Get all rest days."""
        rest_days = self.repo.get_all()
        return [RestDayResponse.model_validate(rd) for rd in rest_days]

    def is_rest_day(self, target_date: date) -> bool:
        """
        Check if a date is a rest day.

        Args:
            target_date: Date to check

        Returns:
            True if it's a rest day
        """
        rest_day = self.repo.get_by_date(target_date)
        return rest_day is not None

    def create(self, data: RestDayCreate) -> RestDayResponse:
        """
        Create a new rest day.

        Args:
            data: Rest day creation data

        Returns:
            Created RestDayResponse
        """
        rest_day = RestDay(**data.model_dump())
        rest_day = self.repo.create(rest_day)
        return RestDayResponse.model_validate(rest_day)

    def delete(self, rest_day_id: int) -> bool:
        """
        Delete a rest day.

        Args:
            rest_day_id: ID of rest day to delete

        Returns:
            True if deleted successfully

        Raises:
            NotFoundError: If rest day not found
        """
        rest_day = self.repo.get_by_id(rest_day_id)
        if not rest_day:
            raise NotFoundError("RestDay", rest_day_id)

        self.repo.delete(rest_day)
        return True
