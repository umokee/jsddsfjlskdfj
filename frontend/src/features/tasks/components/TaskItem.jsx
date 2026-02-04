/**
 * Single task item component.
 */
import { formatTimeSpent } from '../../../shared/utils/timeFormat';
import { formatDueDate } from '../../../shared/utils/dateFormat';

function TaskItem({ task, onStart, onComplete, onDelete, onEdit, showAll, settings }) {
  // Only show Start/Done for tasks that are scheduled for today (is_today) or are active
  const canInteract = task.is_today || task.status === 'active';
  const showDone = showAll ? task.is_today : canInteract;
  const showStart = canInteract && task.status !== 'active';
  const dueDateLabel = formatDueDate(task.due_date, settings);

  // Check if dependency is blocking this task
  const isBlocked = task.depends_on && !task.dependency_completed;

  return (
    <div
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
              E
            </button>
          )}
          <button
            className="btn btn-small btn-danger"
            onClick={() => onDelete(task.id)}
          >
            x
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
}

export default TaskItem;
