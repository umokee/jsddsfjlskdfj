"""
PointGoal database model.
PRIVATE - do not import from outside this module.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date
from datetime import datetime

from core.database import Base


class PointGoal(Base):
    __tablename__ = "point_goals"

    id = Column(Integer, primary_key=True, index=True)
    goal_type = Column(String, default="points")  # "points" or "project_completion"
    target_points = Column(Integer, nullable=True)  # For points goals
    project_name = Column(String, nullable=True)  # For project_completion goals
    reward_description = Column(String, nullable=False)  # What you'll reward yourself
    reward_claimed = Column(Boolean, default=False)  # Did you claim the reward?
    reward_claimed_at = Column(DateTime, nullable=True)  # When claimed
    deadline = Column(Date, nullable=True)
    achieved = Column(Boolean, default=False)
    achieved_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
