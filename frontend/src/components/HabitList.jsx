import { formatTimeSpent } from '../utils/timeFormat';

function HabitList({ habits, onStart, onComplete, onDelete, onEdit }) {
  if (!habits || habits.length === 0) {
    return (
      <div className="empty-state">
        No habits for today.
      </div>
    );
  }

  return (
    <div className="task-list">
      {habits.map((habit) => (
        <div
          key={habit.id}
          className={`task-item ${habit.status === 'active' ? 'active' : ''}`}
        >
          <div className="task-header">
            <div className="task-title">{habit.description}</div>
            <div className="task-actions">
              {habit.status !== 'active' && (
                <button
                  className="btn btn-small btn-primary"
                  onClick={() => onStart(habit.id)}
                >
                  Start
                </button>
              )}
              <button
                className="btn btn-small"
                onClick={() => onComplete(habit.id)}
              >
                Done
              </button>
              {onEdit && (
                <button
                  className="btn btn-small"
                  onClick={() => onEdit(habit)}
                  title="Edit habit"
                >
                  ✎
                </button>
              )}
              <button
                className="btn btn-small btn-danger"
                onClick={() => onDelete(habit.id)}
              >
                ×
              </button>
            </div>
          </div>

          <div className="task-meta">
            {habit.project && <span>{habit.project}</span>}
            <span className="task-badge">Habit</span>
            {habit.time_spent > 0 && (
              <span className="task-badge" style={{ backgroundColor: '#3b82f6', color: '#fff' }}>
                ⏱️ {formatTimeSpent(habit.time_spent)}
              </span>
            )}
            {habit.streak > 0 && (
              <span className="task-badge" style={{ backgroundColor: '#f59e0b', color: '#000' }}>
                🔥 {habit.streak} day{habit.streak > 1 ? 's' : ''}
              </span>
            )}
            {habit.due_date && (
              <span>Today</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default HabitList;
