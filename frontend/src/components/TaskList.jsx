import { formatTimeSpent } from '../utils/timeFormat';
import { formatDueDate, sortByDueDate } from '../utils/dateFormat';

function TaskList({ tasks, onStart, onComplete, onDelete, onEdit, showAll, settings }) {
  if (!tasks || tasks.length === 0) {
    return (
      <div className="empty-state">
        No tasks yet. Create one to get started.
      </div>
    );
  }

  // Sort tasks by due date (today first, then tomorrow, etc.)
  const sortedTasks = sortByDueDate(tasks, settings);

  return (
    <div className="task-list">
      {sortedTasks.map((task) => {
        // Only show Start/Done for tasks that are scheduled for today (is_today) or are active
        // This prevents point abuse by completing unplanned tasks
        const canInteract = task.is_today || task.status === 'active';
        const showDone = showAll ? task.is_today : canInteract;
        const showStart = canInteract && task.status !== 'active';
        const dueDateLabel = formatDueDate(task.due_date, settings);

        // Check if dependency is blocking this task
        const isBlocked = task.depends_on && !task.dependency_completed;

        return (
          <div
            key={task.id}
            className={`task-item ${task.status === 'active' ? 'active' : ''} ${isBlocked ? 'blocked' : ''}`}
          >
            <div className="task-header">
              <div className="task-title">
                {task.description}
              </div>
              <div className="task-actions">
                {showStart && !isBlocked && (
                  <button
                    className="btn btn-small btn-primary"
                    onClick={() => onStart(task.id)}
                  >
                    Start
                  </button>
                )}
                {showDone && !isBlocked && (
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
            {task.project && <span>{task.project}</span>}
            <span>P:{task.priority}</span>
            <span>E:{task.energy}</span>
            {task.time_spent > 0 && (
              <span>TIME: {formatTimeSpent(task.time_spent)}</span>
            )}
            {task.is_habit && task.streak > 0 && (
              <span>STREAK: {task.streak}D</span>
            )}
            {task.is_habit && (
              <span>HABIT</span>
            )}
            {dueDateLabel && (
              <span>{dueDateLabel}</span>
            )}
            {isBlocked && (
              <span className="status-blocked">BLOCKED</span>
            )}
            {task.dependency_name && (
              <span className={task.dependency_completed ? 'dep-done' : 'dep-pending'}>
                NEEDS: {task.dependency_name.substring(0, 15)}{task.dependency_name.length > 15 ? '...' : ''}
              </span>
            )}
          </div>
        </div>
      );
      })}
    </div>
  );
}

export default TaskList;
