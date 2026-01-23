"""
Goal management service.
Handles point goals and rest days.
"""
from datetime import date, datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from backend.models import PointGoal, RestDay
from backend.schemas import PointGoalCreate, PointGoalUpdate, RestDayCreate
from backend.repositories.points_repository import (
    PointGoalRepository, RestDayRepository
)


class GoalService:
    """Service for managing point goals"""

    def __init__(self, db: Session):
        self.db = db
        self.goal_repo = PointGoalRepository()

    def get_goals(self, include_achieved: bool = False) -> List[PointGoal]:
        """Get all point goals"""
        return self.goal_repo.get_all(self.db, include_achieved)

    def create_goal(self, goal_data: PointGoalCreate) -> PointGoal:
        """Create a new point goal"""
        goal = PointGoal(**goal_data.model_dump())
        return self.goal_repo.create(self.db, goal)

    def update_goal(
        self,
        goal_id: int,
        goal_update: PointGoalUpdate
    ) -> Optional[PointGoal]:
        """Update an existing point goal"""
        goal = self.goal_repo.get_by_id(self.db, goal_id)
        if not goal:
            return None

        update_data = goal_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(goal, key, value)

        return self.goal_repo.update(self.db, goal)

    def delete_goal(self, goal_id: int) -> bool:
        """Delete a point goal"""
        goal = self.goal_repo.get_by_id(self.db, goal_id)
        if not goal:
            return False

        self.goal_repo.delete(self.db, goal)
        return True

    def claim_reward(self, goal_id: int) -> Optional[PointGoal]:
        """Claim reward for an achieved goal"""
        goal = self.goal_repo.get_by_id(self.db, goal_id)
        if not goal:
            return None

        if not goal.achieved:
            return None

        # Mark reward as claimed
        goal.reward_claimed = True
        goal.reward_claimed_at = datetime.now()

        return self.goal_repo.update(self.db, goal)


class RestDayService:
    """Service for managing rest days"""

    def __init__(self, db: Session):
        self.db = db
        self.rest_day_repo = RestDayRepository()

    def get_rest_days(self) -> List[RestDay]:
        """Get all rest days"""
        return self.rest_day_repo.get_all(self.db)

    def create_rest_day(self, rest_day_data: RestDayCreate) -> RestDay:
        """Create a new rest day"""
        rest_day = RestDay(**rest_day_data.model_dump())
        return self.rest_day_repo.create(self.db, rest_day)

    def delete_rest_day(self, rest_day_id: int) -> bool:
        """Delete a rest day"""
        rest_day = self.rest_day_repo.get_by_id(self.db, rest_day_id)
        if not rest_day:
            return False

        self.rest_day_repo.delete(self.db, rest_day)
        return True
