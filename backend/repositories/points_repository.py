"""
Points repository - Data access layer for point-related models.
Handles all database queries related to points, goals, and rest days.
"""
from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models import PointHistory, PointGoal, RestDay


class PointHistoryRepository:
    """Repository for PointHistory data access"""

    @staticmethod
    def get_by_date(db: Session, target_date: date) -> Optional[PointHistory]:
        """Get point history for specific date"""
        return db.query(PointHistory).filter(PointHistory.date == target_date).first()

    @staticmethod
    def get_most_recent(db: Session, before_date: date) -> Optional[PointHistory]:
        """Get most recent history entry before specified date"""
        return db.query(PointHistory).filter(
            PointHistory.date < before_date
        ).order_by(PointHistory.date.desc()).first()

    @staticmethod
    def get_history(db: Session, days: int, from_date: date) -> List[PointHistory]:
        """Get point history for last N days from specified date"""
        start_date = from_date - timedelta(days=days)
        return db.query(PointHistory).filter(
            PointHistory.date >= start_date
        ).order_by(PointHistory.date.desc()).all()

    @staticmethod
    def create(db: Session, history: PointHistory) -> PointHistory:
        """Create new point history entry"""
        db.add(history)
        db.commit()
        db.refresh(history)
        return history

    @staticmethod
    def update(db: Session, history: PointHistory) -> PointHistory:
        """Update existing point history"""
        db.commit()
        db.refresh(history)
        return history


class PointGoalRepository:
    """Repository for PointGoal data access"""

    @staticmethod
    def get_all(db: Session, include_achieved: bool = False) -> List[PointGoal]:
        """Get all point goals"""
        query = db.query(PointGoal)
        if not include_achieved:
            query = query.filter(PointGoal.achieved == False)
        return query.order_by(PointGoal.target_points).all()

    @staticmethod
    def get_by_id(db: Session, goal_id: int) -> Optional[PointGoal]:
        """Get point goal by ID"""
        return db.query(PointGoal).filter(PointGoal.id == goal_id).first()

    @staticmethod
    def create(db: Session, goal: PointGoal) -> PointGoal:
        """Create new point goal"""
        db.add(goal)
        db.commit()
        db.refresh(goal)
        return goal

    @staticmethod
    def update(db: Session, goal: PointGoal) -> PointGoal:
        """Update existing point goal"""
        db.commit()
        db.refresh(goal)
        return goal

    @staticmethod
    def delete(db: Session, goal: PointGoal) -> None:
        """Delete a point goal"""
        db.delete(goal)
        db.commit()


class RestDayRepository:
    """Repository for RestDay data access"""

    @staticmethod
    def get_all(db: Session) -> List[RestDay]:
        """Get all rest days"""
        return db.query(RestDay).order_by(RestDay.date).all()

    @staticmethod
    def get_by_date(db: Session, target_date: date) -> Optional[RestDay]:
        """Get rest day by date"""
        return db.query(RestDay).filter(RestDay.date == target_date).first()

    @staticmethod
    def get_by_id(db: Session, rest_day_id: int) -> Optional[RestDay]:
        """Get rest day by ID"""
        return db.query(RestDay).filter(RestDay.id == rest_day_id).first()

    @staticmethod
    def create(db: Session, rest_day: RestDay) -> RestDay:
        """Create new rest day"""
        db.add(rest_day)
        db.commit()
        db.refresh(rest_day)
        return rest_day

    @staticmethod
    def delete(db: Session, rest_day: RestDay) -> None:
        """Delete a rest day"""
        db.delete(rest_day)
        db.commit()
