"""
Task model re-export for module encapsulation.
The actual model is defined in backend.models to ensure single SQLAlchemy Base.
"""
from backend.models import Task

__all__ = ["Task"]
