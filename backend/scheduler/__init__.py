"""
Scheduler - Background job management.

Handles automatic:
- Penalties at configured time
- Roll at configured time
- Database backups
"""

from .jobs import start_scheduler, stop_scheduler

__all__ = ["start_scheduler", "stop_scheduler"]
