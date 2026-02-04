/**
 * Settings component.
 */
import { useState, useEffect } from 'react';
import { useSettings } from '../../../contexts';
import { useRestDays } from '../hooks/useRestDays';

function Settings() {
  const { settings, updateSettings } = useSettings();
  const { restDays, addRestDay, deleteRestDay } = useRestDays();
  const [formData, setFormData] = useState({
    max_tasks_per_day: 10,
    points_per_task_base: 10,
    points_per_habit_base: 10,
    energy_mult_base: 0.6,
    energy_mult_step: 0.2,
    minutes_per_energy_unit: 20,
    min_work_time_seconds: 120,
    streak_log_factor: 0.15,
    routine_points_fixed: 6,
    completion_bonus_full: 0.10,
    completion_bonus_good: 0.05,
    idle_penalty: 30,
    incomplete_penalty_percent: 0.5,
    missed_habit_penalty_base: 15,
    progressive_penalty_factor: 0.1,
    progressive_penalty_max: 1.5,
    penalty_streak_reset_days: 2,
    day_start_enabled: false,
    day_start_time: "06:00",
    roll_available_time: "00:00",
    auto_penalties_enabled: true,
    penalty_time: "00:01",
    auto_roll_enabled: false,
    auto_roll_time: "06:00",
    auto_mood_timeout_hours: 4,
    auto_backup_enabled: true,
    backup_time: "03:00",
    backup_interval_days: 1,
    backup_keep_local_count: 10,
    google_drive_enabled: false,
  });
  const [saving, setSaving] = useState(false);
  const [newRestDay, setNewRestDay] = useState('');
  const [activeTab, setActiveTab] = useState('points');

  useEffect(() => {
    if (settings) {
      setFormData(settings);
    }
  }, [settings]);

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

    const success = await updateSettings(formData);
    if (success) {
      alert('Settings saved successfully!');
    } else {
      alert('Failed to save settings');
    }
    setSaving(false);
  };

  const handleAddRestDay = async (e) => {
    e.preventDefault();
    if (!newRestDay) return;

    try {
      await addRestDay(newRestDay);
      setNewRestDay('');
    } catch (error) {
      alert('Failed to add rest day');
    }
  };

  const calcEnergyMult = (energy) => formData.energy_mult_base + (energy * formData.energy_mult_step);
  const calcStreakBonus = (streak) => 1 + Math.log2(streak + 1) * formData.streak_log_factor;

  if (!settings) {
    return <div className="settings">Loading settings...</div>;
  }

  return (
    <div className="settings">
      <div className="settings-header">
        <h2>Settings</h2>
      </div>

      <div className="settings-tabs">
        <button type="button" className={`tab-button ${activeTab === 'points' ? 'active' : ''}`} onClick={() => setActiveTab('points')}>
          Points & Rewards
        </button>
        <button type="button" className={`tab-button ${activeTab === 'penalties' ? 'active' : ''}`} onClick={() => setActiveTab('penalties')}>
          Penalties
        </button>
        <button type="button" className={`tab-button ${activeTab === 'automation' ? 'active' : ''}`} onClick={() => setActiveTab('automation')}>
          Automation
        </button>
        <button type="button" className={`tab-button ${activeTab === 'backups' ? 'active' : ''}`} onClick={() => setActiveTab('backups')}>
          Backups
        </button>
        <button type="button" className={`tab-button ${activeTab === 'rest' ? 'active' : ''}`} onClick={() => setActiveTab('rest')}>
          Rest Days
        </button>
      </div>

      <form onSubmit={handleSubmit}>
        {activeTab === 'points' && (
          <div>
            <div className="info-box settings-intro">
              <strong>Balanced Progress v2.0</strong> - Points = Base x EnergyMultiplier x TimeQualityFactor x FocusFactor
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
                Formula: {formData.energy_mult_base} + (energy x {formData.energy_mult_step})<br />
                E0-{'>'}x{calcEnergyMult(0).toFixed(1)}, E1-{'>'}x{calcEnergyMult(1).toFixed(1)}, E2-{'>'}x{calcEnergyMult(2).toFixed(1)}, E3-{'>'}x{calcEnergyMult(3).toFixed(1)}, E4-{'>'}x{calcEnergyMult(4).toFixed(1)}, E5-{'>'}x{calcEnergyMult(5).toFixed(1)}
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
              <h3>Streak Bonus (Skill Habits)</h3>
              <div className="info-box">
                Formula: 1 + log2(streak + 1) x {formData.streak_log_factor}<br />
                Streak 0-{'>'}x{calcStreakBonus(0).toFixed(2)}, 5-{'>'}x{calcStreakBonus(5).toFixed(2)}, 10-{'>'}x{calcStreakBonus(10).toFixed(2)}, 30-{'>'}x{calcStreakBonus(30).toFixed(2)}
              </div>
              <div className="form-group">
                <label className="form-label">Log Factor</label>
                <input className="form-input" type="number" step="0.01" name="streak_log_factor" value={formData.streak_log_factor} onChange={handleChange} min="0" max="1" />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'penalties' && (
          <div>
            <div className="info-box settings-intro">
              Penalties are applied during daily Roll. Progressive multiplier increases with consecutive penalty days.
            </div>

            <div className="settings-section">
              <h3>Idle Day Penalty</h3>
              <div className="form-group">
                <label className="form-label">Penalty (0 tasks AND 0 habits)</label>
                <input className="form-input" type="number" name="idle_penalty" value={formData.idle_penalty} onChange={handleChange} min="0" max="500" />
              </div>
            </div>

            <div className="settings-section">
              <h3>Incomplete Day Penalty</h3>
              <div className="form-group">
                <label className="form-label">Penalty Percent of Missed Potential</label>
                <input className="form-input" type="number" step="0.05" name="incomplete_penalty_percent" value={formData.incomplete_penalty_percent} onChange={handleChange} min="0" max="1" />
              </div>
            </div>

            <div className="settings-section">
              <h3>Missed Habits Penalty</h3>
              <div className="form-group">
                <label className="form-label">Base Penalty per Missed Habit</label>
                <input className="form-input" type="number" name="missed_habit_penalty_base" value={formData.missed_habit_penalty_base} onChange={handleChange} min="0" max="500" />
              </div>
            </div>

            <div className="settings-section">
              <h3>Progressive Penalty</h3>
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
            </div>
          </div>
        )}

        {activeTab === 'automation' && (
          <div>
            <div className="settings-section">
              <h3>Day Boundary</h3>
              <div className="checkbox-group" style={{ marginTop: '1rem' }}>
                <input className="checkbox" type="checkbox" name="day_start_enabled" checked={formData.day_start_enabled} onChange={handleChange} id="day_start_enabled" />
                <label htmlFor="day_start_enabled">Enable custom day start time</label>
              </div>
              {formData.day_start_enabled && (
                <div className="form-group" style={{ marginTop: '1rem' }}>
                  <label className="form-label">Day Start Time</label>
                  <input className="form-input" type="time" name="day_start_time" value={formData.day_start_time} onChange={handleChange} />
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
                <>
                  <div className="form-group" style={{ marginTop: '1rem' }}>
                    <label className="form-label">Auto Roll Time</label>
                    <input className="form-input" type="time" name="auto_roll_time" value={formData.auto_roll_time} onChange={handleChange} />
                  </div>
                  <div className="form-group">
                    <label className="form-label">Auto-complete Timeout (hours)</label>
                    <input className="form-input" type="number" name="auto_mood_timeout_hours" value={formData.auto_mood_timeout_hours} onChange={handleChange} min="1" max="24" />
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {activeTab === 'backups' && (
          <div>
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
          </div>
        )}

        {activeTab === 'rest' && (
          <div>
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
                <button type="button" onClick={handleAddRestDay} disabled={!newRestDay} className="btn btn-primary">
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
                      <button type="button" onClick={() => deleteRestDay(day.id)} className="btn-small btn-danger">
                        x
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

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
