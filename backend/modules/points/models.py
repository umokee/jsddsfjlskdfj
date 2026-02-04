"""
PointHistory database model.
PRIVATE - do not import from outside this module.
"""
from sqlalchemy import Column, Integer, String, DateTime, Date, Float
from datetime import datetime

from core.database import Base


class PointHistory(Base):
    __tablename__ = "point_history"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)

    # Points breakdown
    points_earned = Column(Integer, default=0)  # Total earned from tasks/habits
    points_penalty = Column(Integer, default=0)  # Total penalties
    points_bonus = Column(Integer, default=0)   # Daily completion bonuses
    daily_total = Column(Integer, default=0)    # Net for the day
    cumulative_total = Column(Integer, default=0)  # Running total

    # Task statistics
    tasks_completed = Column(Integer, default=0)
    habits_completed = Column(Integer, default=0)
    tasks_planned = Column(Integer, default=0)  # Tasks that were in TODAY
    completion_rate = Column(Float, default=0.0)

    # Penalty streak tracking
    penalty_streak = Column(Integer, default=0)  # Consecutive days with penalties

    # Detailed breakdown (JSON)
    details = Column(String, nullable=True)  # JSON with per-task breakdown

    created_at = Column(DateTime, default=datetime.now)
