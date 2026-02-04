"""
Application-wide constants.
No business logic, no dependencies on other modules.
"""

# Task Status Values
TASK_STATUS_PENDING = "pending"
TASK_STATUS_ACTIVE = "active"
TASK_STATUS_COMPLETED = "completed"

# Recurrence Types
RECURRENCE_NONE = "none"
RECURRENCE_DAILY = "daily"
RECURRENCE_EVERY_N_DAYS = "every_n_days"
RECURRENCE_WEEKLY = "weekly"

# Habit Types
HABIT_TYPE_SKILL = "skill"
HABIT_TYPE_ROUTINE = "routine"

# Points Calculation Constants
TIME_QUALITY_THRESHOLD = 0.5
TIME_RATIO_THRESHOLD_LOW = 0.8
TIME_RATIO_THRESHOLD_HIGH = 1.5
TIME_RATIO_THRESHOLD_VERY_HIGH = 3.0
TIME_QUALITY_FACTOR_GOOD = 0.9
TIME_QUALITY_FACTOR_BAD = 0.7
FOCUS_PENALTY_MULTIPLIER = 0.8

# Penalty Constants
ROUTINE_PENALTY_MULTIPLIER = 0.5
PROJECTION_MULTIPLIER_LOW = 0.7
PROJECTION_MULTIPLIER_HIGH = 1.3

# Scheduler Default Times
DEFAULT_ROLL_TIME = "06:00"
DEFAULT_PENALTY_TIME = "00:01"
DEFAULT_BACKUP_TIME = "03:00"

# Database Configuration
DEFAULT_DB_DIRECTORY = "/var/lib/task-manager"
DEFAULT_DB_FILENAME = "tasks.db"

# Logging Configuration
DEFAULT_LOG_DIRECTORY_PROD = "/var/log/task-manager"
DEFAULT_LOG_DIRECTORY_DEV = "logs"
MAX_LOG_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT = 5

# CORS Configuration (localhost only)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

# API Configuration
API_V1_PREFIX = "/api"

# Backup Configuration
BACKUP_RETENTION_DAYS_DEFAULT = 7
