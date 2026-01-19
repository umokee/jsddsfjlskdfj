import React, { useState, useEffect } from 'react';
import { schedulerApi } from '../services/apiService';
import './SchedulerStatus.css';

const SchedulerStatus = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const loadStatus = async () => {
    try {
      const response = await schedulerApi.getStatus();
      setStatus(response.data);
      setError(null);
    } catch (err) {
      console.error('Failed to load scheduler status:', err);
      setError('Failed to load scheduler status');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();

    // Auto-refresh every 10 seconds if enabled
    if (autoRefresh) {
      const interval = setInterval(loadStatus, 10000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  const getStatusBadge = (job) => {
    if (job.last_error) {
      return <span className="status-badge status-error">ERROR</span>;
    }
    if (job.executions > 0) {
      return <span className="status-badge status-active">ACTIVE</span>;
    }
    return <span className="status-badge status-idle">IDLE</span>;
  };

  const formatTime = (isoString) => {
    if (!isoString) return 'Never';
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  const formatNextRun = (seconds) => {
    if (seconds === null || seconds === undefined) return 'N/A';
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}m ${secs}s`;
  };

  if (loading) {
    return <div className="scheduler-status loading">Loading scheduler status...</div>;
  }

  if (error) {
    return (
      <div className="scheduler-status error">
        <h2>⚠️ Error</h2>
        <p>{error}</p>
        <button onClick={loadStatus}>Retry</button>
      </div>
    );
  }

  if (!status) {
    return null;
  }

  return (
    <div className="scheduler-status">
      <div className="scheduler-header">
        <h2>🤖 Background Scheduler Status</h2>
        <div className="header-controls">
          <label>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (10s)
          </label>
          <button onClick={loadStatus} className="refresh-btn">
            🔄 Refresh Now
          </button>
        </div>
      </div>

      {/* Overall Status */}
      <div className="status-overview">
        <div className="status-card">
          <div className="status-label">Status</div>
          <div className={`status-value ${status.running ? 'running' : 'stopped'}`}>
            {status.running ? '✅ RUNNING' : '❌ STOPPED'}
          </div>
        </div>
        <div className="status-card">
          <div className="status-label">Uptime</div>
          <div className="status-value">{status.uptime_human || 'N/A'}</div>
        </div>
        <div className="status-card">
          <div className="status-label">Started At</div>
          <div className="status-value">{formatTime(status.started_at)}</div>
        </div>
        <div className="status-card">
          <div className="status-label">Current Time</div>
          <div className="status-value">{formatTime(status.current_time)}</div>
        </div>
      </div>

      {/* Jobs */}
      <div className="jobs-section">
        <h3>Scheduled Jobs</h3>
        {status.jobs && status.jobs.map((job) => (
          <div key={job.id} className="job-card">
            <div className="job-header">
              <h4>{job.name}</h4>
              {getStatusBadge(job)}
            </div>

            <div className="job-stats">
              <div className="stat">
                <span className="stat-label">Checks:</span>
                <span className="stat-value">{job.checks.toLocaleString()}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Executions:</span>
                <span className="stat-value">{job.executions.toLocaleString()}</span>
              </div>
              <div className="stat">
                <span className="stat-label">Next Run:</span>
                <span className="stat-value">{formatNextRun(job.seconds_until_next)}</span>
              </div>
            </div>

            <div className="job-details">
              <div className="detail-row">
                <span className="detail-label">Last Check:</span>
                <span className="detail-value">{formatTime(job.last_check)}</span>
              </div>
              <div className="detail-row">
                <span className="detail-label">Last Execution:</span>
                <span className="detail-value">{formatTime(job.last_execution)}</span>
              </div>
              {job.last_error && (
                <div className="detail-row error-row">
                  <span className="detail-label">Last Error:</span>
                  <span className="detail-value error-text">{job.last_error}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Settings */}
      <div className="settings-section">
        <h3>Automation Settings</h3>
        <div className="settings-grid">
          <div className="setting-item">
            <strong>Auto Roll:</strong>
            <span className={status.settings.auto_roll_enabled ? 'enabled' : 'disabled'}>
              {status.settings.auto_roll_enabled ? `✅ Enabled at ${status.settings.auto_roll_time}` : '❌ Disabled'}
            </span>
          </div>
          <div className="setting-item">
            <strong>Auto Penalties:</strong>
            <span className={status.settings.auto_penalties_enabled ? 'enabled' : 'disabled'}>
              {status.settings.auto_penalties_enabled ? `✅ Enabled at ${status.settings.penalty_time}` : '❌ Disabled'}
            </span>
          </div>
          <div className="setting-item">
            <strong>Auto Backup:</strong>
            <span className={status.settings.auto_backup_enabled ? 'enabled' : 'disabled'}>
              {status.settings.auto_backup_enabled
                ? `✅ Enabled at ${status.settings.backup_time} (every ${status.settings.backup_interval_days} days)`
                : '❌ Disabled'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SchedulerStatus;
