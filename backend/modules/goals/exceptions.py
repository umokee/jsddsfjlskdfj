"""
Goal module exceptions.
"""
from backend.core.exceptions import NotFoundError, ValidationError


class GoalNotFoundError(NotFoundError):
    """Goal not found."""

    def __init__(self, goal_id: int):
        super().__init__("Goal", goal_id)
        self.goal_id = goal_id


class InvalidGoalError(ValidationError):
    """Invalid goal configuration."""

    def __init__(self, message: str):
        super().__init__("goal", message)
