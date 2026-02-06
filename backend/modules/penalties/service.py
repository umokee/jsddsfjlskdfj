"""
Penalty calculation service.
Handles all penalty-related calculations including idle, incomplete day, and missed habits.

This service receives data from other modules through parameters (via workflows),
following the modular monolith architecture where modules don't import each other.
"""
import json
from datetime import date, timedelta
from typing import List, Optional, Callable
from sqlalchemy.orm import Session

from backend.shared.constants import HABIT_TYPE_SKILL, ROUTINE_PENALTY_MULTIPLIER
from backend.shared.date_utils import get_day_range
from backend.modules.points.models import PointHistory
from backend.modules.points.repository import PointHistoryRepository


class PenaltyService:
    """Service for penalty calculation."""

    def __init__(self, db: Session):
        self.db = db
        self.history_repo = PointHistoryRepository(db)

    def finalize_day_penalties(
        self,
        target_date: date,
        is_rest_day: bool,
        day_start_enabled: bool,
        day_start_time: str,
        settings_data: dict,
        get_completed_count: Callable,
        get_missed_habits: Callable,
        count_habits_due: Callable,
        roll_forward_habit: Callable,
    ) -> dict:
        """
        Finalize penalties for a specific date.

        Args:
            target_date: Date to finalize penalties for
            is_rest_day: Whether this is a rest day
            day_start_enabled: Whether custom day start is enabled
            day_start_time: Day start time string
            settings_data: Dict with penalty settings
            get_completed_count: Function(start, end, is_habit) -> int
            get_missed_habits: Function(start, end) -> List[dict]
            count_habits_due: Function(start, end) -> int
            roll_forward_habit: Function(habit_data, from_date) -> None

        Returns:
            Dictionary with penalty information
        """
        # Rest day - no penalties
        if is_rest_day:
            return self._rest_day_result()

        day_history = self.history_repo.get_by_date(target_date)

        # If no history for that day, create it or return no penalties
        if not day_history:
            return self._handle_no_history(
                target_date,
                day_start_enabled,
                day_start_time,
                settings_data,
                get_missed_habits,
                count_habits_due,
                roll_forward_habit,
            )

        # Idempotency: if penalties already applied, return existing values
        if day_history.points_penalty > 0 or self._is_day_finalized(day_history):
            return {
                "penalty": day_history.points_penalty,
                "completion_rate": day_history.completion_rate,
                "tasks_completed": day_history.tasks_completed,
                "tasks_planned": day_history.tasks_planned,
                "missed_habits": 0,
                "already_finalized": True
            }

        day_start, day_end = get_day_range(target_date, day_start_enabled, day_start_time)

        # Update completion counts
        self._update_completion_counts(
            day_history, day_start, day_end, get_completed_count
        )

        # Calculate penalties
        penalty = 0
        missed_task_potential = 0

        # 1. Idle Penalty
        idle_penalty = self._calculate_idle_penalty(day_history, settings_data)
        penalty += idle_penalty

        # 2. Incomplete Day Penalty
        incomplete_penalty, missed_task_potential, incomplete_tasks = (
            self._calculate_incomplete_penalty(day_history, settings_data)
        )
        penalty += incomplete_penalty

        # 3. Daily Consistency Bonus
        self._apply_consistency_bonus(day_history, settings_data)

        # 4. Missed Habits Penalty
        missed_habits_details, habits_penalty = self._calculate_missed_habits_penalty(
            day_start, day_end, day_history, settings_data, get_missed_habits
        )
        penalty += habits_penalty

        # 5. Progressive Penalty Multiplier
        penalty, progressive_multiplier = self._apply_progressive_multiplier(
            penalty, target_date, day_history, settings_data
        )

        # Apply final penalties
        self._apply_final_penalties(day_history, penalty)

        # Save penalty breakdown
        self._save_penalty_breakdown(
            day_history,
            idle_penalty,
            incomplete_penalty,
            habits_penalty,
            progressive_multiplier,
            penalty,
            missed_habits_details,
            incomplete_tasks
        )

        return {
            "penalty": penalty,
            "completion_rate": day_history.completion_rate,
            "tasks_completed": day_history.tasks_completed,
            "tasks_planned": day_history.tasks_planned,
            "missed_habits": len(missed_habits_details),
            "missed_task_potential": missed_task_potential
        }

    def _handle_no_history(
        self,
        target_date: date,
        day_start_enabled: bool,
        day_start_time: str,
        settings_data: dict,
        get_missed_habits: Callable,
        count_habits_due: Callable,
        roll_forward_habit: Callable,
    ) -> dict:
        """Handle case where no history exists for the day."""
        day_start, day_end = get_day_range(target_date, day_start_enabled, day_start_time)

        # Check if there were habits due
        habits_due = count_habits_due(day_start, day_end)
        if habits_due == 0:
            return self._no_history_result()

        # Get previous cumulative total
        prev_history = self.history_repo.get_most_recent(target_date)
        previous_cumulative = prev_history.cumulative_total if prev_history else 0

        # Create history for missed day
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
        self.history_repo.create(day_history)

        # Idle penalty
        idle_penalty = settings_data.get("idle_penalty", 30)

        # Missed habits penalty
        missed_habits = get_missed_habits(day_start, day_end)
        habits_penalty = 0
        missed_habits_details = []

        for habit in missed_habits:
            if habit.get("habit_type") == HABIT_TYPE_SKILL:
                habit_penalty = settings_data.get("missed_habit_penalty_base", 15)
            else:
                habit_penalty = int(
                    settings_data.get("missed_habit_penalty_base", 15) * ROUTINE_PENALTY_MULTIPLIER
                )
            habits_penalty += habit_penalty
            missed_habits_details.append({
                "id": habit.get("id"),
                "description": habit.get("description"),
                "habit_type": habit.get("habit_type"),
                "penalty": habit_penalty
            })

            # Roll forward the habit
            roll_forward_habit(habit, target_date)

        base_penalty = idle_penalty + habits_penalty

        # Progressive multiplier
        yesterday_streak = self._get_effective_penalty_streak(
            target_date - timedelta(days=1)
        )
        day_history.penalty_streak = yesterday_streak + 1 if yesterday_streak > 0 else 1

        progressive_multiplier = 1 + min(
            day_history.penalty_streak * settings_data.get("progressive_penalty_factor", 0.1),
            settings_data.get("progressive_penalty_max", 1.5) - 1
        )

        total_penalty = int(base_penalty * progressive_multiplier)

        # Apply penalties
        day_history.points_penalty = total_penalty
        day_history.daily_total = -total_penalty
        day_history.cumulative_total = max(0, previous_cumulative - total_penalty)

        # Save breakdown
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
                "auto_finalized": True
            }
        }
        day_history.details = json.dumps(details)
        self.history_repo.update(day_history)

        # Propagate to subsequent days (use clamped delta, not raw penalty)
        cumulative_delta = day_history.cumulative_total - previous_cumulative
        if cumulative_delta != 0:
            self._propagate_cumulative_change(target_date, cumulative_delta)

        return {
            "penalty": total_penalty,
            "completion_rate": 0,
            "tasks_completed": 0,
            "tasks_planned": 0,
            "missed_habits": len(missed_habits_details),
            "auto_finalized": True
        }

    def _is_day_finalized(self, history: PointHistory) -> bool:
        """Check if a day's history has been finalized."""
        if not history or not history.details:
            return False
        try:
            details = json.loads(history.details)
            return "penalty_breakdown" in details
        except json.JSONDecodeError:
            return False

    def _rest_day_result(self) -> dict:
        return {
            "penalty": 0,
            "completion_rate": 1.0,
            "tasks_completed": 0,
            "tasks_planned": 0,
            "missed_habits": 0,
            "is_rest_day": True
        }

    def _no_history_result(self) -> dict:
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
        day_start,
        day_end,
        get_completed_count: Callable
    ) -> None:
        """Update completion counts in history. Uses max to never lose counts."""
        actual_tasks = get_completed_count(day_start, day_end, False)
        actual_habits = get_completed_count(day_start, day_end, True)
        day_history.tasks_completed = max(day_history.tasks_completed, actual_tasks)
        day_history.habits_completed = max(day_history.habits_completed, actual_habits)

    def _calculate_idle_penalty(self, day_history: PointHistory, settings_data: dict) -> int:
        """Calculate idle penalty (0 tasks AND 0 habits)."""
        if day_history.tasks_completed == 0 and day_history.habits_completed == 0:
            return settings_data.get("idle_penalty", 30)
        return 0

    def _calculate_incomplete_penalty(
        self,
        day_history: PointHistory,
        settings_data: dict
    ) -> tuple:
        """Calculate incomplete day penalty."""
        if day_history.tasks_planned == 0:
            return 0, 0, []

        completion_rate = min(
            day_history.tasks_completed / day_history.tasks_planned, 1.0
        )
        day_history.completion_rate = completion_rate

        # Load planned tasks from details
        planned_tasks_info = []
        if day_history.details:
            try:
                details = json.loads(day_history.details)
                planned_tasks_info = details.get("planned_tasks", [])
            except (json.JSONDecodeError, KeyError):
                pass

        if not planned_tasks_info:
            # Fallback to average
            incomplete_count = day_history.tasks_planned - day_history.tasks_completed
            if incomplete_count <= 0:
                return 0, 0, []

            energy_mult = settings_data.get("energy_mult_base", 0.6) + (
                3 * settings_data.get("energy_mult_step", 0.2)
            )
            potential_per_task = settings_data.get("points_per_task_base", 10) * energy_mult
            missed_task_potential = int(incomplete_count * potential_per_task)
            penalty = int(
                missed_task_potential * settings_data.get("incomplete_penalty_percent", 0.5)
            )
            return penalty, missed_task_potential, []

        # Build set of completed task IDs from details
        completed_task_ids = set()
        if day_history.details:
            try:
                details = json.loads(day_history.details)
                for completion in details.get("task_completions", []):
                    tid = completion.get("task_id")
                    if tid is not None:
                        completed_task_ids.add(tid)
            except (json.JSONDecodeError, KeyError):
                pass

        # Calculate using real task energy - only for INCOMPLETE tasks
        missed_task_potential = 0
        incomplete_tasks_details = []

        for task_info in planned_tasks_info:
            task_id = task_info.get("task_id")
            # Skip tasks that were actually completed
            if task_id in completed_task_ids:
                continue

            task_energy = task_info.get("energy", 3)
            energy_mult = settings_data.get("energy_mult_base", 0.6) + (
                task_energy * settings_data.get("energy_mult_step", 0.2)
            )
            potential = settings_data.get("points_per_task_base", 10) * energy_mult
            missed_task_potential += potential
            incomplete_tasks_details.append({
                "id": task_id,
                "description": task_info.get("description", ""),
                "energy": task_energy,
                "potential": int(potential)
            })

        if missed_task_potential == 0:
            return 0, 0, []

        penalty = int(
            missed_task_potential * settings_data.get("incomplete_penalty_percent", 0.5)
        )
        return penalty, int(missed_task_potential), incomplete_tasks_details

    def _apply_consistency_bonus(
        self,
        day_history: PointHistory,
        settings_data: dict
    ) -> None:
        """Apply daily consistency bonus."""
        if day_history.points_earned <= 0:
            return

        if day_history.completion_rate >= 1.0:
            day_history.points_bonus = int(
                day_history.points_earned * settings_data.get("completion_bonus_full", 0.10)
            )
        elif day_history.completion_rate >= 0.8:
            day_history.points_bonus = int(
                day_history.points_earned * settings_data.get("completion_bonus_good", 0.05)
            )

    def _calculate_missed_habits_penalty(
        self,
        day_start,
        day_end,
        day_history: PointHistory,
        settings_data: dict,
        get_missed_habits: Callable
    ) -> tuple:
        """Calculate penalty for missed habits."""
        missed_habits = get_missed_habits(day_start, day_end)

        if not missed_habits:
            return [], 0

        penalty = 0
        missed_habits_details = []

        for habit in missed_habits:
            if habit.get("habit_type") == HABIT_TYPE_SKILL:
                habit_penalty = settings_data.get("missed_habit_penalty_base", 15)
            else:
                habit_penalty = int(
                    settings_data.get("missed_habit_penalty_base", 15) * ROUTINE_PENALTY_MULTIPLIER
                )
            penalty += habit_penalty
            missed_habits_details.append({
                "id": habit.get("id"),
                "description": habit.get("description"),
                "habit_type": habit.get("habit_type"),
                "penalty": habit_penalty
            })

        return missed_habits_details, penalty

    def _apply_progressive_multiplier(
        self,
        penalty: int,
        target_date: date,
        day_history: PointHistory,
        settings_data: dict
    ) -> tuple:
        """Apply progressive penalty multiplier."""
        if penalty > 0:
            yesterday_streak = self._get_effective_penalty_streak(
                target_date - timedelta(days=1)
            )

            day_history.penalty_streak = yesterday_streak + 1 if yesterday_streak > 0 else 1

            progressive_multiplier = 1 + min(
                day_history.penalty_streak * settings_data.get("progressive_penalty_factor", 0.1),
                settings_data.get("progressive_penalty_max", 1.5) - 1
            )
            return int(penalty * progressive_multiplier), progressive_multiplier
        else:
            # Count consecutive days without penalty to decide if streak resets
            reset_days = settings_data.get("penalty_streak_reset_days", 2)
            consecutive_clean = 0
            check = target_date

            for _ in range(reset_days):
                prev = self.history_repo.get_by_date(check - timedelta(days=1))
                if not prev or prev.points_penalty > 0:
                    break
                consecutive_clean += 1
                check -= timedelta(days=1)

            if consecutive_clean >= reset_days:
                # Enough clean days: reset streak
                day_history.penalty_streak = 0
            else:
                # Not enough clean days yet: keep previous streak
                yesterday_history = self.history_repo.get_by_date(target_date - timedelta(days=1))
                if yesterday_history:
                    day_history.penalty_streak = yesterday_history.penalty_streak
                else:
                    day_history.penalty_streak = 0
            return penalty, 1.0

    def _get_effective_penalty_streak(self, check_date: date) -> int:
        """Get the effective penalty streak for a date."""
        history = self.history_repo.get_by_date(check_date)

        if not history:
            return 0

        if history.penalty_streak > 0:
            return history.penalty_streak

        if history.points_penalty > 0:
            streak = 1
            current_date = check_date - timedelta(days=1)

            for _ in range(30):
                prev_history = self.history_repo.get_by_date(current_date)
                if not prev_history:
                    break

                if prev_history.penalty_streak > 0:
                    return streak + prev_history.penalty_streak

                if prev_history.points_penalty > 0:
                    streak += 1
                    current_date -= timedelta(days=1)
                else:
                    break

            return streak

        return 0

    def _apply_final_penalties(self, day_history: PointHistory, penalty: int) -> None:
        """Apply final penalties to history."""
        day_history.points_penalty = penalty
        day_history.daily_total = (
            day_history.points_earned +
            day_history.points_bonus -
            day_history.points_penalty
        )

        net_change = day_history.points_bonus - penalty
        old_cumulative = day_history.cumulative_total
        day_history.cumulative_total = max(0, day_history.cumulative_total + net_change)

        self.history_repo.update(day_history)

        if net_change != 0:
            cumulative_delta = day_history.cumulative_total - old_cumulative
            self._propagate_cumulative_change(day_history.date, cumulative_delta)

    def _propagate_cumulative_change(self, from_date: date, delta: int) -> None:
        """Propagate cumulative change to subsequent days."""
        subsequent = self.history_repo.get_all_after(from_date)
        for history in subsequent:
            history.cumulative_total = max(0, history.cumulative_total + delta)
        self.db.commit()

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
        """Save penalty breakdown to history."""
        details = {}
        if day_history.details:
            try:
                details = json.loads(day_history.details)
                if isinstance(details, list):
                    details = {"task_completions": details}
            except json.JSONDecodeError:
                details = {}

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

        day_history.details = json.dumps(details)
        self.history_repo.update(day_history)

    def _finalize_missing_days(
        self,
        effective_today: date,
        is_rest_day_fn: Callable,
        settings,
        get_history_fn: Callable,
        get_missed_habits_fn: Callable,
        count_habits_due_fn: Callable,
        roll_forward_habit_fn: Optional[Callable] = None,
    ) -> None:
        """
        Finalize any missing days between last finalized and yesterday.

        This handles the case where roll was skipped for one or more days,
        ensuring penalty_streak is calculated correctly.
        """
        yesterday = effective_today - timedelta(days=1)

        # Find oldest unfinalized day (look back up to 14 days)
        oldest_unfinalized = None
        check_date = yesterday

        for _ in range(14):
            history = self.history_repo.get_by_date(check_date)

            if history:
                # Check if already finalized
                if history.points_penalty > 0 or self._is_day_finalized(history):
                    break
                oldest_unfinalized = check_date
            else:
                # No history - check if habits were due
                day_start, day_end = get_day_range(
                    check_date,
                    settings.day_start_enabled,
                    settings.day_start_time
                )
                habits_due = count_habits_due_fn(day_start, day_end)
                if habits_due > 0:
                    oldest_unfinalized = check_date
                elif settings.last_roll_date and check_date < settings.last_roll_date:
                    break

            check_date -= timedelta(days=1)

        if oldest_unfinalized is None or oldest_unfinalized == yesterday:
            return

        # Process days from oldest to yesterday (excluding yesterday - it's handled separately)
        current_date = oldest_unfinalized
        while current_date < yesterday:
            # Skip rest days
            if is_rest_day_fn(current_date):
                current_date += timedelta(days=1)
                continue

            history = self.history_repo.get_by_date(current_date)
            if history and (history.points_penalty > 0 or self._is_day_finalized(history)):
                current_date += timedelta(days=1)
                continue

            # Get day range
            day_start, day_end = get_day_range(
                current_date,
                settings.day_start_enabled,
                settings.day_start_time
            )

            # Check for habits due
            habits_due = count_habits_due_fn(day_start, day_end)
            if habits_due == 0 and not history:
                current_date += timedelta(days=1)
                continue

            # Create or get history
            if not history:
                prev_history = self.history_repo.get_most_recent(current_date)
                previous_cumulative = prev_history.cumulative_total if prev_history else 0

                history = PointHistory(
                    date=current_date,
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
                self.history_repo.create(history)

            # Calculate idle penalty
            idle_penalty = getattr(settings, 'idle_penalty', 30)

            # Calculate missed habits penalty
            missed_habits = get_missed_habits_fn(day_start, day_end)
            habits_penalty = 0
            missed_habits_details = []

            for habit in missed_habits:
                if habit.get("habit_type") == HABIT_TYPE_SKILL:
                    habit_penalty = getattr(settings, 'missed_habit_penalty_base', 15)
                else:
                    habit_penalty = int(
                        getattr(settings, 'missed_habit_penalty_base', 15) * ROUTINE_PENALTY_MULTIPLIER
                    )
                habits_penalty += habit_penalty
                missed_habits_details.append({
                    "id": habit.get("id"),
                    "description": habit.get("description"),
                    "habit_type": habit.get("habit_type"),
                    "penalty": habit_penalty
                })

                # Roll forward habit so it appears as due on next day
                if roll_forward_habit_fn:
                    roll_forward_habit_fn(habit, current_date)

            base_penalty = idle_penalty + habits_penalty

            # Progressive multiplier
            yesterday_streak = self._get_effective_penalty_streak(current_date - timedelta(days=1))
            history.penalty_streak = yesterday_streak + 1 if yesterday_streak > 0 else 1

            progressive_multiplier = 1 + min(
                history.penalty_streak * getattr(settings, 'progressive_penalty_factor', 0.1),
                getattr(settings, 'progressive_penalty_max', 1.5) - 1
            )

            total_penalty = int(base_penalty * progressive_multiplier)

            # Apply penalties
            old_cumulative = history.cumulative_total
            history.points_penalty = total_penalty
            history.daily_total = -total_penalty
            history.cumulative_total = max(0, history.cumulative_total - total_penalty)

            # Save breakdown
            details = {
                "penalty_breakdown": {
                    "idle_penalty": idle_penalty,
                    "incomplete_penalty": 0,
                    "missed_habits_penalty": habits_penalty,
                    "progressive_multiplier": progressive_multiplier,
                    "penalty_streak": history.penalty_streak,
                    "total_penalty": total_penalty,
                    "missed_habits": missed_habits_details,
                    "incomplete_tasks": [],
                    "auto_finalized": True
                }
            }
            history.details = json.dumps(details)
            self.history_repo.update(history)

            # Propagate to subsequent days
            if total_penalty > 0:
                self._propagate_cumulative_change(current_date, history.cumulative_total - old_cumulative)

            current_date += timedelta(days=1)

    def calculate_daily_penalties(
        self,
        effective_today: date,
        is_rest_day_fn: Callable,
        settings,
        get_yesterday_history: Callable,
        get_yesterday_completed_tasks: Callable,
        get_yesterday_completed_habits: Callable,
        get_missed_habits_fn: Callable = None,
        count_habits_due_fn: Callable = None,
        roll_forward_habit_fn: Callable = None,
    ) -> dict:
        """
        Calculate penalties for yesterday (and any skipped days).

        This is the main entry point called by workflows.

        Args:
            effective_today: Today's effective date
            is_rest_day_fn: Function to check if date is rest day
            settings: Settings DTO with penalty parameters
            get_yesterday_history: Function(date) -> PointHistory
            get_yesterday_completed_tasks: Function(start, end) -> List[Task]
            get_yesterday_completed_habits: Function(start, end) -> List[Task]
            get_missed_habits_fn: Function(start, end) -> List[dict] for missed habits
            count_habits_due_fn: Function(start, end) -> int for counting due habits

        Returns:
            Dictionary with penalty information
        """
        # First, finalize any skipped days (if callbacks provided)
        if get_missed_habits_fn and count_habits_due_fn:
            self._finalize_missing_days(
                effective_today,
                is_rest_day_fn,
                settings,
                get_yesterday_history,
                get_missed_habits_fn,
                count_habits_due_fn,
                roll_forward_habit_fn,
            )

        yesterday = effective_today - timedelta(days=1)

        # Check if rest day
        is_rest_day = is_rest_day_fn(yesterday)
        if is_rest_day:
            return self._rest_day_result()

        # Get yesterday's history
        yesterday_history = get_yesterday_history(yesterday)

        if not yesterday_history:
            # No history for yesterday - no penalties
            return self._no_history_result()

        # Check if already finalized
        if yesterday_history.points_penalty > 0 or self._is_day_finalized(yesterday_history):
            return {
                "penalty": yesterday_history.points_penalty,
                "completion_rate": yesterday_history.completion_rate,
                "tasks_completed": yesterday_history.tasks_completed,
                "tasks_planned": yesterday_history.tasks_planned,
                "missed_habits": 0,
                "already_finalized": True
            }

        # Get day range for yesterday
        day_start, day_end = get_day_range(
            yesterday,
            settings.day_start_enabled,
            settings.day_start_time
        )

        # Update task counts (use max to never lose counts)
        completed_tasks = get_yesterday_completed_tasks(day_start, day_end)
        yesterday_history.tasks_completed = max(
            yesterday_history.tasks_completed, len(completed_tasks)
        )

        completed_habits = get_yesterday_completed_habits(day_start, day_end)
        yesterday_history.habits_completed = max(
            yesterday_history.habits_completed, len(completed_habits)
        )

        # Build settings dict
        settings_data = {
            "idle_penalty": getattr(settings, 'idle_penalty', 30),
            "incomplete_penalty_percent": getattr(settings, 'incomplete_penalty_percent', 0.5),
            "missed_habit_penalty_base": getattr(settings, 'missed_habit_penalty_base', 15),
            "progressive_penalty_factor": getattr(settings, 'progressive_penalty_factor', 0.1),
            "progressive_penalty_max": getattr(settings, 'progressive_penalty_max', 1.5),
            "completion_bonus_full": getattr(settings, 'completion_bonus_full', 0.10),
            "completion_bonus_good": getattr(settings, 'completion_bonus_good', 0.05),
            "points_per_task_base": getattr(settings, 'points_per_task_base', 10),
            "energy_mult_base": getattr(settings, 'energy_mult_base', 0.6),
            "energy_mult_step": getattr(settings, 'energy_mult_step', 0.2),
        }

        # Calculate penalties
        penalty = 0

        # 1. Idle Penalty
        idle_penalty = self._calculate_idle_penalty(yesterday_history, settings_data)
        penalty += idle_penalty

        # 2. Incomplete Day Penalty
        incomplete_penalty, missed_task_potential, incomplete_tasks = (
            self._calculate_incomplete_penalty(yesterday_history, settings_data)
        )
        penalty += incomplete_penalty

        # 3. Daily Consistency Bonus
        self._apply_consistency_bonus(yesterday_history, settings_data)

        # 4. Progressive Penalty Multiplier
        if penalty > 0:
            penalty, progressive_multiplier = self._apply_progressive_multiplier(
                penalty, yesterday, yesterday_history, settings_data
            )
        else:
            progressive_multiplier = 1.0

        # Apply final penalties
        self._apply_final_penalties(yesterday_history, penalty)

        # Save penalty breakdown
        self._save_penalty_breakdown(
            yesterday_history,
            idle_penalty,
            incomplete_penalty,
            0,  # habits_penalty
            progressive_multiplier,
            penalty,
            [],  # missed_habits_details
            incomplete_tasks
        )

        return {
            "penalty": penalty,
            "completion_rate": yesterday_history.completion_rate,
            "tasks_completed": yesterday_history.tasks_completed,
            "tasks_planned": yesterday_history.tasks_planned,
            "missed_habits": 0
        }
