from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Date
from datetime import datetime, date
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

    # Time tracking (accumulated seconds)
    time_spent = Column(Integer, default=0)  # Total seconds spent on this task

    # Habit-specific fields
    recurrence_type = Column(String, default="none")  # none, daily, every_n_days, weekly
    recurrence_interval = Column(Integer, default=1)   # For every_n_days: interval in days
    recurrence_days = Column(String, nullable=True)    # For weekly: JSON array like "[1,3,5]" (Mon,Wed,Fri)
    streak = Column(Integer, default=0)                # Current streak count
    last_completed_date = Column(Date, nullable=True)  # Last completion date for streak tracking

    def calculate_urgency(self):
        """Calculate task urgency based on priority, due date, and energy"""
        urgency = 0.0

        # Priority coefficient (0-10) * 10
        urgency += self.priority * 10.0

        # Due date coefficient
        if self.due_date:
            # Handle both timezone-aware and timezone-naive datetimes
            due_date_naive = self.due_date.replace(tzinfo=None) if self.due_date.tzinfo else self.due_date
            now_naive = datetime.utcnow()

            days_until = (due_date_naive - now_naive).days
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
