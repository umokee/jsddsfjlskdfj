"""
Task service - Business logic for task management.
Does NOT depend on other modules (points, penalties).
Cross-module operations are handled by workflows.
"""
import random
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.shared.constants import (
    TASK_STATUS_PENDING,
    TASK_STATUS_ACTIVE,
    TASK_STATUS_COMPLETED,
    RECURRENCE_NONE,
    RECURRENCE_DAILY,
    RECURRENCE_EVERY_N_DAYS,
    RECURRENCE_WEEKLY,
)
from backend.shared.date_utils import (
    normalize_to_midnight,
    calculate_next_occurrence,
    calculate_next_due_date,
    get_day_range,
)
from .repository import TaskRepository
from .models import Task
from .schemas import TaskCreate, TaskUpdate, TaskResponse, TaskResult, StatsResponse
from .exceptions import TaskNotFoundError, DependencyNotMetError


class TaskService:
    """Service for task operations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = TaskRepository(db)

    def get(self, task_id: int) -> TaskResponse:
        """
        Get task by ID.

        Raises:
            TaskNotFoundError: If task not found
        """
        task = self.repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(task_id)
        return self._to_response(task)

    def get_or_none(self, task_id: int) -> Optional[TaskResponse]:
        """Get task by ID or None if not found."""
        task = self.repo.get_by_id(task_id)
        if not task:
            return None
        return self._to_response(task)

    def get_all(self, skip: int = 0, limit: int = 100) -> List[TaskResponse]:
        """Get all tasks with pagination."""
        tasks = self.repo.get_all(skip, limit)
        return [self._to_response(t) for t in tasks]

    def get_pending(self) -> List[TaskResponse]:
        """Get all pending tasks (excluding habits)."""
        tasks = self.repo.get_pending_tasks()
        return [self._to_response(t) for t in tasks]

    def get_active(self) -> Optional[TaskResponse]:
        """Get currently active task."""
        task = self.repo.get_active_task()
        if not task:
            return None
        return self._to_response(task)

    def get_habits(self) -> List[TaskResponse]:
        """Get all pending habits."""
        habits = self.repo.get_all_habits()
        return [self._to_response(h) for h in habits]

    def get_today_tasks(self) -> List[TaskResponse]:
        """Get today's scheduled tasks (non-habits)."""
        tasks = self.repo.get_today_tasks()
        return [self._to_response(t) for t in tasks]

    def get_today_habits(self, today: date) -> List[TaskResponse]:
        """Get habits due today."""
        habits = self.repo.get_today_habits(today)
        return [self._to_response(h) for h in habits]

    def get_stats(
        self,
        today: date,
        day_start_enabled: bool = False,
        day_start_time: Optional[str] = None
    ) -> StatsResponse:
        """Get daily statistics."""
        day_start, day_end = get_day_range(today, day_start_enabled, day_start_time)

        done_today = self.repo.get_completed_count(day_start, day_end)
        pending_today = self.repo.get_pending_count(today)
        total_pending = self.repo.get_total_pending_count()

        # Habits stats
        habits_done = self.repo.get_completed_count(day_start, day_end, is_habit=True)
        today_habits = self.repo.get_today_habits(today)
        habits_total = len(today_habits) + habits_done

        active_task = self.repo.get_active_task()

        return StatsResponse(
            done_today=done_today,
            pending_today=pending_today,
            total_pending=total_pending,
            habits_done=habits_done,
            habits_total=habits_total,
            active_task=self._to_response(active_task) if active_task else None
        )

    def create(
        self,
        data: TaskCreate,
        effective_today: date,
        last_roll_date: Optional[date] = None
    ) -> TaskResponse:
        """
        Create a new task.

        Args:
            data: Task creation data
            effective_today: Current effective date
            last_roll_date: Date of last roll (to determine if habit should be tomorrow)
        """
        task = Task(**data.model_dump())

        # For recurring habits without due_date, set it to next available day
        if task.is_habit and task.recurrence_type != RECURRENCE_NONE and not task.due_date:
            if last_roll_date == effective_today:
                # Roll already done for this effective day, create for next day
                task.due_date = datetime.combine(effective_today + timedelta(days=1), datetime.min.time())
            else:
                # Roll not done yet, create for current effective day
                task.due_date = datetime.combine(effective_today, datetime.min.time())

        # Normalize due_date to midnight
        if task.due_date:
            task.due_date = normalize_to_midnight(task.due_date)

        # For recurring habits with explicit due_date, calculate next occurrence if in past
        if (task.is_habit and task.recurrence_type != RECURRENCE_NONE and
            task.due_date and data.due_date is not None):
            task.due_date = calculate_next_occurrence(
                task.due_date,
                task.recurrence_type,
                task.recurrence_interval,
                task.recurrence_days
            )

        task.calculate_urgency()
        task = self.repo.create(task)
        return self._to_response(task)

    def update(self, task_id: int, data: TaskUpdate) -> TaskResponse:
        """
        Update an existing task.

        Raises:
            TaskNotFoundError: If task not found
        """
        task = self.repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(task_id)

        # Apply updates
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(task, key, value)

        # Normalize due_date to midnight
        if task.due_date:
            task.due_date = normalize_to_midnight(task.due_date)

        # For recurring habits, calculate next occurrence if due_date is in the past
        if task.is_habit and task.recurrence_type != RECURRENCE_NONE and task.due_date:
            task.due_date = calculate_next_occurrence(
                task.due_date,
                task.recurrence_type,
                task.recurrence_interval,
                task.recurrence_days
            )

        task.calculate_urgency()
        task = self.repo.update(task)
        return self._to_response(task)

    def delete(self, task_id: int) -> bool:
        """
        Delete a task.

        Raises:
            TaskNotFoundError: If task not found
        """
        task = self.repo.get_by_id(task_id)
        if not task:
            raise TaskNotFoundError(task_id)

        self.repo.delete(task)
        return True

    def start(self, task_id: Optional[int] = None) -> Optional[TaskResponse]:
        """
        Start a task (stop all active first).

        Args:
            task_id: Specific task to start, or None to start next available

        Raises:
            DependencyNotMetError: If task has unmet dependency
        """
        # Stop all active tasks
        active_tasks = self.repo.get_all_active_tasks()
        for task in active_tasks:
            if task.started_at:
                elapsed = (datetime.now() - task.started_at).total_seconds()
                task.time_spent = (task.time_spent or 0) + int(elapsed)
            task.status = TASK_STATUS_PENDING
            task.started_at = None
        self.db.commit()

        # Start requested task
        if task_id:
            task = self.repo.get_by_id(task_id)
            if task:
                # Check dependencies before starting
                if not self._check_dependencies_met(task):
                    raise DependencyNotMetError(task.id, task.depends_on)
                task.status = TASK_STATUS_ACTIVE
                task.started_at = datetime.now()
                task.is_today = True
                task = self.repo.update(task)
                return self._to_response(task)
        else:
            # Start next available task (not habits)
            task = self.repo.get_next_task()
            if task:
                task.status = TASK_STATUS_ACTIVE
                task.started_at = datetime.now()
                task = self.repo.update(task)
                return self._to_response(task)

        return None

    def stop(self) -> bool:
        """Stop active task and save elapsed time."""
        active_task = self.repo.get_active_task()
        if not active_task:
            return False

        # Calculate elapsed time
        if active_task.started_at:
            elapsed = (datetime.now() - active_task.started_at).total_seconds()
            active_task.time_spent = (active_task.time_spent or 0) + int(elapsed)

        active_task.status = TASK_STATUS_PENDING
        active_task.started_at = None
        self.repo.update(active_task)
        return True

    def complete(self, task_id: Optional[int] = None, today: Optional[date] = None) -> TaskResult:
        """
        Complete a task (internal logic only, no points).
        Returns TaskResult for workflow to handle points.

        Args:
            task_id: Specific task to complete, or None to complete active task
            today: Current effective date for habit handling

        Returns:
            TaskResult with completion info

        Raises:
            TaskNotFoundError: If task not found
            DependencyNotMetError: If task has unmet dependency
        """
        # Get task to complete
        if task_id:
            task = self.repo.get_by_id(task_id)
        else:
            task = self.repo.get_active_task()

        if not task:
            raise TaskNotFoundError(task_id or 0)

        # Check dependencies before completing
        if not self._check_dependencies_met(task):
            raise DependencyNotMetError(task.id, task.depends_on)

        # Refresh task from DB (race condition protection)
        self.db.refresh(task)
        if task.status == TASK_STATUS_COMPLETED:
            return self._to_result(task, fully_completed=True)

        completion_date = datetime.now()
        fully_completed = False

        # For habits with daily_target > 1, track progress
        if task.is_habit and (task.daily_target or 1) > 1:
            task.daily_completed = (task.daily_completed or 0) + 1

            if task.daily_completed >= task.daily_target:
                # Target reached - complete the habit
                fully_completed = True
                task.status = TASK_STATUS_COMPLETED
                task.completed_at = completion_date

                # Handle habit recurrence
                if task.recurrence_type != RECURRENCE_NONE and today:
                    self._handle_habit_completion(task, today)
            else:
                # Not yet reached - just update counter
                if task.started_at:
                    elapsed = (completion_date - task.started_at).total_seconds()
                    task.time_spent = (task.time_spent or 0) + int(elapsed)

                task.status = TASK_STATUS_PENDING
                task.started_at = None

            self.repo.update(task)
            return self._to_result(task, fully_completed=fully_completed)

        # Regular task or habit with daily_target=1
        fully_completed = True
        task.status = TASK_STATUS_COMPLETED
        task.completed_at = completion_date

        # Calculate elapsed time
        if task.started_at:
            elapsed = (completion_date - task.started_at).total_seconds()
            task.time_spent = (task.time_spent or 0) + int(elapsed)

        # Handle habit recurrence
        if task.is_habit and task.recurrence_type != RECURRENCE_NONE and today:
            self._handle_habit_completion(task, today)

        self.repo.update(task)
        return self._to_result(task, fully_completed=fully_completed)

    def can_roll(
        self,
        effective_today: date,
        last_roll_date: Optional[date],
        day_start_enabled: bool,
        roll_available_time: str
    ) -> Tuple[bool, str]:
        """
        Check if roll is available right now.

        Returns:
            Tuple of (can_roll, error_message)
        """
        now = datetime.now()
        current_hhmm = now.strftime("%H%M")

        # Check if already rolled today
        if last_roll_date == effective_today:
            return False, "Roll already done today"

        # If day_start is enabled, roll is always available (day boundary controls it)
        if day_start_enabled:
            return True, ""

        # If day_start is disabled, check roll_available_time
        roll_time_str = roll_available_time or "0000"
        target_hhmm = roll_time_str.replace(":", "")

        if int(current_hhmm) < int(target_hhmm):
            formatted_time = f"{target_hhmm[:2]}:{target_hhmm[2:]}"
            return False, f"Roll will be available at {formatted_time}"

        return True, ""

    def roll_tasks(
        self,
        mood: Optional[str],
        daily_limit: int,
        today: date
    ) -> Tuple[List[TaskResponse], List[TaskResponse], int]:
        """
        Generate daily task plan.
        Does NOT handle penalties (that's in workflow).

        Args:
            mood: Energy level filter (0-5)
            daily_limit: Maximum tasks to schedule
            today: Current effective date

        Returns:
            Tuple of (selected_tasks, today_habits, deleted_habits_count)
        """
        today_start = datetime.combine(today, datetime.min.time())

        # 1. Clean up overdue habits
        deleted_count = self._delete_overdue_habits(today_start, today)

        # 2. Clear today tag from regular tasks
        self.repo.clear_today_flag()

        # 3. Select tasks using weighted random based on urgency
        self._schedule_weighted_tasks(mood, daily_limit)

        # 4. Get results
        tasks = self.repo.get_today_tasks()
        habits = self.repo.get_today_habits(today)

        return (
            [self._to_response(t) for t in tasks],
            [self._to_response(h) for h in habits],
            deleted_count
        )

    def get_today_task_details(self) -> List[dict]:
        """Get details of today's tasks for penalty calculation."""
        tasks = self.repo.get_today_tasks()
        return [
            {
                "task_id": task.id,
                "energy": task.energy,
                "description": task.description[:50]
            }
            for task in tasks
        ]

    def get_project_progress(self, project_name: str) -> dict:
        """Get task completion progress for a project."""
        return self.repo.get_project_task_counts(project_name)

    def check_dependencies_met(self, task_id: int) -> bool:
        """Check if all dependencies for a task are met."""
        task = self.repo.get_by_id(task_id)
        if not task:
            return True
        return self._check_dependencies_met(task)

    def enrich_with_dependency(self, task_response: TaskResponse) -> TaskResponse:
        """Add dependency info to task response."""
        if not task_response.depends_on:
            return task_response

        dep_task = self.repo.get_by_id(task_response.depends_on)
        if dep_task:
            task_response.dependency_name = dep_task.description
            task_response.dependency_completed = dep_task.status == TASK_STATUS_COMPLETED
        else:
            task_response.dependency_completed = True

        return task_response

    def check_dependency_in_today_plan(self, task: Task) -> bool:
        """Check if task's dependency is already scheduled for today."""
        if not task.depends_on:
            return False

        dependency = self.repo.get_by_id(task.depends_on)
        if not dependency:
            return False

        return dependency.status == TASK_STATUS_PENDING and dependency.is_today

    def get_missed_habits(self, start: datetime, end: datetime) -> List[dict]:
        """Get habits that were due but not completed in a date range."""
        missed = self.repo.get_missed_habits(start, end)
        return [
            {
                "id": h.id,
                "description": h.description,
                "habit_type": h.habit_type,
                "recurrence_type": h.recurrence_type,
            }
            for h in missed
        ]

    def count_habits_due(self, start: datetime, end: datetime) -> int:
        """Count habits due in a date range."""
        return self.repo.count_habits_due_in_range(start, end)

    def roll_forward_missed_habit(self, habit_data: dict, from_date: date) -> None:
        """Roll forward a missed habit to its next due date.

        Used by penalty finalization to reschedule habits on intermediate
        missed days so that subsequent days can detect them as due.
        """
        habit = self.repo.get_by_id(habit_data.get("id"))
        if not habit or not habit.is_habit:
            return

        if habit.recurrence_type == RECURRENCE_NONE:
            return

        current_due = habit.due_date.date() if habit.due_date else from_date
        next_due = calculate_next_due_date(
            habit.recurrence_type,
            current_due,
            habit.recurrence_interval,
            habit.recurrence_days
        )

        if next_due:
            self._create_next_habit_occurrence(habit, next_due)
        self.repo.delete(habit)

    # Private methods

    def _check_dependencies_met(self, task: Task) -> bool:
        """Check if all dependencies for a task are met."""
        if not task.depends_on:
            return True

        dependency = self.repo.get_by_id(task.depends_on)
        if not dependency:
            return True  # Dependency doesn't exist anymore

        return dependency.status == TASK_STATUS_COMPLETED

    def _handle_habit_completion(self, habit: Task, today: date) -> None:
        """Handle habit completion including streak update and next occurrence."""
        habit_due = habit.due_date.date() if habit.due_date else today

        # Update streak
        self._update_habit_streak(habit, today)
        habit.last_completed_date = today

        # Create next occurrence
        next_due = calculate_next_due_date(
            habit.recurrence_type,
            habit_due,
            habit.recurrence_interval,
            habit.recurrence_days
        )
        if next_due:
            self._create_next_habit_occurrence(habit, next_due)

    def _update_habit_streak(self, habit: Task, today: date) -> None:
        """Update habit streak based on completion timing."""
        if not habit.last_completed_date:
            habit.streak = 1
            return

        # Calculate expected interval
        if habit.recurrence_type == RECURRENCE_DAILY:
            expected_diff = 1
        elif habit.recurrence_type == RECURRENCE_EVERY_N_DAYS:
            expected_diff = max(1, habit.recurrence_interval or 1)
        elif habit.recurrence_type == RECURRENCE_WEEKLY:
            expected_diff = 8  # Within 1 week + 1 day tolerance
        else:
            expected_diff = 1

        days_since_last = (today - habit.last_completed_date).days

        if days_since_last <= expected_diff:
            habit.streak = (habit.streak or 0) + 1
        else:
            habit.streak = 1

    def _create_next_habit_occurrence(self, habit: Task, next_due: date) -> None:
        """Create next occurrence of a recurring habit."""
        is_missed = habit.status != TASK_STATUS_COMPLETED

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
            streak=0 if is_missed else habit.streak,
            last_completed_date=habit.last_completed_date,
            daily_target=habit.daily_target or 1,
            daily_completed=0
        )
        next_habit.calculate_urgency()
        self.repo.create(next_habit)

    def _delete_overdue_habits(self, today_start: datetime, today: date) -> int:
        """Delete overdue habits and create new instances if recurring."""
        overdue_habits = self.repo.get_overdue_habits(today_start)
        deleted_count = 0

        for habit in overdue_habits:
            # For recurring habits, create new instance at next occurrence
            if habit.recurrence_type != RECURRENCE_NONE:
                current_due = habit.due_date.date() if habit.due_date else today
                next_due = calculate_next_due_date(
                    habit.recurrence_type,
                    current_due,
                    habit.recurrence_interval,
                    habit.recurrence_days
                )

                if next_due:
                    self._create_next_habit_occurrence(habit, next_due)

            # Delete the overdue habit
            self.repo.delete(habit)
            deleted_count += 1

        return deleted_count

    def _schedule_weighted_tasks(
        self,
        mood: Optional[str],
        daily_limit: int
    ) -> None:
        """Select tasks using weighted random selection based on urgency."""
        # 1. Get all available pending tasks
        available_tasks = self.repo.get_available_tasks()

        if not available_tasks:
            return

        # 2. Filter by mood (energy level)
        if mood and mood.isdigit():
            energy_level = int(mood)
            if 0 <= energy_level <= 5:
                available_tasks = [t for t in available_tasks if t.energy <= energy_level]

        # 3. Filter by dependencies (only ready tasks)
        ready_tasks = [
            t for t in available_tasks if self._check_dependencies_met(t)
        ]

        if not ready_tasks:
            return

        # 4. Calculate urgency for each task
        for task in ready_tasks:
            task.calculate_urgency()

        # 5. Normalize weights (handle negative urgency)
        min_urgency = min(task.urgency for task in ready_tasks)
        if min_urgency < 0:
            weights = [task.urgency - min_urgency + 1 for task in ready_tasks]
        else:
            weights = [task.urgency + 1 for task in ready_tasks]

        # 6. Weighted random selection up to daily_limit
        selected_tasks = []
        available_pool = ready_tasks.copy()
        available_weights = weights.copy()

        slots = min(daily_limit, len(available_pool))

        for _ in range(slots):
            if not available_pool:
                break

            selected_task = random.choices(
                available_pool,
                weights=available_weights,
                k=1
            )[0]

            selected_tasks.append(selected_task)

            idx = available_pool.index(selected_task)
            available_pool.pop(idx)
            available_weights.pop(idx)

        # 7. Mark selected tasks for today
        for task in selected_tasks:
            task.is_today = True

        self.db.commit()

    def _to_response(self, task: Task) -> TaskResponse:
        """Convert Task model to TaskResponse."""
        response = TaskResponse.model_validate(task)

        # Add dependency info
        if task.depends_on:
            dep_task = self.repo.get_by_id(task.depends_on)
            if dep_task:
                response.dependency_name = dep_task.description
                response.dependency_completed = dep_task.status == TASK_STATUS_COMPLETED
            else:
                response.dependency_completed = True

        return response

    def _to_result(self, task: Task, fully_completed: bool) -> TaskResult:
        """Convert Task model to TaskResult for workflows."""
        return TaskResult(
            id=task.id,
            description=task.description,
            energy=task.energy,
            priority=task.priority,
            is_habit=task.is_habit,
            habit_type=task.habit_type or "skill",
            streak=task.streak or 0,
            time_spent=task.time_spent or 0,
            started_at=task.started_at,
            daily_target=task.daily_target or 1,
            daily_completed=task.daily_completed or 0,
            fully_completed=fully_completed
        )

    # Methods for scheduler/workflows
    def _get_completed_in_range(self, start: datetime, end: datetime) -> List[Task]:
        """Get tasks completed in a date range (for penalty calculation)."""
        return self.repo.get_completed_in_range(start, end)

    def _get_completed_habits_in_range(self, start: datetime, end: datetime) -> List[Task]:
        """Get habits completed in a date range (for penalty calculation)."""
        return self.repo.get_completed_habits_in_range(start, end)
