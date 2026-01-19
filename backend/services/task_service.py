"""
Task management service.
Handles all task-related business logic including CRUD, completion, rolling, and dependencies.
"""
import random
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.models import Task, Settings
from backend.schemas import TaskCreate, TaskUpdate
from backend.repositories.task_repository import TaskRepository
from backend.repositories.settings_repository import SettingsRepository
from backend.services.date_service import DateService
from backend.services.points_service import PointsService
from backend.services.penalty_service import PenaltyService
from backend.constants import (
    TASK_STATUS_PENDING, TASK_STATUS_ACTIVE, TASK_STATUS_COMPLETED,
    RECURRENCE_NONE, RECURRENCE_DAILY, RECURRENCE_EVERY_N_DAYS, RECURRENCE_WEEKLY
)


class TaskService:
    """Service for task management"""

    def __init__(self, db: Session):
        self.db = db
        self.task_repo = TaskRepository()
        self.settings_repo = SettingsRepository()
        self.date_service = DateService()
        self.points_service = PointsService(db)
        self.penalty_service = PenaltyService(db)

    def get_task(self, task_id: int) -> Optional[Task]:
        """Get task by ID"""
        return self.task_repo.get_by_id(self.db, task_id)

    def get_tasks(self, skip: int = 0, limit: int = 100) -> List[Task]:
        """Get all tasks with pagination"""
        return self.task_repo.get_all(self.db, skip, limit)

    def get_stats(self) -> dict:
        """Get daily statistics"""
        settings = self.settings_repo.get(self.db)
        today = self.date_service.get_effective_date(settings)
        day_start, day_end = self.date_service.get_day_range(today)

        done_today = self.task_repo.get_completed_count(
            self.db, day_start, day_end
        )
        pending_today = self.task_repo.get_pending_count(self.db, today)
        total_pending = self.task_repo.get_total_pending_count(self.db)

        return {
            "done_today": done_today,
            "pending_today": pending_today,
            "total_pending": total_pending
        }

    def create_task(self, task_data: TaskCreate) -> Task:
        """Create a new task"""
        # Convert TaskCreate to Task model
        task = Task(**task_data.model_dump())

        # For recurring habits without due_date, set it to today
        if task.is_habit and task.recurrence_type != RECURRENCE_NONE and not task.due_date:
            task.due_date = datetime.combine(date.today(), datetime.min.time())

        # Normalize due_date to midnight
        if task.due_date:
            task.due_date = self.date_service.normalize_to_midnight(task.due_date)

        # For recurring habits, calculate next occurrence if due_date is in the past
        if task.is_habit and task.recurrence_type != RECURRENCE_NONE and task.due_date:
            task.due_date = self.date_service.calculate_next_occurrence(
                task.due_date,
                task.recurrence_type,
                task.recurrence_interval,
                task.recurrence_days
            )

        task.calculate_urgency()
        return self.task_repo.create(self.db, task)

    def update_task(self, task_id: int, task_update: TaskUpdate) -> Optional[Task]:
        """Update an existing task"""
        task = self.task_repo.get_by_id(self.db, task_id)
        if not task:
            return None

        # Apply updates
        update_data = task_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(task, key, value)

        # Normalize due_date to midnight
        if task.due_date:
            task.due_date = self.date_service.normalize_to_midnight(task.due_date)

        # For recurring habits, calculate next occurrence if due_date is in the past
        if task.is_habit and task.recurrence_type != RECURRENCE_NONE and task.due_date:
            task.due_date = self.date_service.calculate_next_occurrence(
                task.due_date,
                task.recurrence_type,
                task.recurrence_interval,
                task.recurrence_days
            )

        task.calculate_urgency()
        return self.task_repo.update(self.db, task)

    def delete_task(self, task_id: int) -> bool:
        """Delete a task"""
        task = self.task_repo.get_by_id(self.db, task_id)
        if not task:
            return False
        self.task_repo.delete(self.db, task)
        return True

    def start_task(self, task_id: Optional[int] = None) -> Optional[Task]:
        """
        Start a task (stop all active first).

        Args:
            task_id: Specific task to start, or None to start next available

        Returns:
            Started task, or None
        """
        # Stop all active tasks
        active_tasks = self.task_repo.get_all_active_tasks(self.db)
        for task in active_tasks:
            if task.started_at:
                elapsed = (datetime.now() - task.started_at).total_seconds()
                task.time_spent = (task.time_spent or 0) + int(elapsed)
            task.status = TASK_STATUS_PENDING
            task.started_at = None
        self.db.commit()

        # Start requested task
        if task_id:
            task = self.task_repo.get_by_id(self.db, task_id)
            if task:
                task.status = TASK_STATUS_ACTIVE
                task.started_at = datetime.now()
                task.is_today = True
                return self.task_repo.update(self.db, task)
        else:
            # Start next available task (not habits)
            task = self.task_repo.get_next_task(self.db)
            if task:
                task.status = TASK_STATUS_ACTIVE
                task.started_at = datetime.now()
                return self.task_repo.update(self.db, task)

        return None

    def stop_task(self) -> bool:
        """Stop active task and save elapsed time"""
        active_task = self.task_repo.get_active_task(self.db)
        if not active_task:
            return False

        # Calculate elapsed time
        if active_task.started_at:
            elapsed = (datetime.now() - active_task.started_at).total_seconds()
            active_task.time_spent = (active_task.time_spent or 0) + int(elapsed)

        active_task.status = TASK_STATUS_PENDING
        active_task.started_at = None
        self.task_repo.update(self.db, active_task)
        return True

    def complete_task(self, task_id: Optional[int] = None) -> Optional[Task]:
        """
        Complete a task.

        Args:
            task_id: Specific task to complete, or None to complete active task

        Returns:
            Completed task, or None
        """
        # Get task to complete
        if task_id:
            task = self.task_repo.get_by_id(self.db, task_id)
        else:
            task = self.task_repo.get_active_task(self.db)

        if not task:
            return None

        # Prevent duplicate completions
        if task.status == TASK_STATUS_COMPLETED:
            return task

        # Mark as completed
        completion_date = datetime.now()
        task.status = TASK_STATUS_COMPLETED
        task.completed_at = completion_date

        # Calculate elapsed time
        if task.started_at:
            elapsed = (completion_date - task.started_at).total_seconds()
            task.time_spent = (task.time_spent or 0) + int(elapsed)

        # Handle habit recurrence
        if task.is_habit and task.recurrence_type != RECURRENCE_NONE:
            self._handle_habit_completion(task)

        self.task_repo.update(self.db, task)

        # Award points
        self.points_service.add_task_completion_points(task)

        # Check goal achievements
        self.points_service.check_goal_achievements()

        return task

    def _handle_habit_completion(self, habit: Task) -> None:
        """Handle habit completion including streak update and next occurrence"""
        settings = self.settings_repo.get(self.db)
        today = self.date_service.get_effective_date(settings)

        # Use habit's due_date as reference
        habit_due = habit.due_date.date() if habit.due_date else today

        # Update streak
        self._update_habit_streak(habit, today)
        habit.last_completed_date = today

        # Create next occurrence
        next_due = self.date_service.calculate_next_due_date(habit, habit_due)
        if next_due:
            self._create_next_habit_occurrence(habit, next_due)

    def _update_habit_streak(self, habit: Task, today: date) -> None:
        """Update habit streak based on completion timing"""
        if not habit.last_completed_date:
            habit.streak = 1
            return

        # Calculate expected interval
        if habit.recurrence_type == RECURRENCE_DAILY:
            expected_diff = 1
        elif habit.recurrence_type == RECURRENCE_EVERY_N_DAYS:
            expected_diff = max(1, habit.recurrence_interval or 1)
        elif habit.recurrence_type == RECURRENCE_WEEKLY:
            expected_diff = 14  # Within 2 weeks is acceptable
        else:
            expected_diff = 1

        days_since_last = (today - habit.last_completed_date).days

        if days_since_last <= expected_diff:
            # On time or early - increment streak
            habit.streak = (habit.streak or 0) + 1
        else:
            # Missed expected completion - reset streak
            habit.streak = 1

    def _create_next_habit_occurrence(self, habit: Task, next_due: date) -> None:
        """Create next occurrence of a recurring habit"""
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
            streak=habit.streak,
            last_completed_date=habit.last_completed_date
        )
        next_habit.calculate_urgency()
        self.task_repo.create(self.db, next_habit)

    def check_dependencies_met(self, task: Task) -> bool:
        """Check if all dependencies for a task are met"""
        if not task.depends_on:
            return True

        dependency = self.task_repo.get_by_id(self.db, task.depends_on)
        if not dependency:
            return True  # Dependency doesn't exist anymore

        return dependency.status == TASK_STATUS_COMPLETED

    def check_dependency_in_today_plan(self, task: Task) -> bool:
        """Check if task's dependency is already scheduled for today"""
        if not task.depends_on:
            return False

        dependency = self.task_repo.get_by_id(self.db, task.depends_on)
        if not dependency:
            return False

        return dependency.status == TASK_STATUS_PENDING and dependency.is_today

    def can_roll_now(self) -> Tuple[bool, str]:
        """
        Check if roll is available right now.

        Returns:
            Tuple of (can_roll, error_message)
        """
        settings = self.settings_repo.get(self.db)
        now = datetime.now()
        effective_today = self.date_service.get_effective_date(settings)
        current_hhmm = now.strftime("%H%M")

        # Check if already rolled today
        if settings.last_roll_date == effective_today:
            return False, "Roll already done today"

        if settings.day_start_enabled:
             return True, ""

        # Check if current time is after roll_available_time
        if not settings.day_start_enabled:
            roll_time_str = settings.roll_available_time or "0000"
            target_hhmm = roll_time_str.replace(":", "")
            
            if int(current_hhmm) < int(target_hhmm):
                formatted_time = f"{target_hhmm[:2]}:{target_hhmm[2:]}"
                return False, f"Roll will be available at {formatted_time}"

        return True, ""

    def roll_tasks(
        self,
        mood: Optional[str] = None,
        daily_limit: int = 5,
        critical_days: int = 2
    ) -> dict:
        """
        Generate daily task plan (max once per day).

        Args:
            mood: Energy level filter (0-5)
            daily_limit: Maximum tasks to schedule
            critical_days: Days threshold for critical tasks

        Returns:
            Dictionary with roll results
        """
        # Check if roll is available
        can_roll, error_msg = self.can_roll_now()
        if not can_roll:
            return self._roll_error_response(error_msg)

        settings = self.settings_repo.get(self.db)
        today = self.date_service.get_effective_date(settings)
        today_start = datetime.combine(today, datetime.min.time())

        # 1. Clean up overdue habits
        deleted_count = self._delete_overdue_habits(today_start)

        # 2. Clear today tag from regular tasks
        self.task_repo.clear_today_flag()

        # 3. Add critical tasks (due soon)
        critical_tasks = self._schedule_critical_tasks(today_start, critical_days)

        # 4. Fill remaining slots with random tasks
        self._schedule_random_tasks(
            mood, daily_limit, len(critical_tasks)
        )

        # 5. Calculate penalties for yesterday
        penalty_info = self.penalty_service.calculate_daily_penalties()

        # 6. Update last roll date
        settings.last_roll_date = today
        self.settings_repo.update(self.db, settings)

        # 7. Get plan summary
        return self._get_roll_summary(deleted_count, penalty_info, today)

    def _roll_error_response(self, error_msg: str) -> dict:
        """Create error response for roll"""
        return {
            "error": error_msg,
            "habits": [],
            "tasks": [],
            "deleted_habits": 0,
            "penalty_info": {
                "penalty": 0,
                "completion_rate": 0,
                "tasks_completed": 0,
                "tasks_planned": 0,
                "missed_habits": 0
            }
        }

    def _delete_overdue_habits(self, today_start: datetime) -> int:
        """Delete habits from before today"""
        overdue_habits = self.task_repo.get_overdue_habits(self.db, today_start)
        for habit in overdue_habits:
            self.task_repo.delete(self.db, habit)
        return len(overdue_habits)

    def _schedule_critical_tasks(
        self,
        today_start: datetime,
        critical_days: int
    ) -> List[Task]:
        """Schedule tasks that are due soon"""
        critical_date = today_start + timedelta(days=critical_days)
        critical_tasks = self.task_repo.get_critical_tasks(
            self.db, today_start, critical_date
        )

        for task in critical_tasks:
            task.is_today = True
        self.db.commit()

        return critical_tasks

    def _schedule_random_tasks(
        self,
        mood: Optional[str],
        daily_limit: int,
        critical_count: int
    ) -> None:
        """Fill remaining slots with random tasks"""
        slots = max(0, daily_limit - critical_count)
        if slots == 0:
            return

        # Get available tasks
        available_tasks = self.task_repo.get_available_tasks(self.db)

        # Pass 1: Tasks with completed dependencies
        ready_tasks = [
            t for t in available_tasks if self.check_dependencies_met(t)
        ]
        ready_tasks = self._filter_by_mood(ready_tasks, mood)
        selected_count = self._select_and_schedule_tasks(ready_tasks, slots)

        # Pass 2: Tasks with dependency in today's plan
        if selected_count < slots:
            dependent_tasks = [
                t for t in available_tasks
                if not t.is_today and self.check_dependency_in_today_plan(t)
            ]
            dependent_tasks = self._filter_by_mood(dependent_tasks, mood)
            remaining_slots = slots - selected_count
            self._select_and_schedule_tasks(dependent_tasks, remaining_slots)

        self.db.commit()

    def _filter_by_mood(self, tasks: List[Task], mood: Optional[str]) -> List[Task]:
        """Filter tasks by energy/mood level"""
        if not mood or not mood.isdigit():
            return tasks

        energy_level = int(mood)
        if 0 <= energy_level <= 5:
            return [t for t in tasks if t.energy <= energy_level]

        return tasks

    def _select_and_schedule_tasks(self, tasks: List[Task], slots: int) -> int:
        """Randomly select and schedule tasks up to slot limit"""
        random.shuffle(tasks)
        selected_count = 0

        for task in tasks:
            if selected_count >= slots:
                break
            if not task.is_today:
                task.is_today = True
                selected_count += 1

        return selected_count

    def _get_roll_summary(
        self,
        deleted_count: int,
        penalty_info: dict,
        today: date
    ) -> dict:
        """Get summary of roll results"""
        habits = self.task_repo.get_today_habits(self.db, today)
        tasks = self.task_repo.get_today_tasks(self.db)

        return {
            "habits": habits,
            "tasks": tasks,
            "deleted_habits": deleted_count,
            "penalty_info": penalty_info
        }
