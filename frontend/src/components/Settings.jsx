import { useState, useEffect } from 'react';
import axios from 'axios';

import { API_URL } from '../config';
import { getApiKey } from '../api';

function Settings({ onClose }) {
  const [settings, setSettings] = useState(null);
  const [formData, setFormData] = useState({
    // Base points
    max_tasks_per_day: 10,
    points_per_task_base: 10,
    points_per_habit_base: 10,

    // === BALANCED PROGRESS v2.0 ===

    // Energy multiplier
    energy_mult_base: 0.6,
    energy_mult_step: 0.2,

    // Time quality
    minutes_per_energy_unit: 20,
    min_work_time_seconds: 120,

    // Streak settings
    streak_log_factor: 0.15,
    max_streak_bonus_days: 100,

    // Routine habits
    routine_points_fixed: 6,

    // Daily completion bonus
    completion_bonus_full: 0.10,
    completion_bonus_good: 0.05,

    // Penalties
    idle_penalty: 30,
    incomplete_day_penalty: 10,
    incomplete_day_threshold: 0.6,
    incomplete_threshold_severe: 0.4,
    incomplete_penalty_severe: 15,
    missed_habit_penalty_base: 15,
    progressive_penalty_factor: 0.1,
    progressive_penalty_max: 1.5,
    penalty_streak_reset_days: 2,

    // Day boundary settings
    day_start_enabled: false,
    day_start_time: "06:00",

    // Time settings
    roll_available_time: "00:00",
    auto_penalties_enabled: true,
    penalty_time: "00:01",
    auto_roll_enabled: false,
    auto_roll_time: "06:00",

    // Backup settings
    auto_backup_enabled: true,
    backup_time: "03:00",
    backup_interval_days: 1,
    backup_keep_local_count: 10,
    google_drive_enabled: false,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [restDays, setRestDays] = useState([]);
  const [newRestDay, setNewRestDay] = useState('');
  const [activeTab, setActiveTab] = useState('points');

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

  // Calculate example points for display
  const calcEnergyMult = (energy) => formData.energy_mult_base + (energy * formData.energy_mult_step);
  const calcStreakBonus = (streak) => 1 + Math.log2(streak + 1) * formData.streak_log_factor;

  if (loading) {
    return <div className="settings">Loading settings...</div>;
  }

  return (
    <div className="settings">
      <div className="settings-header">
        <h2>Settings</h2>
      </div>

      {/* Tab Navigation */}
      <div className="settings-tabs">
        <button
          type="button"
          className={`tab-button ${activeTab === 'points' ? 'active' : ''}`}
          onClick={() => setActiveTab('points')}
        >
          Points & Rewards
        </button>
        <button
          type="button"
          className={`tab-button ${activeTab === 'penalties' ? 'active' : ''}`}
          onClick={() => setActiveTab('penalties')}
        >
          Penalties
        </button>
        <button
          type="button"
          className={`tab-button ${activeTab === 'automation' ? 'active' : ''}`}
          onClick={() => setActiveTab('automation')}
        >
          Automation
        </button>
        <button
          type="button"
          className={`tab-button ${activeTab === 'backups' ? 'active' : ''}`}
          onClick={() => setActiveTab('backups')}
        >
          Backups
        </button>
        <button
          type="button"
          className={`tab-button ${activeTab === 'rest' ? 'active' : ''}`}
          onClick={() => setActiveTab('rest')}
        >
          Rest Days
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Points & Rewards Tab */}
        {activeTab === 'points' && (
          <div>
            <div className="info-box" style={{ margin: '0 2rem', marginTop: '1.5rem' }}>
              <strong>Balanced Progress v2.0</strong> — Points = Base × EnergyMultiplier × TimeQualityFactor × FocusFactor
            </div>

            <div className="settings-section">
              <h3>Base Points</h3>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Tasks (base)</label>
                  <input className="form-input" type="number" name="points_per_task_base" value={formData.points_per_task_base} onChange={handleChange} min="1" max="100" />
                </div>
                <div className="form-group">
                  <label className="form-label">Skill Habits (base)</label>
                  <input className="form-input" type="number" name="points_per_habit_base" value={formData.points_per_habit_base} onChange={handleChange} min="1" max="100" />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Routine Habits (fixed)</label>
                <input className="form-input" type="number" name="routine_points_fixed" value={formData.routine_points_fixed} onChange={handleChange} min="1" max="50" />
                <small>Routines get fixed points, no streak bonus</small>
              </div>
            </div>

            <div className="settings-section">
              <h3>Energy Multiplier</h3>
              <div className="info-box">
                Formula: {formData.energy_mult_base} + (energy × {formData.energy_mult_step})<br />
                E0→{calcEnergyMult(0).toFixed(1)}, E1→{calcEnergyMult(1).toFixed(1)}, E2→{calcEnergyMult(2).toFixed(1)}, E3→{calcEnergyMult(3).toFixed(1)}, E4→{calcEnergyMult(4).toFixed(1)}, E5→{calcEnergyMult(5).toFixed(1)}
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Base Multiplier</label>
                  <input className="form-input" type="number" step="0.1" name="energy_mult_base" value={formData.energy_mult_base} onChange={handleChange} min="0.1" max="2" />
                </div>
                <div className="form-group">
                  <label className="form-label">Step per Energy Level</label>
                  <input className="form-input" type="number" step="0.1" name="energy_mult_step" value={formData.energy_mult_step} onChange={handleChange} min="0" max="1" />
                </div>
              </div>
            </div>

            <div className="settings-section">
              <h3>Time Quality</h3>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Minutes per Energy Unit</label>
                  <input className="form-input" type="number" name="minutes_per_energy_unit" value={formData.minutes_per_energy_unit} onChange={handleChange} min="5" max="120" />
                  <small>E3 task = {3 * formData.minutes_per_energy_unit} min expected</small>
                </div>
                <div className="form-group">
                  <label className="form-label">Min Work Time (seconds)</label>
                  <input className="form-input" type="number" name="min_work_time_seconds" value={formData.min_work_time_seconds} onChange={handleChange} min="0" max="600" />
                  <small>Tasks under this time get reduced points</small>
                </div>
              </div>
            </div>

            <div className="settings-section">
              <h3>Streak Bonus (Skill Habits)</h3>
              <div className="info-box">
                Formula: 1 + log₂(streak + 1) × {formData.streak_log_factor}<br />
                Streak 0→×{calcStreakBonus(0).toFixed(2)}, 5→×{calcStreakBonus(5).toFixed(2)}, 10→×{calcStreakBonus(10).toFixed(2)}, 30→×{calcStreakBonus(30).toFixed(2)}, 100→×{calcStreakBonus(100).toFixed(2)}
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Log Factor</label>
                  <input className="form-input" type="number" step="0.01" name="streak_log_factor" value={formData.streak_log_factor} onChange={handleChange} min="0" max="1" />
                </div>
                <div className="form-group">
                  <label className="form-label">Max Streak Days</label>
                  <input className="form-input" type="number" name="max_streak_bonus_days" value={formData.max_streak_bonus_days} onChange={handleChange} min="1" max="365" />
                </div>
              </div>
            </div>

            <div className="settings-section">
              <h3>Daily Completion Bonus</h3>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">100% Completion Bonus</label>
                  <input className="form-input" type="number" step="0.01" name="completion_bonus_full" value={formData.completion_bonus_full} onChange={handleChange} min="0" max="0.5" />
                  <small>{(formData.completion_bonus_full * 100).toFixed(0)}% of earned points</small>
                </div>
                <div className="form-group">
                  <label className="form-label">80%+ Completion Bonus</label>
                  <input className="form-input" type="number" step="0.01" name="completion_bonus_good" value={formData.completion_bonus_good} onChange={handleChange} min="0" max="0.3" />
                  <small>{(formData.completion_bonus_good * 100).toFixed(0)}% of earned points</small>
                </div>
              </div>
            </div>

            <div className="settings-section">
              <h3>Task Limits</h3>
              <div className="form-group">
                <label className="form-label">Max Tasks Per Day</label>
                <input className="form-input" type="number" name="max_tasks_per_day" value={formData.max_tasks_per_day} onChange={handleChange} min="1" max="100" />
              </div>
            </div>
          </div>
        )}

        {/* Penalties Tab */}
        {activeTab === 'penalties' && (
          <div>
            <div className="info-box" style={{ margin: '0 2rem', marginTop: '1.5rem' }}>
              Penalties are applied during daily Roll. Progressive multiplier increases with consecutive penalty days.
            </div>

            <div className="settings-section">
              <h3>Idle Day Penalty</h3>
              <div className="form-group">
                <label className="form-label">Penalty (0 tasks AND 0 habits)</label>
                <input className="form-input" type="number" name="idle_penalty" value={formData.idle_penalty} onChange={handleChange} min="0" max="500" />
                <small>Applied only if both tasks and habits are 0</small>
              </div>
            </div>

            <div className="settings-section">
              <h3>Incomplete Day Penalty</h3>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Threshold (normal)</label>
                  <input className="form-input" type="number" step="0.05" name="incomplete_day_threshold" value={formData.incomplete_day_threshold} onChange={handleChange} min="0" max="1" />
                  <small>Below {(formData.incomplete_day_threshold * 100).toFixed(0)}% = scaled penalty</small>
                </div>
                <div className="form-group">
                  <label className="form-label">Penalty (scaled)</label>
                  <input className="form-input" type="number" name="incomplete_day_penalty" value={formData.incomplete_day_penalty} onChange={handleChange} min="0" max="500" />
                  <small>penalty × (1 - completion_rate)</small>
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Threshold (severe)</label>
                  <input className="form-input" type="number" step="0.05" name="incomplete_threshold_severe" value={formData.incomplete_threshold_severe} onChange={handleChange} min="0" max="1" />
                  <small>Below {(formData.incomplete_threshold_severe * 100).toFixed(0)}% = fixed penalty</small>
                </div>
                <div className="form-group">
                  <label className="form-label">Penalty (severe)</label>
                  <input className="form-input" type="number" name="incomplete_penalty_severe" value={formData.incomplete_penalty_severe} onChange={handleChange} min="0" max="500" />
                </div>
              </div>
            </div>

            <div className="settings-section">
              <h3>Missed Habits Penalty</h3>
              <div className="form-group">
                <label className="form-label">Base Penalty per Missed Habit</label>
                <input className="form-input" type="number" name="missed_habit_penalty_base" value={formData.missed_habit_penalty_base} onChange={handleChange} min="0" max="500" />
                <small>Skill: {formData.missed_habit_penalty_base} pts, Routine: {Math.floor(formData.missed_habit_penalty_base * 0.5)} pts</small>
              </div>
            </div>

            <div className="settings-section">
              <h3>Progressive Penalty</h3>
              <div className="info-box">
                Multiplier = 1 + min(penalty_streak × {formData.progressive_penalty_factor}, {(formData.progressive_penalty_max - 1).toFixed(1)})<br />
                Day 1: ×{(1 + Math.min(1 * formData.progressive_penalty_factor, formData.progressive_penalty_max - 1)).toFixed(1)},
                Day 3: ×{(1 + Math.min(3 * formData.progressive_penalty_factor, formData.progressive_penalty_max - 1)).toFixed(1)},
                Day 5+: ×{formData.progressive_penalty_max.toFixed(1)} (max)
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label className="form-label">Factor per Day</label>
                  <input className="form-input" type="number" step="0.05" name="progressive_penalty_factor" value={formData.progressive_penalty_factor} onChange={handleChange} min="0" max="1" />
                </div>
                <div className="form-group">
                  <label className="form-label">Max Multiplier</label>
                  <input className="form-input" type="number" step="0.1" name="progressive_penalty_max" value={formData.progressive_penalty_max} onChange={handleChange} min="1" max="5" />
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Reset After (days without penalties)</label>
                <input className="form-input" type="number" name="penalty_streak_reset_days" value={formData.penalty_streak_reset_days} onChange={handleChange} min="1" max="30" />
              </div>
            </div>
          </div>
        )}

        {/* Automation Tab */}
        {activeTab === 'automation' && (
          <div>
            <div className="settings-section">
              <h3>Day Boundary</h3>
              <div className="info-box">
                For shifted sleep schedules. If enabled, "today" starts at the specified time instead of midnight.
              </div>
              <div className="checkbox-group" style={{ marginTop: '1rem' }}>
                <input className="checkbox" type="checkbox" name="day_start_enabled" checked={formData.day_start_enabled} onChange={handleChange} id="day_start_enabled" />
                <label htmlFor="day_start_enabled">Enable custom day start time</label>
              </div>
              {formData.day_start_enabled && (
                <div className="form-group" style={{ marginTop: '1rem' }}>
                  <label className="form-label">Day Start Time</label>
                  <input className="form-input" type="time" name="day_start_time" value={formData.day_start_time} onChange={handleChange} />
                  <small>New day starts at this time (e.g., 06:00 means 05:59 is still "yesterday")</small>
                </div>
              )}
            </div>

            <div className="settings-section">
              <h3>Roll Availability</h3>
              <div className="form-group">
                <label className="form-label">Available From (daily)</label>
                <input className="form-input" type="time" name="roll_available_time" value={formData.roll_available_time} onChange={handleChange} />
                <small>Roll button appears at this time each day{formData.day_start_enabled ? ' (ignored when Day Boundary is enabled)' : ''}</small>
              </div>
            </div>

            <div className="settings-section">
              <h3>Auto-Penalties</h3>
              <div className="checkbox-group">
                <input className="checkbox" type="checkbox" name="auto_penalties_enabled" checked={formData.auto_penalties_enabled} onChange={handleChange} id="auto_penalties" />
                <label htmlFor="auto_penalties">Enable automatic penalties</label>
              </div>
              {formData.auto_penalties_enabled && (
                <div className="form-group" style={{ marginTop: '1rem' }}>
                  <label className="form-label">Penalty Calculation Time</label>
                  <input className="form-input" type="time" name="penalty_time" value={formData.penalty_time} onChange={handleChange} />
                  <small>Penalties for yesterday are applied at this time</small>
                </div>
              )}
            </div>

            <div className="settings-section">
              <h3>Auto-Roll</h3>
              <div className="checkbox-group">
                <input className="checkbox" type="checkbox" name="auto_roll_enabled" checked={formData.auto_roll_enabled} onChange={handleChange} id="auto_roll" />
                <label htmlFor="auto_roll">Enable automatic daily Roll</label>
              </div>
              {formData.auto_roll_enabled && (
                <div className="form-group" style={{ marginTop: '1rem' }}>
                  <label className="form-label">Auto Roll Time</label>
                  <input className="form-input" type="time" name="auto_roll_time" value={formData.auto_roll_time} onChange={handleChange} />
                </div>
              )}
            </div>
          </div>
        )}

        {/* Backups Tab */}
        {activeTab === 'backups' && (
          <div>
            <div className="info-box" style={{ margin: '0 2rem', marginTop: '1.5rem' }}>
              Automatic database backups protect your data. Backups are stored locally and optionally uploaded to Google Drive.
            </div>

            <div className="settings-section">
              <h3>Auto-Backup</h3>
              <div className="checkbox-group">
                <input className="checkbox" type="checkbox" name="auto_backup_enabled" checked={formData.auto_backup_enabled} onChange={handleChange} id="auto_backup" />
                <label htmlFor="auto_backup">Enable automatic backups</label>
              </div>

              {formData.auto_backup_enabled && (
                <>
                  <div className="form-group" style={{ marginTop: '1rem' }}>
                    <label className="form-label">Backup Time (daily)</label>
                    <input className="form-input" type="time" name="backup_time" value={formData.backup_time} onChange={handleChange} />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Backup Interval (days)</label>
                    <input className="form-input" type="number" name="backup_interval_days" value={formData.backup_interval_days} onChange={handleChange} min="1" max="30" />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Keep Local Backups</label>
                    <input className="form-input" type="number" name="backup_keep_local_count" value={formData.backup_keep_local_count} onChange={handleChange} min="1" max="100" />
                  </div>
                </>
              )}
            </div>

            <div className="settings-section">
              <h3>Google Drive Integration</h3>
              <div className="checkbox-group">
                <input className="checkbox" type="checkbox" name="google_drive_enabled" checked={formData.google_drive_enabled} onChange={handleChange} id="google_drive" />
                <label htmlFor="google_drive">Upload backups to Google Drive</label>
              </div>
              {formData.google_drive_enabled && (
                <div className="info-box" style={{ marginTop: '1rem', backgroundColor: 'rgba(255, 193, 7, 0.1)' }}>
                  <strong>Note:</strong> Requires Google Drive API credentials to be configured on the server.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Rest Days Tab */}
        {activeTab === 'rest' && (
          <div>
            <div className="info-box" style={{ margin: '0 2rem', marginTop: '1.5rem' }}>
              Rest days are penalty-free days regardless of task/habit completion.
            </div>

            <div className="settings-section">
              <h3>Add Rest Day</h3>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <input
                  className="form-input"
                  type="date"
                  value={newRestDay}
                  onChange={(e) => setNewRestDay(e.target.value)}
                  style={{ flex: 1 }}
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
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>No rest days scheduled</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {restDays.map((day) => (
                    <div key={day.id} style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '0.75rem',
                      background: 'var(--bg-primary)',
                      border: '1px solid var(--border)'
                    }}>
                      <span>{new Date(day.date).toLocaleDateString()}</span>
                      <button
                        type="button"
                        onClick={() => deleteRestDay(day.id)}
                        className="btn-small btn-danger"
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
        <div className="form-actions">
          <button type="submit" disabled={saving} className="btn btn-primary">
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  );
}

export default Settings;
