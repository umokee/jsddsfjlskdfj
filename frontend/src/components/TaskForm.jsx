import { useState } from 'react';

function TaskForm({ onSubmit, onCancel }) {
  const [formData, setFormData] = useState({
    description: '',
    project: '',
    priority: 5,
    energy: 3,
    is_habit: false,
    is_today: false,
    due_date: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();

    const submitData = {
      ...formData,
      due_date: formData.due_date ? new Date(formData.due_date).toISOString() : null
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

      <div className="form-group">
        <label className="form-label">Due Date</label>
        <input
          className="form-input"
          type="datetime-local"
          name="due_date"
          value={formData.due_date}
          onChange={handleChange}
        />
      </div>

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

      <div className="checkbox-group">
        <input
          className="checkbox"
          type="checkbox"
          id="is_today"
          name="is_today"
          checked={formData.is_today}
          onChange={handleChange}
        />
        <label htmlFor="is_today">Schedule for Today</label>
      </div>

      <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
        <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>
          Create Task
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
