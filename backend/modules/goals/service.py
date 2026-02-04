"""
Goal service - Business logic for goal management.
"""
from datetime import date, datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from .repository import GoalRepository
from .models import PointGoal
from .schemas import PointGoalCreate, PointGoalUpdate, PointGoalResponse
from .exceptions import GoalNotFoundError, InvalidGoalError


class GoalService:
    """Service for goal operations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = GoalRepository(db)

    def get_all(self, include_achieved: bool = False) -> List[PointGoalResponse]:
        """Get all goals."""
        goals = self.repo.get_all(include_achieved)
        return [PointGoalResponse.model_validate(g) for g in goals]

    def get(self, goal_id: int) -> PointGoalResponse:
        """
        Get goal by ID.

        Raises:
            GoalNotFoundError: If goal not found
        """
        goal = self.repo.get_by_id(goal_id)
        if not goal:
            raise GoalNotFoundError(goal_id)
        return PointGoalResponse.model_validate(goal)

    def create(
        self,
        data: PointGoalCreate,
        project_has_tasks: bool = True
    ) -> PointGoalResponse:
        """
        Create a new goal.

        Args:
            data: Goal creation data
            project_has_tasks: For project goals, whether project has tasks

        Raises:
            InvalidGoalError: If goal configuration is invalid
        """
        # Validate project_completion goals
        if data.goal_type == "project_completion":
            if not data.project_name:
                raise InvalidGoalError("project_name is required for project_completion goals")
            if not project_has_tasks:
                raise InvalidGoalError(
                    f"Project '{data.project_name}' has no tasks. Add tasks before creating a goal."
                )

        # Validate points goals
        if data.goal_type == "points":
            if not data.target_points or data.target_points <= 0:
                raise InvalidGoalError("target_points must be greater than 0 for points goals")

        goal = PointGoal(**data.model_dump())
        goal = self.repo.create(goal)
        return PointGoalResponse.model_validate(goal)

    def update(self, goal_id: int, data: PointGoalUpdate) -> PointGoalResponse:
        """
        Update a goal.

        Raises:
            GoalNotFoundError: If goal not found
        """
        goal = self.repo.get_by_id(goal_id)
        if not goal:
            raise GoalNotFoundError(goal_id)

        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(goal, key, value)

        goal = self.repo.update(goal)
        return PointGoalResponse.model_validate(goal)

    def delete(self, goal_id: int) -> bool:
        """
        Delete a goal.

        Raises:
            GoalNotFoundError: If goal not found
        """
        goal = self.repo.get_by_id(goal_id)
        if not goal:
            raise GoalNotFoundError(goal_id)

        self.repo.delete(goal)
        return True

    def claim_reward(self, goal_id: int) -> PointGoalResponse:
        """
        Claim reward for an achieved goal.

        Raises:
            GoalNotFoundError: If goal not found
            InvalidGoalError: If goal not achieved
        """
        goal = self.repo.get_by_id(goal_id)
        if not goal:
            raise GoalNotFoundError(goal_id)

        if not goal.achieved:
            raise InvalidGoalError("Cannot claim reward for unachieved goal")

        goal.reward_claimed = True
        goal.reward_claimed_at = datetime.now()
        goal = self.repo.update(goal)
        return PointGoalResponse.model_validate(goal)

    def check_achievements(
        self,
        current_points: int,
        today: date,
        get_project_progress: callable
    ) -> List[PointGoalResponse]:
        """
        Check and mark achieved goals.

        Args:
            current_points: Current cumulative points
            today: Current effective date
            get_project_progress: Function to get project progress (project_name) -> dict

        Returns:
            List of newly achieved goals
        """
        goals = self.repo.get_all(include_achieved=False)
        achieved_goals = []

        for goal in goals:
            is_achieved = False

            if goal.goal_type == "points":
                if goal.target_points and current_points >= goal.target_points:
                    is_achieved = True

            elif goal.goal_type == "project_completion":
                if goal.project_name:
                    progress = get_project_progress(goal.project_name)
                    total = progress.get("total_tasks", 0)
                    completed = progress.get("completed_tasks", 0)
                    if total > 0 and completed == total:
                        is_achieved = True

            if is_achieved:
                goal.achieved = True
                goal.achieved_date = today
                self.repo.update(goal)
                achieved_goals.append(PointGoalResponse.model_validate(goal))

        return achieved_goals

    def enrich_with_progress(
        self,
        goal_response: PointGoalResponse,
        get_project_progress: callable
    ) -> PointGoalResponse:
        """Add project progress to goal response."""
        if goal_response.goal_type == "project_completion" and goal_response.project_name:
            progress = get_project_progress(goal_response.project_name)
            goal_response.total_tasks = progress.get("total_tasks", 0)
            goal_response.completed_tasks = progress.get("completed_tasks", 0)
        return goal_response
