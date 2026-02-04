"""
Points service - Business logic for points calculation.
Does NOT depend on tasks module (receives data via parameters).
"""
import math
import json
from datetime import datetime, date, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session

from backend.shared.constants import (
    TIME_QUALITY_THRESHOLD,
    TIME_RATIO_THRESHOLD_LOW,
    TIME_RATIO_THRESHOLD_HIGH,
    TIME_RATIO_THRESHOLD_VERY_HIGH,
    TIME_QUALITY_FACTOR_GOOD,
    TIME_QUALITY_FACTOR_BAD,
    FOCUS_PENALTY_MULTIPLIER,
    HABIT_TYPE_SKILL,
    PROJECTION_MULTIPLIER_LOW,
    PROJECTION_MULTIPLIER_HIGH,
)
from backend.shared.date_utils import get_day_range, get_effective_date
from .repository import PointHistoryRepository
from .models import PointHistory
from .schemas import PointHistoryResponse, PointsCalculationResult


class PointsService:
    """Service for points calculation and management."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = PointHistoryRepository(db)

    def calculate_task_points(
        self,
        energy: int,
        time_spent: int,
        started_at: Optional[datetime],
        points_per_task_base: int,
        energy_mult_base: float,
        energy_mult_step: float,
        minutes_per_energy_unit: int,
        min_work_time_seconds: int
    ) -> PointsCalculationResult:
        """
        Calculate points for completing a task using Balanced Progress v2.0 formula.

        Args:
            energy: Task energy level (0-5)
            time_spent: Actual time spent in seconds
            started_at: When task was started (None = not tracked)
            points_per_task_base: Base points from settings
            energy_mult_base: Energy multiplier base from settings
            energy_mult_step: Energy multiplier step from settings
            minutes_per_energy_unit: Minutes per energy unit from settings
            min_work_time_seconds: Minimum work time from settings

        Returns:
            PointsCalculationResult with points and factors
        """
        base = points_per_task_base

        # 1. Energy Multiplier
        energy_multiplier = energy_mult_base + (energy * energy_mult_step)

        # 2. Time Quality Factor
        time_quality_factor = self._calculate_time_quality_factor(
            time_spent, energy, minutes_per_energy_unit, min_work_time_seconds
        )

        # 3. Focus Factor
        focus_factor = 1.0 if started_at else FOCUS_PENALTY_MULTIPLIER

        # Calculate total points
        total_points = base * energy_multiplier * time_quality_factor * focus_factor

        return PointsCalculationResult(
            points=max(1, int(total_points)),
            energy_multiplier=energy_multiplier,
            time_quality_factor=time_quality_factor,
            focus_factor=focus_factor
        )

    def _calculate_time_quality_factor(
        self,
        actual_time: int,
        energy: int,
        minutes_per_energy_unit: int,
        min_work_time_seconds: int
    ) -> float:
        """Calculate time quality factor based on actual vs expected time."""
        expected_time = energy * minutes_per_energy_unit * 60  # seconds

        # Suspiciously fast
        if actual_time < min_work_time_seconds:
            return TIME_QUALITY_THRESHOLD

        # No expected time (E0 tasks)
        if expected_time == 0:
            return 1.0

        # Calculate time ratio
        ratio = actual_time / expected_time

        if ratio < TIME_QUALITY_THRESHOLD:
            return TIME_RATIO_THRESHOLD_LOW  # Too fast
        elif ratio <= TIME_RATIO_THRESHOLD_HIGH:
            return 1.0  # Normal range
        elif ratio <= TIME_RATIO_THRESHOLD_VERY_HIGH:
            return TIME_QUALITY_FACTOR_GOOD  # Slightly slow
        else:
            return TIME_QUALITY_FACTOR_BAD  # Very slow

    def calculate_habit_points(
        self,
        habit_type: str,
        streak: int,
        points_per_habit_base: int,
        routine_points_fixed: int,
        streak_log_factor: float
    ) -> int:
        """
        Calculate points for completing a habit.

        Args:
            habit_type: "skill" or "routine"
            streak: Current streak count
            points_per_habit_base: Base points from settings
            routine_points_fixed: Fixed points for routine habits
            streak_log_factor: Streak log factor from settings

        Returns:
            Points earned (minimum 1)
        """
        # Routine habits get fixed points, no streak
        if habit_type != HABIT_TYPE_SKILL:
            return routine_points_fixed

        # Skill habits: base + streak bonus
        base = points_per_habit_base
        streak_bonus = 1 + math.log2(streak + 1) * streak_log_factor

        total = base * streak_bonus
        return max(1, int(total))

    def get_or_create_today_history(self, today: date) -> PointHistory:
        """
        Get or create point history for today.

        Args:
            today: Current effective date

        Returns:
            Point history for today
        """
        history = self.repo.get_by_date(today)

        if history:
            return history

        # Get most recent history entry to get cumulative total
        last_history = self.repo.get_most_recent(today)
        previous_total = last_history.cumulative_total if last_history else 0

        # Create new history entry
        history = PointHistory(
            date=today,
            cumulative_total=previous_total
        )
        return self.repo.create(history)

    def add_task_completion_points(
        self,
        today: date,
        task_id: int,
        description: str,
        is_habit: bool,
        points: int
    ) -> None:
        """
        Add points when a task/habit is completed.

        Args:
            today: Current effective date
            task_id: ID of completed task
            description: Task description
            is_habit: Whether it's a habit
            points: Points to add
        """
        history = self.get_or_create_today_history(today)

        # Update counters
        if is_habit:
            history.habits_completed += 1
        else:
            history.tasks_completed += 1

        # Add to earned points
        history.points_earned += points

        # Update daily and cumulative totals
        history.daily_total = (
            history.points_earned + history.points_bonus - history.points_penalty
        )
        history.cumulative_total += points

        # Store completion details
        details = {}
        if history.details:
            try:
                details = json.loads(history.details)
                if isinstance(details, list):
                    details = {"task_completions": details}
            except json.JSONDecodeError:
                details = {}

        if "task_completions" not in details:
            details["task_completions"] = []

        details["task_completions"].append({
            "task_id": task_id,
            "description": description,
            "is_habit": is_habit,
            "points": points,
            "time": datetime.now().isoformat()
        })
        history.details = json.dumps(details)

        self.repo.update(history)

    def save_planned_tasks(self, today: date, tasks_planned: int, task_details: List[dict]) -> None:
        """Save planned tasks info for penalty calculation later."""
        history = self.get_or_create_today_history(today)
        history.tasks_planned = tasks_planned

        details = {}
        if history.details:
            try:
                details = json.loads(history.details)
                if isinstance(details, list):
                    details = {"task_completions": details}
            except json.JSONDecodeError:
                details = {}

        details["planned_tasks"] = task_details
        history.details = json.dumps(details)

        self.repo.update(history)

    def get_current_points(self, today: date) -> int:
        """Get current total points."""
        history = self.get_or_create_today_history(today)
        return history.cumulative_total

    def get_history(self, days: int, from_date: date) -> List[PointHistoryResponse]:
        """Get point history for last N days."""
        history_list = self.repo.get_history(days, from_date)
        return [PointHistoryResponse.model_validate(h) for h in history_list]

    def get_history_by_date(self, target_date: date) -> Optional[PointHistory]:
        """Get history for a specific date (raw model for workflows)."""
        return self.repo.get_by_date(target_date)

    def update_history(self, history: PointHistory) -> None:
        """Update history (for workflows)."""
        self.repo.update(history)

    def calculate_projection(
        self,
        today: date,
        target_date: date,
        current_total: int
    ) -> dict:
        """
        Calculate point projections until target date.

        Args:
            today: Current effective date
            target_date: Date to project to
            current_total: Current cumulative total

        Returns:
            Dictionary with projections (min, avg, max)
        """
        # Get last 30 days average
        history = self.repo.get_history(30, today)

        if not history:
            avg_per_day = 0
        else:
            total_daily = sum(h.daily_total for h in history)
            avg_per_day = total_daily / len(history)

        days_until = (target_date - today).days

        if days_until <= 0:
            return {
                "current_total": current_total,
                "days_until": days_until,
                "avg_per_day": avg_per_day,
                "projection": current_total
            }

        # Calculate projections
        min_projection = current_total + int(
            avg_per_day * PROJECTION_MULTIPLIER_LOW * days_until
        )
        avg_projection = current_total + int(avg_per_day * days_until)
        max_projection = current_total + int(
            avg_per_day * PROJECTION_MULTIPLIER_HIGH * days_until
        )

        return {
            "current_total": current_total,
            "days_until": days_until,
            "avg_per_day": round(avg_per_day, 2),
            "min_projection": max(min_projection, current_total),
            "avg_projection": max(avg_projection, current_total),
            "max_projection": max(max_projection, current_total)
        }

    def propagate_cumulative_change(self, from_date: date, delta: int) -> None:
        """
        Propagate cumulative total change to all subsequent days.

        Args:
            from_date: Date from which to start propagating
            delta: Amount to add (negative for subtract)
        """
        subsequent_days = self.repo.get_all_after(from_date)
        for day_history in subsequent_days:
            day_history.cumulative_total += delta
        self.db.commit()

    # Alias methods for workflows
    def get_history_for_date(self, target_date: date) -> Optional[PointHistory]:
        """Alias for get_history_by_date."""
        return self.get_history_by_date(target_date)

    def get_history_data(self, target_date: date) -> Optional[dict]:
        """Get history data as dict for workflows."""
        history = self.repo.get_by_date(target_date)
        if not history:
            return None
        return {
            "date": history.date,
            "points_earned": history.points_earned,
            "points_penalty": history.points_penalty,
            "points_bonus": history.points_bonus,
            "daily_total": history.daily_total,
            "cumulative_total": history.cumulative_total,
            "tasks_completed": history.tasks_completed,
            "habits_completed": history.habits_completed,
            "tasks_planned": history.tasks_planned,
            "completion_rate": history.completion_rate,
            "penalty_streak": history.penalty_streak,
            "details": history.details,
        }

    def get_current_points(self) -> int:
        """Get current total points (uses effective date internally)."""
        # This needs to be called with no arguments for workflow compatibility
        # Find the most recent history entry
        history = self.repo.get_most_recent(date.today())
        return history.cumulative_total if history else 0
