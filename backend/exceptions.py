"""
Custom exceptions for the task manager application.
Provides specific exception types for better error handling and recovery.
"""


class TaskManagerException(Exception):
    """Base exception for task manager application"""
    pass


class TaskNotFoundException(TaskManagerException):
    """Raised when a task is not found"""
    def __init__(self, task_id: int):
        self.task_id = task_id
        super().__init__(f"Task with ID {task_id} not found")


class GoalNotFoundException(TaskManagerException):
    """Raised when a goal is not found"""
    def __init__(self, goal_id: int):
        self.goal_id = goal_id
        super().__init__(f"Goal with ID {goal_id} not found")


class RestDayNotFoundException(TaskManagerException):
    """Raised when a rest day is not found"""
    def __init__(self, rest_day_id: int):
        self.rest_day_id = rest_day_id
        super().__init__(f"Rest day with ID {rest_day_id} not found")


class RollNotAvailableException(TaskManagerException):
    """Raised when roll is not currently available"""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Roll not available: {reason}")


class InvalidTimeFormatException(TaskManagerException):
    """Raised when time format is invalid"""
    def __init__(self, time_str: str):
        self.time_str = time_str
        super().__init__(f"Invalid time format: {time_str}. Expected HH:MM")


class DependencyNotMetException(TaskManagerException):
    """Raised when task dependencies are not met"""
    def __init__(self, task_id: int, dependency_id: int):
        self.task_id = task_id
        self.dependency_id = dependency_id
        super().__init__(
            f"Task {task_id} cannot be completed: dependency {dependency_id} not met"
        )


class DatabaseException(TaskManagerException):
    """Raised when database operations fail"""
    def __init__(self, operation: str, details: str):
        self.operation = operation
        self.details = details
        super().__init__(f"Database {operation} failed: {details}")


class BackupException(TaskManagerException):
    """Raised when backup operations fail"""
    def __init__(self, message: str):
        super().__init__(f"Backup operation failed: {message}")


class ValidationException(TaskManagerException):
    """Raised when data validation fails"""
    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(f"Validation error for {field}: {message}")
