"""
Goal repository - Data access layer.
PRIVATE - do not import from outside this module.
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from .models import PointGoal


class GoalRepository:
    """Repository for PointGoal data access."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self, include_achieved: bool = False) -> List[PointGoal]:
        """Get all point goals."""
        query = self.db.query(PointGoal)
        if not include_achieved:
            query = query.filter(PointGoal.achieved == False)
        return query.order_by(PointGoal.target_points).all()

    def get_by_id(self, goal_id: int) -> Optional[PointGoal]:
        """Get point goal by ID."""
        return self.db.query(PointGoal).filter(PointGoal.id == goal_id).first()

    def create(self, goal: PointGoal) -> PointGoal:
        """Create new point goal."""
        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)
        return goal

    def update(self, goal: PointGoal) -> PointGoal:
        """Update existing point goal."""
        self.db.commit()
        self.db.refresh(goal)
        return goal

    def delete(self, goal: PointGoal) -> None:
        """Delete a point goal."""
        self.db.delete(goal)
        self.db.commit()
