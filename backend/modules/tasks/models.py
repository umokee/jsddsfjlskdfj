"""
Task database model.
PRIVATE - do not import from outside this module.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Date
from datetime import datetime

from core.database import Base


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
    created_at = Column(DateTime, default=datetime.now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    urgency = Column(Float, default=0.0)

    # Time tracking (accumulated seconds)
    time_spent = Column(Integer, default=0)  # Total seconds spent on this task
    estimated_time = Column(Integer, default=0)  # Estimated time in seconds

    # Task dependencies
    depends_on = Column(Integer, nullable=True)  # ID of task that must be completed first

    # Habit-specific fields
    recurrence_type = Column(String, default="none")  # none, daily, every_n_days, weekly
    recurrence_interval = Column(Integer, default=1)   # For every_n_days: interval in days
    recurrence_days = Column(String, nullable=True)    # For weekly: JSON array like "[1,3,5]" (Mon,Wed,Fri)
    habit_type = Column(String, default="skill")  # skill (new habit) or routine (daily routine)
    streak = Column(Integer, default=0)                # Current streak count
    last_completed_date = Column(Date, nullable=True)  # Last completion date for streak tracking
    daily_target = Column(Integer, default=1)          # How many times per day habit should be completed
    daily_completed = Column(Integer, default=0)       # How many times completed today

    def calculate_urgency(self):
        """
        Calculate task urgency for weighted random selection.

        Formula: urgency = priority * 10 + due_date_bonus + energy_bonus

        Higher urgency = higher probability of being selected for today's plan.
        """
        urgency = 0.0

        # Priority component (0-10) * 10 = 0-100
        urgency += self.priority * 10.0

        # Due date component
        if self.due_date:
            # Handle both timezone-aware and timezone-naive datetimes
            due_date_naive = self.due_date.replace(tzinfo=None) if self.due_date.tzinfo else self.due_date
            now_naive = datetime.now()

            days_until = (due_date_naive - now_naive).days
            if days_until <= 0:
                urgency += 100.0  # Overdue - maximum priority
            elif days_until <= 2:
                urgency += 75.0   # Critical - very high probability (~90-99%)
            elif days_until <= 7:
                urgency += 30.0   # Soon - noticeably higher probability

        # Energy component
        if self.energy >= 4:
            urgency += 5.0   # High energy - slightly increases probability
        elif self.energy <= 1:
            urgency -= 5.0   # Low energy - slightly decreases probability

        self.urgency = urgency
        return urgency
