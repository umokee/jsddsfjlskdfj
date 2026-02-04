"""
RestDay database model.
PRIVATE - do not import from outside this module.
"""
from sqlalchemy import Column, Integer, String, DateTime, Date
from datetime import datetime

from core.database import Base


class RestDay(Base):
    __tablename__ = "rest_days"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)  # Optional reason (e.g., "New Year", "Rest day")
    created_at = Column(DateTime, default=datetime.now)
