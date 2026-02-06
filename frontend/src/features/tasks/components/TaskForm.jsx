/**
 * Task creation/edit form component.
 */
import { useState, useEffect } from 'react';
import { taskApi } from '../../../shared/api';

function TaskForm({ onSubmit, onCancel, editTask }) {
  const [formData, setFormData] = useState({
    description: '',
    project: '',
    priority: 5,
    energy: 3,
    is_habit: false,
    is_today: false,
    due_date: '',
    recurrence_type: 'daily',
    recurrence_interval: 1,
    recurrence_days: '[]',
    depends_on: null,
    habit_type: 'skill',
    daily_target: 1
  });

  const [selectedWeekDays, setSelectedWeekDays] = useState([]);
  const [availableTasks, setAvailableTasks] = useState([]);

  // Fetch available tasks for dependency dropdown
  useEffect(() => {
    const fetchTasks = async () => {
      try {
        const response = await taskApi.getAll();
        // Filter to only pending tasks (not habits, not completed)
        const pendingTasks = response.data.filter(
          task => task.status === 'pending' && !task.is_habit
        );
        // Exclude current task if editing
        const filtered = editTask
          ? pendingTasks.filter(task => task.id !== editTask.id)
          : pendingTasks;
        setAvailableTasks(filtered);
      } catch (error) {
        console.error('Error fetching tasks:', error);
      }
    };
    fetchTasks();
  }, [editTask]);

  // Populate form when editing
  useEffect(() => {
    if (editTask) {
      const dueDate = editTask.due_date
        ? editTask.due_date.split('T')[0]
        : '';

      setFormData({
        description: editTask.description || '',
        project: editTask.project || '',
        priority: editTask.priority || 5,
        energy: editTask.energy || 3,
        is_habit: editTask.is_habit || false,
        is_today: editTask.is_today || false,
        due_date: dueDate,
        recurrence_type: editTask.recurrence_type || 'daily',
        recurrence_interval: editTask.recurrence_interval || 1,
        recurrence_days: editTask.recurrence_days || '[]',
        depends_on: editTask.depends_on || null,
        habit_type: editTask.habit_type || 'skill',
        daily_target: editTask.daily_target || 1
      });

      if (editTask.recurrence_days) {
        try {
          const days = JSON.parse(editTask.recurrence_days);
          setSelectedWeekDays(days);
        } catch (e) {
          setSelectedWeekDays([]);
        }
      }
    }
  }, [editTask]);

  const handleSubmit = (e) => {
    e.preventDefault();

    let dueDate = formData.due_date ? new Date(formData.due_date + 'T12:00:00').toISOString() : null;
    if (formData.is_habit && !dueDate) {
      dueDate = new Date().toISOString();
    }

    const submitData = {
      ...formData,
      due_date: dueDate,
      recurrence_type: formData.is_habit ? formData.recurrence_type : 'none',
      depends_on: formData.is_habit ? null : (formData.depends_on ? parseInt(formData.depends_on, 10) : null)
    };

    onSubmit(submitData);
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const toggleWeekDay = (day) => {
    setSelectedWeekDays(prev => {
      const newDays = prev.includes(day)
        ? prev.filter(d => d !== day)
        : [...prev, day].sort((a, b) => a - b);

      setFormData(prevForm => ({
        ...prevForm,
        recurrence_days: JSON.stringify(newDays)
      }));

      return newDays;
    });
  };

  const weekDayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <label className="form-label">Description *</label>
        <textarea
          className="form-textarea"
          name="description"
          value={formData.description}
          onChange={handleChange}
          required
          placeholder="What needs to be done?"
        />
      </div>

      <div className="form-group">
        <label className="form-label">Project</label>
        <input
          className="form-input"
          type="text"
          name="project"
          value={formData.project}
          onChange={handleChange}
          placeholder="Optional project name"
        />
      </div>

      {!formData.is_habit && (
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Priority (0-10)</label>
            <input
              className="form-input"
              type="number"
              name="priority"
              min="0"
              max="10"
              value={formData.priority}
              onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Energy (0-5)</label>
            <input
              className="form-input"
              type="number"
              name="energy"
              min="0"
              max="5"
              value={formData.energy}
              onChange={handleChange}
            />
          </div>
        </div>
      )}

      <div className="form-group">
        <label className="form-label">Due Date</label>
        <input
          className="form-input"
          type="date"
          name="due_date"
          value={formData.due_date}
          onChange={handleChange}
          style={{
            fontSize: '0.9rem',
            padding: '0.75rem',
            cursor: 'pointer'
          }}
        />
        <small style={{ color: '#888', fontSize: '0.75rem', marginTop: '0.25rem', display: 'block' }}>
          {formData.is_habit
            ? 'Start date for recurring habit (leave empty for today)'
            : 'Deadline for task (leave empty for no deadline)'}
        </small>
      </div>

      {!formData.is_habit && (
        <div className="dependency-section">
          <label className="form-label">Task Dependency</label>
          <select
            className="form-input"
            name="depends_on"
            value={formData.depends_on || ''}
            onChange={handleChange}
          >
            <option value="">Independent Task (No Dependencies)</option>
            {availableTasks.map(task => (
              <option key={task.id} value={task.id}>
                Depends on: {task.description.substring(0, 40)}{task.description.length > 40 ? '...' : ''} (P:{task.priority} E:{task.energy})
              </option>
            ))}
          </select>
          <div className="info-box" style={{ marginTop: '0.75rem' }}>
            This task will only appear in Roll after its dependency is completed
          </div>
        </div>
      )}

      <div className="checkbox-group">
        <input
          className="checkbox"
          type="checkbox"
          id="is_habit"
          name="is_habit"
          checked={formData.is_habit}
          onChange={handleChange}
        />
        <label htmlFor="is_habit">Habit</label>
      </div>

      {formData.is_habit && (
        <div className="habit-settings">
          <div className="habit-type-selector">
            <label className="form-label">Habit Type</label>
            <div className="radio-group">
              <label className="radio-label">
                <input
                  type="radio"
                  name="habit_type"
                  value="skill"
                  checked={formData.habit_type === 'skill'}
                  onChange={handleChange}
                />
                <span>Skill (New Habit)</span>
              </label>
              <label className="radio-label">
                <input
                  type="radio"
                  name="habit_type"
                  value="routine"
                  checked={formData.habit_type === 'routine'}
                  onChange={handleChange}
                />
                <span>Routine (Daily Task)</span>
              </label>
            </div>
            <div className="info-box">
              {formData.habit_type === 'skill'
                ? 'Skills: Full points. For building new habits like exercise, meditation, learning.'
                : 'Routines: 50% points. For easy daily tasks like brushing teeth, making bed.'}
            </div>
          </div>

          <div className="form-group" style={{ marginTop: '1rem' }}>
            <label className="form-label">Daily Target</label>
            <input
              className="form-input"
              type="number"
              name="daily_target"
              min="1"
              max="20"
              value={formData.daily_target}
              onChange={handleChange}
            />
            <div className="info-box" style={{ marginTop: '0.5rem' }}>
              How many times per day should this habit be completed? (e.g., "Drink water" - 8 times)
            </div>
          </div>

          <label className="form-label" style={{ marginTop: '1rem' }}>Recurrence Pattern</label>

          <select
            className="form-input"
            name="recurrence_type"
            value={formData.recurrence_type}
            onChange={handleChange}
            style={{ marginBottom: '1rem' }}
          >
            <option value="daily">Every Day</option>
            <option value="every_n_days">Every N Days</option>
            <option value="weekly">Specific Days of Week</option>
            <option value="none">No Repeat (One-time)</option>
          </select>

          {formData.recurrence_type === 'every_n_days' && (
            <div className="form-group">
              <label className="form-label">Every N Days</label>
              <input
                className="form-input"
                type="number"
                name="recurrence_interval"
                min="1"
                max="30"
                value={formData.recurrence_interval}
                onChange={handleChange}
                placeholder="e.g., 2 for every other day"
              />
            </div>
          )}

          {formData.recurrence_type === 'weekly' && (
            <div className="form-group">
              <label className="form-label">Days of Week</label>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.5rem' }}>
                {weekDayNames.map((day, index) => (
                  <button
                    key={index}
                    type="button"
                    onClick={() => toggleWeekDay(index)}
                    className={selectedWeekDays.includes(index) ? 'btn btn-primary btn-small' : 'btn btn-small'}
                    style={{ minWidth: '50px' }}
                  >
                    {day}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
        <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>
          {editTask ? 'Update Task' : 'Create Task'}
        </button>
        {onCancel && (
          <button type="button" className="btn" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}

export default TaskForm;
