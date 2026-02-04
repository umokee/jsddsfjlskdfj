"""
RestDay repository - Data access layer.
PRIVATE - do not import from outside this module.
"""
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Optional

from .models import RestDay


class RestDayRepository:
    """Repository for RestDay data access."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[RestDay]:
        """Get all rest days sorted by date."""
        return self.db.query(RestDay).order_by(RestDay.date).all()

    def get_by_id(self, rest_day_id: int) -> Optional[RestDay]:
        """Get rest day by ID."""
        return self.db.query(RestDay).filter(RestDay.id == rest_day_id).first()

    def get_by_date(self, target_date: date) -> Optional[RestDay]:
        """Get rest day by date."""
        return self.db.query(RestDay).filter(RestDay.date == target_date).first()

    def create(self, rest_day: RestDay) -> RestDay:
        """Create a new rest day."""
        self.db.add(rest_day)
        self.db.commit()
        self.db.refresh(rest_day)
        return rest_day

    def delete(self, rest_day: RestDay) -> None:
        """Delete a rest day."""
        self.db.delete(rest_day)
        self.db.commit()
