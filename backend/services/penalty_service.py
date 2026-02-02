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
        # First, ensure all previous days are finalized (handles skipped rolls)
        self._finalize_missing_days(target_date)

        # Now finalize the target date
        return self._finalize_single_day(target_date)

    def _finalize_missing_days(self, target_date: date) -> None:
        """
        Finalize any missing days between the last finalized day and target_date.

        This handles the case where roll was skipped for one or more days,
        ensuring penalty_streak is calculated correctly and missed habits are penalized.

        Key behavior:
        - Creates history records for days where user didn't open the app
        - Counts habits that were due on each day as missed
        - Applies idle penalty + missed habits penalty for skipped days
        - Rolls habits forward after each day, so they can be counted again for next day
        """
        import json

        settings = self.settings_repo.get(self.db)
        yesterday = target_date - timedelta(days=1)

        # First, find the oldest day that needs processing
        # by looking back until we find a finalized day
        oldest_unfinalized = None
        check_date = yesterday

        for _ in range(14):
            history = self.history_repo.get_by_date(self.db, check_date)

            if history:
                # Check if this day is already finalized
                if history.points_penalty > 0:
                    break

                if history.details:
                    try:
                        details = json.loads(history.details)
                        if "penalty_breakdown" in details:
                            break
                    except json.JSONDecodeError:
                        pass

                # History exists but not finalized
                oldest_unfinalized = check_date
            else:
                # No history - check if we should process this day
                day_start, day_end = self.date_service.get_day_range(check_date, settings)
                habits_due = self.task_repo.count_habits_due_in_range(self.db, day_start, day_end)

                if habits_due > 0:
                    oldest_unfinalized = check_date
                elif settings.last_roll_date and check_date < settings.last_roll_date:
                    break

            check_date -= timedelta(days=1)

        if oldest_unfinalized is None:
            return

        # Process days from oldest to newest (yesterday)
        # This ensures habits get rolled forward properly
        current_date = oldest_unfinalized
        while current_date <= yesterday:
            # Re-check if this day needs processing (habits may have been rolled forward)
            history = self.history_repo.get_by_date(self.db, current_date)

            needs_processing = False
            if history:
                if history.points_penalty == 0 and not self._is_day_finalized(history):
                    needs_processing = True
            else:
                # No history - check for habits due
                day_start, day_end = self.date_service.get_day_range(current_date, settings)
                habits_due = self.task_repo.count_habits_due_in_range(self.db, day_start, day_end)
                if habits_due > 0:
                    needs_processing = True

            if needs_processing:
                self._finalize_or_create_day(current_date, settings)

            current_date += timedelta(days=1)

    def _is_day_finalized(self, history: PointHistory) -> bool:
        """Check if a day's history has been finalized (has penalty breakdown)"""
        import json
        if not history or not history.details:
            return False
        try:
            details = json.loads(history.details)
            return "penalty_breakdown" in details
        except json.JSONDecodeError:
            return False

    def _finalize_or_create_day(self, target_date: date, settings: Settings) -> dict:
        """
        Finalize a day, creating history if it doesn't exist.

        This handles days where user didn't open the app but had habits due.
        """
        import json

        # Check if rest day
        if self._is_rest_day(target_date):
            return self._rest_day_result()

        day_history = self.history_repo.get_by_date(self.db, target_date)

        if day_history:
            # History exists - use normal finalization
            return self._finalize_single_day(target_date)

        # No history exists - create one for this missed day
        # First, get the previous day's cumulative total
        prev_date = target_date - timedelta(days=1)
        prev_history = self.history_repo.get_by_date(self.db, prev_date)

        if not prev_history:
            # Look for most recent history before this date
            from backend.models import PointHistory
            prev_history = self.db.query(PointHistory).filter(
                PointHistory.date < target_date
            ).order_by(PointHistory.date.desc()).first()

        previous_cumulative = prev_history.cumulative_total if prev_history else 0

        # Create new history entry for this missed day
        from backend.models import PointHistory
        day_history = PointHistory(
            date=target_date,
            points_earned=0,
            points_penalty=0,
            points_bonus=0,
            daily_total=0,
            cumulative_total=previous_cumulative,
            tasks_completed=0,
            habits_completed=0,
            tasks_planned=0,
            completion_rate=0.0
        )
        self.history_repo.create(self.db, day_history)

        # Now calculate penalties for this day
        # 1. Idle Penalty (always applies for missed days)
        idle_penalty = settings.idle_penalty

        # 2. Missed Habits Penalty
        day_start, day_end = self.date_service.get_day_range(target_date, settings)
        missed_habits = self.task_repo.get_missed_habits(self.db, day_start, day_end)

        habits_penalty = 0
        missed_habits_details = []
        for habit in missed_habits:
            if habit.habit_type == HABIT_TYPE_SKILL:
                habit_penalty = settings.missed_habit_penalty_base
            else:
                habit_penalty = int(settings.missed_habit_penalty_base * ROUTINE_PENALTY_MULTIPLIER)
            habits_penalty += habit_penalty
            missed_habits_details.append({
                "id": habit.id,
                "description": habit.description,
                "habit_type": habit.habit_type,
                "penalty": habit_penalty
            })

        base_penalty = idle_penalty + habits_penalty

        # 3. Progressive Penalty Multiplier
        yesterday_streak = self._get_effective_penalty_streak(target_date - timedelta(days=1), settings)
        if yesterday_streak > 0:
            day_history.penalty_streak = yesterday_streak + 1
        else:
            day_history.penalty_streak = 1

        progressive_multiplier = 1 + min(
            day_history.penalty_streak * settings.progressive_penalty_factor,
            settings.progressive_penalty_max - 1
        )

        total_penalty = int(base_penalty * progressive_multiplier)

        # Apply penalties
        day_history.points_penalty = total_penalty
        day_history.daily_total = -total_penalty
        day_history.cumulative_total = max(0, previous_cumulative - total_penalty)

        # Save penalty breakdown
        details = {
            "penalty_breakdown": {
                "idle_penalty": idle_penalty,
                "incomplete_penalty": 0,
                "missed_habits_penalty": habits_penalty,
                "progressive_multiplier": progressive_multiplier,
                "penalty_streak": day_history.penalty_streak,
                "total_penalty": total_penalty,
                "missed_habits": missed_habits_details,
                "incomplete_tasks": [],
                "auto_finalized": True  # Mark that this was auto-finalized for a missed day
            }
        }
        day_history.details = json.dumps(details)

        self.history_repo.update(self.db, day_history)

        # Propagate cumulative change to subsequent days
        if total_penalty > 0:
            self._propagate_cumulative_change(target_date, -total_penalty)

        # Roll forward the missed habits to the next day
        # This is critical for daily habits - they should be counted as missed
        # on each day they were due, not just the first missed day
        self._roll_forward_missed_habits(missed_habits, target_date)

        return {
            "penalty": total_penalty,
            "completion_rate": 0,
            "tasks_completed": 0,
            "tasks_planned": 0,
            "missed_habits": len(missed_habits_details),
            "auto_finalized": True
        }

    def _roll_forward_missed_habits(self, missed_habits: list, from_date: date) -> None:
        """
        Roll forward missed habits to their next occurrence.

        This ensures that recurring habits are counted as missed on each day they were due,
        not just the first missed day. For example, a daily habit missed on Mon, Tue, Wed
        should incur penalties for all three days.

        Args:
            missed_habits: List of Task objects that were missed
            from_date: The date these habits were missed on
        """
        from datetime import datetime
        from backend.models import Task
        from backend.constants import RECURRENCE_NONE

        for habit in missed_habits:
            if habit.recurrence_type == RECURRENCE_NONE:
                # Non-recurring habits: just delete them (they were missed and won't recur)
                self.task_repo.delete(self.db, habit)
                continue

            # Calculate next due date for recurring habits
            next_due = self.date_service.calculate_next_due_date(habit, from_date)
            if not next_due:
                self.task_repo.delete(self.db, habit)
                continue

            # Create next occurrence of the habit
            next_habit = Task(
                description=habit.description,
                project=habit.project,
                priority=habit.priority,
                energy=habit.energy,
                is_habit=True,
                is_today=False,
                due_date=datetime.combine(next_due, datetime.min.time()),
                recurrence_type=habit.recurrence_type,
                recurrence_interval=habit.recurrence_interval,
                recurrence_days=habit.recurrence_days,
                habit_type=habit.habit_type,
                streak=0,  # Reset streak since habit was missed
                last_completed_date=habit.last_completed_date,
                daily_target=habit.daily_target or 1,
                daily_completed=0
            )
            next_habit.calculate_urgency()
            self.task_repo.create(self.db, next_habit)

            # Delete the old missed habit
            self.task_repo.delete(self.db, habit)

    def _finalize_single_day(self, target_date: date) -> dict:
        """Internal finalization for a single day (no recursion check)"""
        # Check if this is a rest day - no penalties
        if self._is_rest_day(target_date):
            return self._rest_day_result()

        settings = self.settings_repo.get(self.db)
        day_history = self.history_repo.get_by_date(self.db, target_date)

        # If no history for that day, no penalties
        if not day_history:
            return self._no_history_result()

        # Idempotency: if penalties already applied, return existing values
        if day_history.points_penalty > 0 or day_history.completion_rate > 0:
            return {
                "penalty": day_history.points_penalty,
                "completion_rate": day_history.completion_rate,
                "tasks_completed": day_history.tasks_completed,
                "tasks_planned": day_history.tasks_planned,
                "missed_habits": 0,
                "already_finalized": True
            }

        # Update completion counts
        self._update_completion_counts(day_history, target_date, settings)

        # Calculate penalties
        penalty = 0
        missed_task_potential = 0

        # 1. Idle Penalty
        idle_penalty = self._calculate_idle_penalty(day_history, settings)
        penalty += idle_penalty

        # 2. Incomplete Day Penalty
        incomplete_penalty, missed_task_potential, incomplete_tasks = self._calculate_incomplete_penalty(
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

        # Store pre-multiplier penalty for breakdown
        base_penalty = penalty

        # 5. Progressive Penalty Multiplier
        penalty, progressive_multiplier = self._apply_progressive_multiplier(
            penalty, target_date, day_history, settings
        )

        # Apply final penalties and bonuses
        self._apply_final_penalties(day_history, penalty)

        # Save penalty breakdown to history details
        self._save_penalty_breakdown(
            day_history,
            idle_penalty,
            incomplete_penalty,
            habits_penalty,
            progressive_multiplier,
            penalty,
            missed_habits,
            incomplete_tasks
        )

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
        target_date: date,
        settings: Settings
    ) -> None:
        """Update completion counts in history if not already set"""
        day_start, day_end = self.date_service.get_day_range(target_date, settings)

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

        # Note: tasks_planned is set during roll in task_service.py
        # If it's 0, it means no tasks were planned - don't override

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
    ) -> tuple[int, int, list]:
        """
        Calculate incomplete day penalty based on missed task potential.

        Returns:
            Tuple of (penalty, missed_task_potential, incomplete_tasks_details)
        """
        if day_history.tasks_planned == 0:
            return 0, 0, []

        # Calculate completion rate
        completion_rate = min(
            day_history.tasks_completed / day_history.tasks_planned, 1.0
        )
        day_history.completion_rate = completion_rate

        # Get incomplete tasks from target date using saved planned_tasks info
        day_start, day_end = self.date_service.get_day_range(target_date, settings)

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
                return 0, 0, []

            energy_mult = settings.energy_mult_base + (3 * settings.energy_mult_step)
            potential_per_task = settings.points_per_task_base * energy_mult
            missed_task_potential = int(incomplete_count * potential_per_task)

            penalty = int(missed_task_potential * settings.incomplete_penalty_percent)
            return penalty, missed_task_potential, []

        # Calculate missed potential using REAL task energy from planned_tasks
        missed_task_potential = 0
        incomplete_tasks_details = []

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
                incomplete_tasks_details.append({
                    "id": task_id,
                    "description": task.description if task else task_info.get("description", "Unknown task"),
                    "energy": task_energy,
                    "potential": int(potential)
                })

        if missed_task_potential == 0:
            return 0, 0, []

        # Calculate penalty
        penalty = int(missed_task_potential * settings.incomplete_penalty_percent)
        return penalty, int(missed_task_potential), incomplete_tasks_details

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
    ) -> tuple[list, int]:
        """
        Calculate penalty for missed habits.

        Returns:
            Tuple of (missed_habits_details, penalty)
            missed_habits_details is a list of dicts with habit info and penalty
        """
        day_start, day_end = self.date_service.get_day_range(target_date, settings)

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

        # Calculate penalty and build details list
        penalty = 0
        missed_habits_details = []
        for habit in missed_habits:
            if habit.habit_type == HABIT_TYPE_SKILL:
                # Full penalty for skill habits
                habit_penalty = settings.missed_habit_penalty_base
            else:
                # Reduced penalty for routines
                habit_penalty = int(
                    settings.missed_habit_penalty_base * ROUTINE_PENALTY_MULTIPLIER
                )
            penalty += habit_penalty
            missed_habits_details.append({
                "id": habit.id,
                "description": habit.description,
                "habit_type": habit.habit_type,
                "penalty": habit_penalty
            })

        return missed_habits_details, penalty

    def _apply_progressive_multiplier(
        self,
        penalty: int,
        target_date: date,
        day_history: PointHistory,
        settings: Settings
    ) -> tuple[int, float]:
        """
        Apply progressive penalty multiplier based on streak.

        Also handles penalty streak reset logic.

        Returns:
            Tuple of (final penalty with multiplier, actual multiplier used)
        """
        yesterday_date = target_date - timedelta(days=1)
        yesterday_history = self.history_repo.get_by_date(self.db, yesterday_date)

        if penalty > 0:
            # Got penalties today - calculate streak
            # We need to check if yesterday had penalties (points_penalty > 0)
            # Not just penalty_streak > 0, because yesterday might not be finalized yet
            yesterday_streak = self._get_effective_penalty_streak(yesterday_date, settings)

            if yesterday_streak > 0:
                day_history.penalty_streak = yesterday_streak + 1
            else:
                day_history.penalty_streak = 1

            # Apply progressive penalty with cap
            # Formula: 1 + min(penalty_streak × factor, max - 1)
            progressive_multiplier = 1 + min(
                day_history.penalty_streak * settings.progressive_penalty_factor,
                settings.progressive_penalty_max - 1
            )
            return int(penalty * progressive_multiplier), progressive_multiplier
        else:
            # No penalties today - check if we should reset streak
            self._update_penalty_streak(
                day_history, yesterday_history, settings, yesterday_date
            )
            return penalty, 1.0

    def _get_effective_penalty_streak(self, check_date: date, settings: Settings) -> int:
        """
        Get the effective penalty streak for a date, even if that day wasn't finalized.

        This handles the case where roll was skipped for one or more days.
        We count backwards to find how many consecutive days had penalties.
        """
        history = self.history_repo.get_by_date(self.db, check_date)

        if not history:
            return 0

        # If the day has penalty_streak set (finalized), use it directly
        # This is the most reliable source as it was calculated correctly
        if history.penalty_streak > 0:
            return history.penalty_streak

        # If the day has penalties but penalty_streak is 0, it might be unfinalized
        # or it's the first day with penalties
        if history.points_penalty > 0:
            # Day has penalties but no streak set - count backwards
            streak = 1  # At least this day has penalties
            current_date = check_date - timedelta(days=1)

            # Look back up to 30 days
            for _ in range(30):
                prev_history = self.history_repo.get_by_date(self.db, current_date)

                if not prev_history:
                    break

                # Use penalty_streak if available
                if prev_history.penalty_streak > 0:
                    return streak + prev_history.penalty_streak

                # Otherwise check if day had penalties
                if prev_history.points_penalty > 0:
                    streak += 1
                    current_date -= timedelta(days=1)
                else:
                    break

            return streak

        # No penalties on this day
        return 0

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
        old_cumulative = day_history.cumulative_total
        day_history.cumulative_total = max(
            0, day_history.cumulative_total + net_change
        )

        self.history_repo.update(self.db, day_history)

        # Propagate the change to subsequent days if their history already exists
        # This handles the case when user opens app before roll - today's history
        # was created with old cumulative_total before penalties were applied
        if net_change != 0:
            cumulative_delta = day_history.cumulative_total - old_cumulative
            self._propagate_cumulative_change(day_history.date, cumulative_delta)

    def _propagate_cumulative_change(self, from_date: date, delta: int) -> None:
        """Propagate cumulative_total change to all days after from_date"""
        from backend.models import PointHistory

        # Get all history entries after from_date
        subsequent_histories = self.db.query(PointHistory).filter(
            PointHistory.date > from_date
        ).order_by(PointHistory.date.asc()).all()

        for history in subsequent_histories:
            history.cumulative_total = max(0, history.cumulative_total + delta)
            self.history_repo.update(self.db, history)

    def _save_penalty_breakdown(
        self,
        day_history: PointHistory,
        idle_penalty: int,
        incomplete_penalty: int,
        habits_penalty: int,
        progressive_multiplier: float,
        total_penalty: int,
        missed_habits_details: list = None,
        incomplete_tasks_details: list = None
    ) -> None:
        """Save detailed penalty breakdown to history details"""
        import json

        # Load existing details (as dict)
        details = {}
        if day_history.details:
            try:
                details = json.loads(day_history.details)
                # Handle legacy format where details was a list
                if isinstance(details, list):
                    details = {"task_completions": details}
            except json.JSONDecodeError:
                details = {}

        # Add penalty breakdown
        details["penalty_breakdown"] = {
            "idle_penalty": idle_penalty,
            "incomplete_penalty": incomplete_penalty,
            "missed_habits_penalty": habits_penalty,
            "progressive_multiplier": progressive_multiplier,
            "penalty_streak": day_history.penalty_streak,
            "total_penalty": total_penalty,
            "missed_habits": missed_habits_details or [],
            "incomplete_tasks": incomplete_tasks_details or []
        }

        # Save back to history
        day_history.details = json.dumps(details)
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
