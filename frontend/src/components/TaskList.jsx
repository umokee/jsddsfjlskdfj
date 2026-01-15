import { formatTimeSpent } from '../utils/timeFormat';
import { formatDueDate, sortByDueDate } from '../utils/dateFormat';

function TaskList({ tasks, onStart, onComplete, onDelete, onEdit, showAll }) {
  const getPriorityClass = (priority) => {
    if (priority >= 7) return 'priority-high';
    if (priority >= 4) return 'priority-medium';
    return 'priority-low';
  };

  const renderEnergyDots = (energy) => {
    return (
      <div className="energy-badge">
        {[...Array(5)].map((_, i) => (
          <div
            key={i}
            className={`energy-dot ${i < energy ? 'filled' : ''}`}
          />
        ))}
      </div>
    );
  };

  if (!tasks || tasks.length === 0) {
    return (
      <div className="empty-state">
        No tasks yet. Create one to get started.
      </div>
    );
  }

  // Sort tasks by due date (today first, then tomorrow, etc.)
  const sortedTasks = sortByDueDate(tasks);

  return (
    <div className="task-list">
      {sortedTasks.map((task) => {
        const showDone = showAll ? task.is_today : true; // If showAll, only show Done for today's tasks
        const dueDateLabel = formatDueDate(task.due_date);

        return (
          <div
            key={task.id}
            className={`task-item ${task.status === 'active' ? 'active' : ''}`}
          >
            <div className="task-header">
              <div className="task-title">{task.description}</div>
              <div className="task-actions">
                {task.status !== 'active' && (
                  <button
                    className="btn btn-small btn-primary"
                    onClick={() => onStart(task.id)}
                  >
                    Start
                  </button>
                )}
                {showDone && (
                  <button
                    className="btn btn-small"
                    onClick={() => onComplete(task.id)}
                  >
                    Done
                  </button>
                )}
                {onEdit && (
                  <button
                    className="btn btn-small"
                    onClick={() => onEdit(task)}
                    title="Edit task"
                  >
                    ✎
                  </button>
                )}
                <button
                  className="btn btn-small btn-danger"
                  onClick={() => onDelete(task.id)}
                >
                  ×
                </button>
              </div>
            </div>

          <div className="task-meta">
            {task.project && <span>Project: {task.project}</span>}
            <span className={`task-badge ${getPriorityClass(task.priority)}`}>
              P: {task.priority}
            </span>
            <span className="task-badge">
              E: {task.energy}
            </span>
            {renderEnergyDots(task.energy)}
            {task.time_spent > 0 && (
              <span className="task-badge" style={{ backgroundColor: '#3b82f6', color: '#fff' }}>
                ⏱️ {formatTimeSpent(task.time_spent)}
              </span>
            )}
            {task.is_habit && task.streak > 0 && (
              <span className="task-badge" style={{ backgroundColor: '#f59e0b', color: '#000' }}>
                🔥 {task.streak} day{task.streak > 1 ? 's' : ''}
              </span>
            )}
            {task.is_habit && (
              <span className="task-badge">Habit</span>
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

export default TaskList;
