"""
Penalty calculation service.
Handles all penalty-related calculations including idle, incomplete day, and missed habits.
"""
from datetime import date, timedelta
from typing import List
from sqlalchemy.orm import Session

from backend.models import Settings, PointHistory, Task
from backend.repositories.task_repository import TaskRepository
from backend.repositories.points_repository import (
    PointHistoryRepository, RestDayRepository
)
from backend.repositories.settings_repository import SettingsRepository
from backend.services.date_service import DateService
from backend.constants import HABIT_TYPE_SKILL, ROUTINE_PENALTY_MULTIPLIER


class PenaltyService:
    """Service for penalty calculation"""

    def __init__(self, db: Session):
        self.db = db
        self.task_repo = TaskRepository()
        self.history_repo = PointHistoryRepository()
        self.rest_day_repo = RestDayRepository()
        self.settings_repo = SettingsRepository()
        self.date_service = DateService()

    def finalize_day_penalties(self, target_date: date) -> dict:
        """
        Finalize penalties for a specific date using Balanced Progress v2.0 formula.

        Penalty types:
        1. Idle Penalty: Applied when 0 tasks AND 0 habits completed
        2. Incomplete Day Penalty: % of missed task potential
        3. Missed Habit Penalty: Points for each missed habit

        Args:
            target_date: Date to finalize penalties for

        Returns:
            Dictionary with penalty information
        """
        # Check if this is a rest day - no penalties
        if self._is_rest_day(target_date):
            return self._rest_day_result()

        settings = self.settings_repo.get(self.db)
        day_history = self.history_repo.get_by_date(self.db, target_date)

        # If no history for that day, no penalties
        if not day_history:
            return self._no_history_result()

        # Update completion counts
        self._update_completion_counts(day_history, target_date)

        # Calculate penalties
        penalty = 0
        missed_task_potential = 0

        # 1. Idle Penalty
        penalty += self._calculate_idle_penalty(day_history, settings)

        # 2. Incomplete Day Penalty
        incomplete_penalty, missed_task_potential = self._calculate_incomplete_penalty(
            day_history, target_date, settings
        )
        penalty += incomplete_penalty

        # 3. Daily Consistency Bonus
        self._apply_consistency_bonus(day_history, settings)

        # 4. Missed Habits Penalty
        missed_habits, habits_penalty = self._calculate_missed_habits_penalty(
            target_date, day_history, settings
        )
        penalty += habits_penalty

        # 5. Progressive Penalty Multiplier
        penalty = self._apply_progressive_multiplier(
            penalty, target_date, day_history, settings
        )

        # Apply final penalties and bonuses
        self._apply_final_penalties(day_history, penalty)

        return {
            "penalty": penalty,
            "completion_rate": day_history.completion_rate,
            "tasks_completed": day_history.tasks_completed,
            "tasks_planned": day_history.tasks_planned,
            "missed_habits": missed_habits,
            "missed_task_potential": missed_task_potential
        }

    def _is_rest_day(self, target_date: date) -> bool:
        """Check if target date is a rest day"""
        rest_day = self.rest_day_repo.get_by_date(self.db, target_date)
        return rest_day is not None

    def _rest_day_result(self) -> dict:
        """Return result for rest day (no penalties)"""
        return {
            "penalty": 0,
            "completion_rate": 1.0,
            "tasks_completed": 0,
            "tasks_planned": 0,
            "missed_habits": 0,
            "is_rest_day": True
        }

    def _no_history_result(self) -> dict:
        """Return result when no history exists"""
        return {
            "penalty": 0,
            "completion_rate": 0,
            "tasks_completed": 0,
            "tasks_planned": 0,
            "missed_habits": 0
        }

    def _update_completion_counts(
        self,
        day_history: PointHistory,
        target_date: date
    ) -> None:
        """Update completion counts in history if not already set"""
        day_start, day_end = self.date_service.get_day_range(target_date)

        # Count completed tasks
        if day_history.tasks_completed == 0:
            tasks_completed = self.task_repo.get_completed_count(
                self.db, day_start, day_end, is_habit=False
            )
            day_history.tasks_completed = tasks_completed

        # Count completed habits
        if day_history.habits_completed == 0:
            habits_completed = self.task_repo.get_completed_count(
                self.db, day_start, day_end, is_habit=True
            )
            day_history.habits_completed = habits_completed

        # Set tasks_planned if not tracked
        if day_history.tasks_planned == 0:
            day_history.tasks_planned = max(day_history.tasks_completed, 1)

    def _calculate_idle_penalty(
        self,
        day_history: PointHistory,
        settings: Settings
    ) -> int:
        """
        Calculate idle penalty.
        Only applies if BOTH tasks and habits are 0.
        """
        if day_history.tasks_completed == 0 and day_history.habits_completed == 0:
            return settings.idle_penalty
        return 0

    def _calculate_incomplete_penalty(
        self,
        day_history: PointHistory,
        target_date: date,
        settings: Settings
    ) -> tuple[int, int]:
        """
        Calculate incomplete day penalty based on missed task potential.

        Returns:
            Tuple of (penalty, missed_task_potential)
        """
        if day_history.tasks_planned == 0:
            return 0, 0

        # Calculate completion rate
        completion_rate = min(
            day_history.tasks_completed / day_history.tasks_planned, 1.0
        )
        day_history.completion_rate = completion_rate

        # Get incomplete tasks from target date using saved planned_tasks info
        day_start, day_end = self.date_service.get_day_range(target_date)

        # Load planned tasks from details
        import json
        planned_tasks_info = []
        if day_history.details:
            try:
                details = json.loads(day_history.details)
                planned_tasks_info = details.get("planned_tasks", [])
            except (json.JSONDecodeError, KeyError):
                planned_tasks_info = []

        if not planned_tasks_info:
            # No planned tasks info - fallback to average
            incomplete_count = day_history.tasks_planned - day_history.tasks_completed
            if incomplete_count <= 0:
                return 0, 0

            energy_mult = settings.energy_mult_base + (3 * settings.energy_mult_step)
            potential_per_task = settings.points_per_task_base * energy_mult
            missed_task_potential = int(incomplete_count * potential_per_task)

            penalty = int(missed_task_potential * settings.incomplete_penalty_percent)
            return penalty, missed_task_potential

        # Calculate missed potential using REAL task energy from planned_tasks
        missed_task_potential = 0
        incomplete_count = 0

        for task_info in planned_tasks_info:
            task_id = task_info.get("task_id")
            task_energy = task_info.get("energy", 3)

            # Check if task was completed
            task = self.task_repo.get_by_id(self.db, task_id)
            if not task or task.status != "completed":
                # Task was not completed - calculate its potential
                energy_mult = settings.energy_mult_base + (task_energy * settings.energy_mult_step)
                potential = settings.points_per_task_base * energy_mult
                missed_task_potential += potential
                incomplete_count += 1

        if missed_task_potential == 0:
            return 0, 0

        # Calculate penalty
        penalty = int(missed_task_potential * settings.incomplete_penalty_percent)
        return penalty, int(missed_task_potential)

    def _apply_consistency_bonus(
        self,
        day_history: PointHistory,
        settings: Settings
    ) -> None:
        """Apply daily consistency bonus based on completion rate"""
        if day_history.points_earned <= 0:
            return

        completion_rate = day_history.completion_rate

        if completion_rate >= 1.0:
            # 100% completion: full bonus
            day_history.points_bonus = int(
                day_history.points_earned * settings.completion_bonus_full
            )
        elif completion_rate >= 0.8:
            # 80%+ completion: good bonus
            day_history.points_bonus = int(
                day_history.points_earned * settings.completion_bonus_good
            )

    def _calculate_missed_habits_penalty(
        self,
        target_date: date,
        day_history: PointHistory,
        settings: Settings
    ) -> tuple[List[Task], int]:
        """
        Calculate penalty for missed habits.

        Returns:
            Tuple of (missed_habits_list, penalty)
        """
        day_start, day_end = self.date_service.get_day_range(target_date)

        # Count habits due on target date
        habits_due = self.task_repo.count_habits_due_in_range(
            self.db, day_start, day_end
        )

        missed_habits_count = max(0, habits_due - day_history.habits_completed)

        if missed_habits_count == 0:
            return [], 0

        # Get missed habits
        missed_habits = self.task_repo.get_missed_habits(
            self.db, day_start, day_end
        )

        # Calculate penalty
        penalty = 0
        for habit in missed_habits:
            if habit.habit_type == HABIT_TYPE_SKILL:
                # Full penalty for skill habits
                penalty += settings.missed_habit_penalty_base
            else:
                # Reduced penalty for routines
                penalty += int(
                    settings.missed_habit_penalty_base * ROUTINE_PENALTY_MULTIPLIER
                )

        return missed_habits, penalty

    def _apply_progressive_multiplier(
        self,
        penalty: int,
        target_date: date,
        day_history: PointHistory,
        settings: Settings
    ) -> int:
        """
        Apply progressive penalty multiplier based on streak.

        Also handles penalty streak reset logic.

        Returns:
            Final penalty with multiplier applied
        """
        yesterday_date = target_date - timedelta(days=1)
        yesterday_history = self.history_repo.get_by_date(self.db, yesterday_date)

        if penalty > 0:
            # Got penalties today - increment streak
            if yesterday_history and yesterday_history.penalty_streak > 0:
                day_history.penalty_streak = yesterday_history.penalty_streak + 1
            else:
                day_history.penalty_streak = 1

            # Apply progressive penalty with cap
            # Formula: 1 + min(penalty_streak × factor, max - 1)
            progressive_multiplier = 1 + min(
                day_history.penalty_streak * settings.progressive_penalty_factor,
                settings.progressive_penalty_max - 1
            )
            return int(penalty * progressive_multiplier)
        else:
            # No penalties today - check if we should reset streak
            self._update_penalty_streak(
                day_history, yesterday_history, settings, yesterday_date
            )
            return penalty

    def _update_penalty_streak(
        self,
        day_history: PointHistory,
        yesterday_history: PointHistory,
        settings: Settings,
        yesterday_date: date
    ) -> None:
        """Update penalty streak when no penalties occurred"""
        if not yesterday_history:
            day_history.penalty_streak = 0
            return

        days_without_penalty = 1  # Today has no penalty

        # Count consecutive days without penalty
        check_date = yesterday_date
        for _ in range(settings.penalty_streak_reset_days - 1):
            hist = self.history_repo.get_by_date(self.db, check_date)
            if hist and hist.points_penalty == 0:
                days_without_penalty += 1
                check_date -= timedelta(days=1)
            else:
                break

        if days_without_penalty >= settings.penalty_streak_reset_days:
            day_history.penalty_streak = 0  # Reset streak
        else:
            day_history.penalty_streak = yesterday_history.penalty_streak

    def _apply_final_penalties(
        self,
        day_history: PointHistory,
        penalty: int
    ) -> None:
        """Apply final penalties and bonuses to history"""
        day_history.points_penalty = penalty
        day_history.daily_total = (
            day_history.points_earned +
            day_history.points_bonus -
            day_history.points_penalty
        )

        # Update cumulative total (never goes below 0)
        # NOTE: points_earned were already added to cumulative_total when tasks were completed
        # So we only add the bonus and subtract penalties here
        net_change = day_history.points_bonus - penalty
        day_history.cumulative_total = max(
            0, day_history.cumulative_total + net_change
        )

        self.history_repo.update(self.db, day_history)

    def calculate_daily_penalties(self) -> dict:
        """
        Calculate penalties for YESTERDAY.
        Called during Roll for new day.

        Returns:
            Dictionary with penalty information
        """
        settings = self.settings_repo.get(self.db)
        today = self.date_service.get_effective_date(settings)
        yesterday = today - timedelta(days=1)
        return self.finalize_day_penalties(yesterday)
