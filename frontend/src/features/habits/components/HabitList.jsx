/**
 * Habit list component.
 */
import { formatTimeSpent } from '../../../shared/utils/timeFormat';
import { formatDueDate, isToday, sortByDueDate } from '../../../shared/utils/dateFormat';

function HabitList({ habits, onStart, onComplete, onDelete, onEdit, showAll, settings }) {
  if (!habits || habits.length === 0) {
    return (
      <div className="empty-state">
        No habits for today.
      </div>
    );
  }

  // Sort habits by due date (today first, then tomorrow, etc.)
  const sortedHabits = sortByDueDate(habits, settings);

  return (
    <div className="task-list">
      {sortedHabits.map((habit) => {
        const isTodayHabit = isToday(habit.due_date, settings);
        const showDone = showAll ? isTodayHabit : true;
        const dueDateLabel = formatDueDate(habit.due_date, settings);

        return (
          <div
            key={habit.id}
            className={`task-item ${habit.status === 'active' ? 'active' : ''}`}
          >
            <div className="task-header">
              <div className="task-title">{habit.description}</div>
              <div className="task-actions">
                {habit.status === 'pending' && (
                  <>
                    {isTodayHabit && onStart && (
                      <button
                        className="btn btn-small btn-primary"
                        onClick={() => onStart(habit.id)}
                        title="Start timer for this habit"
                      >
                        Start
                      </button>
                    )}
                    {showDone && (
                      <button
                        className="btn btn-small"
                        onClick={() => onComplete(habit.id)}
                      >
                        Done
                      </button>
                    )}
                    {onEdit && (
                      <button
                        className="btn btn-small"
                        onClick={() => onEdit(habit)}
                        title="Edit habit"
                      >
                        E
                      </button>
                    )}
                    <button
                      className="btn btn-small btn-danger"
                      onClick={() => onDelete(habit.id)}
                    >
                      x
                    </button>
                  </>
                )}
              </div>
            </div>

            <div className="task-meta">
              {habit.project && <span>{habit.project}</span>}
              <span>HABIT</span>
              {habit.time_spent > 0 && (
                <span>TIME: {formatTimeSpent(habit.time_spent)}</span>
              )}
              {habit.streak > 0 && (
                <span>STREAK: {habit.streak}D</span>
              )}
              {(habit.daily_target || 1) > 1 && (
                <span>PROGRESS: {habit.daily_completed || 0}/{habit.daily_target}</span>
              )}
              {dueDateLabel && (
                <span>{dueDateLabel}</span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default HabitList;
