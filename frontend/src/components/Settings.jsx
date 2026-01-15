import { useState, useEffect } from 'react';
import axios from 'axios';

import { API_URL } from '../config';
import { getApiKey } from '../api';

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
    idle_tasks_penalty: 20,
    idle_habits_penalty: 20,
    penalty_streak_reset_days: 3,
    routine_habit_multiplier: 0.5,
    roll_available_time: "00:00",
    auto_penalties_enabled: true,
    auto_roll_enabled: false,
    auto_roll_time: "06:00",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [restDays, setRestDays] = useState([]);
  const [newRestDay, setNewRestDay] = useState('');
  const [activeTab, setActiveTab] = useState('points'); // points, penalties, automation, rest

  useEffect(() => {
    fetchSettings();
    fetchRestDays();
  }, []);

  const fetchRestDays = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/rest-days`, {
        headers: { 'X-API-Key': getApiKey() }
      });
      setRestDays(response.data);
    } catch (error) {
      console.error('Failed to fetch rest days:', error);
    }
  };

  const addRestDay = async (e) => {
    e.preventDefault();
    if (!newRestDay) return;

    try {
      await axios.post(`${API_URL}/api/rest-days`,
        { date: newRestDay },
        { headers: { 'X-API-Key': getApiKey() } }
      );
      setNewRestDay('');
      fetchRestDays();
    } catch (error) {
      console.error('Failed to add rest day:', error);
      alert('Failed to add rest day');
    }
  };

  const deleteRestDay = async (id) => {
    try {
      await axios.delete(`${API_URL}/api/rest-days/${id}`, {
        headers: { 'X-API-Key': getApiKey() }
      });
      fetchRestDays();
    } catch (error) {
      console.error('Failed to delete rest day:', error);
    }
  };

  const fetchSettings = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/settings`, {
        headers: { 'X-API-Key': getApiKey() }
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
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : (type === 'time' || type === 'text' && value.includes(':')) ? value : (parseFloat(value) || 0)
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      await axios.put(`${API_URL}/api/settings`, formData, {
        headers: { 'X-API-Key': getApiKey() }
      });
      alert('Settings saved successfully!');
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
      </div>

      {/* Tab Navigation */}
      <div style={{
        display: 'flex',
        gap: '0.5rem',
        borderBottom: '2px solid var(--border)',
        marginBottom: '1.5rem',
        flexWrap: 'wrap'
      }}>
        <button
          type="button"
          onClick={() => setActiveTab('points')}
          style={{
            padding: '0.75rem 1rem',
            background: activeTab === 'points' ? 'var(--primary)' : 'transparent',
            color: activeTab === 'points' ? '#fff' : 'inherit',
            border: 'none',
            borderBottom: activeTab === 'points' ? '2px solid var(--primary)' : 'none',
            cursor: 'pointer',
            fontWeight: activeTab === 'points' ? 'bold' : 'normal'
          }}
        >
          Points & Rewards
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('penalties')}
          style={{
            padding: '0.75rem 1rem',
            background: activeTab === 'penalties' ? 'var(--primary)' : 'transparent',
            color: activeTab === 'penalties' ? '#fff' : 'inherit',
            border: 'none',
            borderBottom: activeTab === 'penalties' ? '2px solid var(--primary)' : 'none',
            cursor: 'pointer',
            fontWeight: activeTab === 'penalties' ? 'bold' : 'normal'
          }}
        >
          Penalties
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('automation')}
          style={{
            padding: '0.75rem 1rem',
            background: activeTab === 'automation' ? 'var(--primary)' : 'transparent',
            color: activeTab === 'automation' ? '#fff' : 'inherit',
            border: 'none',
            borderBottom: activeTab === 'automation' ? '2px solid var(--primary)' : 'none',
            cursor: 'pointer',
            fontWeight: activeTab === 'automation' ? 'bold' : 'normal'
          }}
        >
          Automation
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('rest')}
          style={{
            padding: '0.75rem 1rem',
            background: activeTab === 'rest' ? 'var(--primary)' : 'transparent',
            color: activeTab === 'rest' ? '#fff' : 'inherit',
            border: 'none',
            borderBottom: activeTab === 'rest' ? '2px solid var(--primary)' : 'none',
            cursor: 'pointer',
            fontWeight: activeTab === 'rest' ? 'bold' : 'normal'
          }}
        >
          Rest Days
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Points & Rewards Tab */}
        {activeTab === 'points' && (
          <div>
            <div className="settings-section">
              <h3>Base Points</h3>
              <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label>Tasks</label>
                  <input type="number" name="points_per_task_base" value={formData.points_per_task_base} onChange={handleChange} min="1" max="1000" />
                </div>
                <div className="form-group">
                  <label>Habits</label>
                  <input type="number" name="points_per_habit_base" value={formData.points_per_habit_base} onChange={handleChange} min="1" max="1000" />
                </div>
              </div>
            </div>

            <div className="settings-section">
              <h3>Bonuses</h3>
              <div className="form-group">
                <label>Streak Multiplier (per day, max 30)</label>
                <input type="number" step="0.1" name="streak_multiplier" value={formData.streak_multiplier} onChange={handleChange} min="0" max="10" />
                <small>Current with 30-day streak: {formData.points_per_habit_base + 30 * formData.streak_multiplier} points</small>
              </div>
              <div className="form-group">
                <label>Energy Weight (tasks only)</label>
                <input type="number" step="0.1" name="energy_weight" value={formData.energy_weight} onChange={handleChange} min="0" max="20" />
              </div>
              <div className="form-group">
                <label>Time Efficiency Weight</label>
                <input type="number" step="0.1" name="time_efficiency_weight" value={formData.time_efficiency_weight} onChange={handleChange} min="0" max="5" />
              </div>
            </div>

            <div className="settings-section">
              <h3>Habit Types</h3>
              <div className="form-group">
                <label>Routine Multiplier (easy daily tasks)</label>
                <input type="number" step="0.1" name="routine_habit_multiplier" value={formData.routine_habit_multiplier} onChange={handleChange} min="0" max="1" />
                <small>Skills get full points, routines get {(formData.routine_habit_multiplier * 100).toFixed(0)}% points</small>
              </div>
            </div>

            <div className="settings-section">
              <h3>Time Settings</h3>
              <div className="form-group">
                <label>Max Tasks Per Day</label>
                <input type="number" name="max_tasks_per_day" value={formData.max_tasks_per_day} onChange={handleChange} min="1" max="100" />
              </div>
              <div className="form-group">
                <label>Minutes Per Energy Unit</label>
                <input type="number" name="minutes_per_energy_unit" value={formData.minutes_per_energy_unit} onChange={handleChange} min="5" max="180" />
                <small>Energy 3 = {3 * formData.minutes_per_energy_unit} minutes</small>
              </div>
            </div>
          </div>
        )}

        {/* Penalties Tab */}
        {activeTab === 'penalties' && (
          <div>
            <div className="info-box" style={{ marginBottom: '1.5rem' }}>
              Progressive penalties increase based on consecutive days WITH penalties (penalty streak), not habit streak.
            </div>

            <div className="settings-section">
              <h3>Incomplete Day</h3>
              <div className="form-group">
                <label>Penalty Points</label>
                <input type="number" name="incomplete_day_penalty" value={formData.incomplete_day_penalty} onChange={handleChange} min="0" max="500" />
              </div>
              <div className="form-group">
                <label>Threshold</label>
                <input type="number" step="0.05" name="incomplete_day_threshold" value={formData.incomplete_day_threshold} onChange={handleChange} min="0" max="1" />
                <small>Need {(formData.incomplete_day_threshold * 100).toFixed(0)}% completion to avoid penalty</small>
              </div>
            </div>

            <div className="settings-section">
              <h3>Idle Days</h3>
              <div className="form-row" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="form-group">
                  <label>Tasks (0 completed)</label>
                  <input type="number" name="idle_tasks_penalty" value={formData.idle_tasks_penalty} onChange={handleChange} min="0" max="500" />
                </div>
                <div className="form-group">
                  <label>Habits (0 completed)</label>
                  <input type="number" name="idle_habits_penalty" value={formData.idle_habits_penalty} onChange={handleChange} min="0" max="500" />
                </div>
              </div>
            </div>

            <div className="settings-section">
              <h3>Missed Habits</h3>
              <div className="form-group">
                <label>Base Penalty</label>
                <input type="number" name="missed_habit_penalty_base" value={formData.missed_habit_penalty_base} onChange={handleChange} min="0" max="500" />
              </div>
            </div>

            <div className="settings-section">
              <h3>Progressive Penalties</h3>
              <div className="form-group">
                <label>Penalty Streak Factor</label>
                <input type="number" step="0.1" name="progressive_penalty_factor" value={formData.progressive_penalty_factor} onChange={handleChange} min="0" max="5" />
                <small>Formula: penalty × (1 + factor × penalty_streak)</small>
              </div>
              <div className="form-group">
                <label>Reset After (days without penalties)</label>
                <input type="number" name="penalty_streak_reset_days" value={formData.penalty_streak_reset_days} onChange={handleChange} min="1" max="30" />
              </div>
            </div>
          </div>
        )}

        {/* Automation Tab */}
        {activeTab === 'automation' && (
          <div>
            <div className="settings-section">
              <h3>Roll Availability</h3>
              <div className="form-group">
                <label>Available From (daily)</label>
                <input type="time" name="roll_available_time" value={formData.roll_available_time} onChange={handleChange} />
                <small>Roll button appears at this time each day</small>
              </div>
            </div>

            <div className="settings-section">
              <h3>Auto-Penalties</h3>
              <div className="form-group">
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <input type="checkbox" name="auto_penalties_enabled" checked={formData.auto_penalties_enabled} onChange={handleChange} />
                  <span>Enable automatic penalties at midnight</span>
                </label>
                <small>Automatically calculate and apply penalties for yesterday</small>
              </div>
            </div>

            <div className="settings-section">
              <h3>Auto-Roll</h3>
              <div className="form-group">
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <input type="checkbox" name="auto_roll_enabled" checked={formData.auto_roll_enabled} onChange={handleChange} />
                  <span>Enable automatic daily Roll</span>
                </label>
              </div>
              {formData.auto_roll_enabled && (
                <div className="form-group">
                  <label>Auto Roll Time</label>
                  <input type="time" name="auto_roll_time" value={formData.auto_roll_time} onChange={handleChange} />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Rest Days Tab */}
        {activeTab === 'rest' && (
          <div>
            <div className="info-box" style={{ marginBottom: '1.5rem' }}>
              Rest days are penalty-free days regardless of task/habit completion.
            </div>

            <div className="settings-section">
              <h3>Add Rest Day</h3>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  type="date"
                  value={newRestDay}
                  onChange={(e) => setNewRestDay(e.target.value)}
                  style={{ flex: 1, padding: '0.75rem', fontSize: '0.9rem' }}
                />
                <button
                  type="button"
                  onClick={addRestDay}
                  disabled={!newRestDay}
                  className="btn btn-primary"
                >
                  Add
                </button>
              </div>
            </div>

            <div className="settings-section">
              <h3>Scheduled Rest Days</h3>
              {restDays.length === 0 ? (
                <p style={{ color: '#888', fontSize: '0.875rem' }}>No rest days scheduled</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {restDays.map((day) => (
                    <div key={day.id} style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '0.75rem',
                      background: 'var(--bg-secondary)',
                      borderRadius: '4px'
                    }}>
                      <span>{new Date(day.date).toLocaleDateString()}</span>
                      <button
                        type="button"
                        onClick={() => deleteRestDay(day.id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--danger)',
                          cursor: 'pointer',
                          fontSize: '1.5rem',
                          lineHeight: '1'
                        }}
                        title="Delete"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Save Button */}
        <div className="form-actions" style={{ marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
          <button type="submit" disabled={saving} className="btn btn-primary" style={{ minWidth: '150px' }}>
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default Settings;
