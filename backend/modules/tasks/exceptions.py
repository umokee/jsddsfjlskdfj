"""
Task module exceptions.
"""
from backend.core.exceptions import NotFoundError, AppError


class TaskNotFoundError(NotFoundError):
    """Task not found."""

    def __init__(self, task_id: int):
        super().__init__("Task", task_id)
        self.task_id = task_id


class DependencyNotMetError(AppError):
    """Task dependencies are not met."""

    def __init__(self, task_id: int, dependency_id: int):
        self.task_id = task_id
        self.dependency_id = dependency_id
        super().__init__(
            f"Task {task_id} cannot be started/completed: dependency {dependency_id} not met",
            code="DEPENDENCY_NOT_MET"
        )
