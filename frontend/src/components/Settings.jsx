import { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY;

function Settings({ onClose }) {
  const [settings, setSettings] = useState(null);
  const [formData, setFormData] = useState({
    max_tasks_per_day: 10,
    points_per_task_base: 10,
    points_per_habit_base: 10,
    streak_multiplier: 1.0,
    energy_weight: 3.0,
    time_efficiency_weight: 0.5,
    minutes_per_energy_unit: 30,
    incomplete_day_penalty: 20,
    incomplete_day_threshold: 0.8,
    missed_habit_penalty_base: 50,
    progressive_penalty_factor: 0.5,
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
            <small>Base points for completing a task</small>
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
            <small>Base points for completing a habit (max with 30-day streak: {formData.points_per_habit_base + 30 * formData.streak_multiplier})</small>
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
            <small>Points per streak day for habits (capped at 30 days)</small>
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
            <small>Points multiplier per energy level (0-5)</small>
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
          <h3>Time Estimation (Automatic)</h3>
          <div className="form-group">
            <label>Minutes Per Energy Unit:</label>
            <input
              type="number"
              name="minutes_per_energy_unit"
              value={formData.minutes_per_energy_unit}
              onChange={handleChange}
              min="5"
              max="180"
            />
            <small>Expected time per energy level (e.g., energy=3 → {3 * formData.minutes_per_energy_unit} min)</small>
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
            <small>Penalty for completing less than threshold</small>
          </div>
          <div className="form-group">
            <label>Incomplete Day Threshold:</label>
            <input
              type="number"
              step="0.05"
              name="incomplete_day_threshold"
              value={formData.incomplete_day_threshold}
              onChange={handleChange}
              min="0"
              max="1"
            />
            <small>Completion rate required to avoid penalty ({(formData.incomplete_day_threshold * 100).toFixed(0)}%)</small>
          </div>
          <div className="form-group">
            <label>Missed Habit Penalty (Base):</label>
            <input
              type="number"
              name="missed_habit_penalty_base"
              value={formData.missed_habit_penalty_base}
              onChange={handleChange}
              min="0"
              max="500"
            />
            <small>Base penalty for missing a habit</small>
          </div>
          <div className="form-group">
            <label>Progressive Penalty Factor:</label>
            <input
              type="number"
              step="0.1"
              name="progressive_penalty_factor"
              value={formData.progressive_penalty_factor}
              onChange={handleChange}
              min="0"
              max="5"
            />
            <small>Penalty multiplier based on streak (e.g., 20-day streak, factor 0.5 → penalty × 11)</small>
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
            <small>Penalty for no tasks/habits completed at all</small>
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
