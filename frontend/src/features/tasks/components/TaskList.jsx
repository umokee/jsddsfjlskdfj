/**
 * Task list component.
 */
import { sortByDueDate } from '../../../shared/utils/dateFormat';
import TaskItem from './TaskItem';

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
      {sortedTasks.map((task) => (
        <TaskItem
          key={task.id}
          task={task}
          onStart={onStart}
          onComplete={onComplete}
          onDelete={onDelete}
          onEdit={onEdit}
          showAll={showAll}
          settings={settings}
        />
      ))}
    </div>
  );
}

export default TaskList;
