"""
Points repository - Data access layer.
PRIVATE - do not import from outside this module.
"""
from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from .models import PointHistory


class PointHistoryRepository:
    """Repository for PointHistory data access."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_date(self, target_date: date) -> Optional[PointHistory]:
        """Get point history for specific date."""
        return self.db.query(PointHistory).filter(PointHistory.date == target_date).first()

    def get_most_recent(self, before_date: date) -> Optional[PointHistory]:
        """Get most recent history entry before specified date."""
        return self.db.query(PointHistory).filter(
            PointHistory.date < before_date
        ).order_by(PointHistory.date.desc()).first()

    def get_history(self, days: int, from_date: date) -> List[PointHistory]:
        """Get point history for last N days from specified date."""
        start_date = from_date - timedelta(days=days)
        return self.db.query(PointHistory).filter(
            PointHistory.date >= start_date
        ).order_by(PointHistory.date.desc()).all()

    def get_all_after(self, after_date: date) -> List[PointHistory]:
        """Get all history entries after a date."""
        return self.db.query(PointHistory).filter(
            PointHistory.date > after_date
        ).order_by(PointHistory.date).all()

    def create(self, history: PointHistory) -> PointHistory:
        """Create new point history entry."""
        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history

    def update(self, history: PointHistory) -> PointHistory:
        """Update existing point history."""
        self.db.commit()
        self.db.refresh(history)
        return history
