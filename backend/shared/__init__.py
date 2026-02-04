"""
Shared utilities module.
Contains pure utility functions without business logic.
No dependencies on core/ or modules/.
"""

from .constants import (
    # Task Status
    TASK_STATUS_PENDING,
    TASK_STATUS_ACTIVE,
    TASK_STATUS_COMPLETED,
    # Recurrence Types
    RECURRENCE_NONE,
    RECURRENCE_DAILY,
    RECURRENCE_EVERY_N_DAYS,
    RECURRENCE_WEEKLY,
    # Habit Types
    HABIT_TYPE_SKILL,
    HABIT_TYPE_ROUTINE,
    # Time Constants
    DEFAULT_ROLL_TIME,
    DEFAULT_PENALTY_TIME,
    DEFAULT_BACKUP_TIME,
    # CORS
    CORS_ALLOWED_ORIGINS,
)

from .date_utils import (
    parse_time,
    normalize_to_midnight,
    get_effective_date,
    calculate_next_occurrence,
    calculate_next_due_date,
    get_day_range,
)

__all__ = [
    # Constants
    "TASK_STATUS_PENDING",
    "TASK_STATUS_ACTIVE",
    "TASK_STATUS_COMPLETED",
    "RECURRENCE_NONE",
    "RECURRENCE_DAILY",
    "RECURRENCE_EVERY_N_DAYS",
    "RECURRENCE_WEEKLY",
    "HABIT_TYPE_SKILL",
    "HABIT_TYPE_ROUTINE",
    "DEFAULT_ROLL_TIME",
    "DEFAULT_PENALTY_TIME",
    "DEFAULT_BACKUP_TIME",
    "CORS_ALLOWED_ORIGINS",
    # Date Utils
    "parse_time",
    "normalize_to_midnight",
    "get_effective_date",
    "calculate_next_occurrence",
    "calculate_next_due_date",
    "get_day_range",
]
