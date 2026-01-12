import { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY;

function Settings({ onClose }) {
  const [settings, setSettings] = useState(null);
  const [formData, setFormData] = useState({
    max_tasks_per_day: 10,
    points_per_task_base: 10,
    points_per_habit_base: 15,
    streak_multiplier: 2.0,
    energy_weight: 3.0,
    time_efficiency_weight: 0.5,
    incomplete_day_penalty: 20,
    missed_day_penalty: 50,
    idle_day_penalty: 30,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/settings`, {
        headers: { 'X-API-Key': API_KEY }
      });
      setSettings(response.data);
      setFormData(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch settings:', error);
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: parseFloat(value) || 0
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      await axios.put(`${API_URL}/api/settings`, formData, {
        headers: { 'X-API-Key': API_KEY }
      });
      alert('Settings saved successfully!');
      if (onClose) onClose();
    } catch (error) {
      console.error('Failed to save settings:', error);
      alert('Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="settings">Loading settings...</div>;
  }

  return (
    <div className="settings">
      <div className="settings-header">
        <h2>Settings</h2>
        {onClose && (
          <button onClick={onClose} className="close-btn">×</button>
        )}
      </div>

      <form onSubmit={handleSubmit}>
        <div className="settings-section">
          <h3>Task Limits</h3>
          <div className="form-group">
            <label>Max Tasks Per Day:</label>
            <input
              type="number"
              name="max_tasks_per_day"
              value={formData.max_tasks_per_day}
              onChange={handleChange}
              min="1"
              max="100"
            />
          </div>
        </div>

        <div className="settings-section">
          <h3>Base Points</h3>
          <div className="form-group">
            <label>Points Per Task:</label>
            <input
              type="number"
              name="points_per_task_base"
              value={formData.points_per_task_base}
              onChange={handleChange}
              min="1"
              max="1000"
            />
          </div>
          <div className="form-group">
            <label>Points Per Habit:</label>
            <input
              type="number"
              name="points_per_habit_base"
              value={formData.points_per_habit_base}
              onChange={handleChange}
              min="1"
              max="1000"
            />
          </div>
        </div>

        <div className="settings-section">
          <h3>Multipliers & Weights</h3>
          <div className="form-group">
            <label>Streak Multiplier:</label>
            <input
              type="number"
              step="0.1"
              name="streak_multiplier"
              value={formData.streak_multiplier}
              onChange={handleChange}
              min="0"
              max="10"
            />
            <small>Points per streak day for habits</small>
          </div>
          <div className="form-group">
            <label>Energy Weight:</label>
            <input
              type="number"
              step="0.1"
              name="energy_weight"
              value={formData.energy_weight}
              onChange={handleChange}
              min="0"
              max="20"
            />
            <small>Points multiplier per energy level</small>
          </div>
          <div className="form-group">
            <label>Time Efficiency Weight:</label>
            <input
              type="number"
              step="0.1"
              name="time_efficiency_weight"
              value={formData.time_efficiency_weight}
              onChange={handleChange}
              min="0"
              max="5"
            />
            <small>Impact of time efficiency on points</small>
          </div>
        </div>

        <div className="settings-section">
          <h3>Penalties</h3>
          <div className="form-group">
            <label>Incomplete Day Penalty:</label>
            <input
              type="number"
              name="incomplete_day_penalty"
              value={formData.incomplete_day_penalty}
              onChange={handleChange}
              min="0"
              max="500"
            />
            <small>Penalty for completing less than 50% of tasks</small>
          </div>
          <div className="form-group">
            <label>Missed Day Penalty:</label>
            <input
              type="number"
              name="missed_day_penalty"
              value={formData.missed_day_penalty}
              onChange={handleChange}
              min="0"
              max="500"
            />
            <small>Penalty per missed habit</small>
          </div>
          <div className="form-group">
            <label>Idle Day Penalty:</label>
            <input
              type="number"
              name="idle_day_penalty"
              value={formData.idle_day_penalty}
              onChange={handleChange}
              min="0"
              max="500"
            />
            <small>Penalty for no tasks/habits completed</small>
          </div>
        </div>

        <div className="form-actions">
          <button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          {onClose && (
            <button type="button" onClick={onClose}>
              Cancel
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

export default Settings;
