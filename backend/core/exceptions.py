"""
Base exception classes for the application.
Module-specific exceptions should inherit from these.
"""


class AppError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, resource: str, identifier):
        self.resource = resource
        self.identifier = identifier
        super().__init__(
            f"{resource} with id {identifier} not found",
            code="NOT_FOUND"
        )


class ValidationError(AppError):
    """Validation failed."""

    def __init__(self, field: str, message: str):
        self.field = field
        super().__init__(
            f"Validation error for {field}: {message}",
            code="VALIDATION_ERROR"
        )


class DatabaseError(AppError):
    """Database operation failed."""

    def __init__(self, operation: str, details: str):
        self.operation = operation
        self.details = details
        super().__init__(
            f"Database {operation} failed: {details}",
            code="DATABASE_ERROR"
        )


class BackupError(AppError):
    """Backup operation failed."""

    def __init__(self, message: str):
        super().__init__(
            f"Backup operation failed: {message}",
            code="BACKUP_ERROR"
        )


class RollNotAvailableError(AppError):
    """Roll is not currently available."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(
            f"Roll not available: {reason}",
            code="ROLL_NOT_AVAILABLE"
        )


class DependencyNotMetError(AppError):
    """Task dependencies are not met."""

    def __init__(self, task_id: int, dependency_id: int):
        self.task_id = task_id
        self.dependency_id = dependency_id
        super().__init__(
            f"Task {task_id} cannot be started/completed: dependency {dependency_id} not met",
            code="DEPENDENCY_NOT_MET"
        )


class InvalidTimeFormatError(AppError):
    """Time format is invalid."""

    def __init__(self, time_str: str):
        self.time_str = time_str
        super().__init__(
            f"Invalid time format: {time_str}. Expected HH:MM",
            code="INVALID_TIME_FORMAT"
        )
