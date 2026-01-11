from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from datetime import datetime
from backend.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(String, nullable=False)
    project = Column(String, nullable=True)
    priority = Column(Integer, default=5)  # 0-10
    energy = Column(Integer, default=3)    # 0-5
    status = Column(String, default="pending")  # pending, active, completed
    is_habit = Column(Boolean, default=False)
    is_today = Column(Boolean, default=False)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    urgency = Column(Float, default=0.0)

    def calculate_urgency(self):
        """Calculate task urgency based on priority, due date, and energy"""
        urgency = 0.0

        # Priority coefficient (0-10) * 10
        urgency += self.priority * 10.0

        # Due date coefficient
        if self.due_date:
            days_until = (self.due_date - datetime.utcnow()).days
            if days_until <= 0:
                urgency += 50.0  # Overdue
            elif days_until <= 2:
                urgency += 25.0  # Critical
            elif days_until <= 7:
                urgency += 10.0  # Soon

        # Energy coefficient
        if self.energy >= 4:
            urgency += 5.0  # High energy
        elif self.energy <= 1:
            urgency -= 1.0  # Low energy

        self.urgency = urgency
        return urgency
