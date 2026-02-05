"""
PointHistory model re-export for module encapsulation.
The actual model is defined in backend.models to ensure single SQLAlchemy Base.
"""
from backend.models import PointHistory

__all__ = ["PointHistory"]
