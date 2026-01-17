import { useState, useEffect } from 'react';
import axios from 'axios';

import { API_URL } from '../config';
import { getApiKey } from '../api';

function Backups() {
  const [backups, setBackups] = useState([]);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    fetchBackups();
    fetchSettings();
  }, []);

  const fetchBackups = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/backups`, {
        headers: { 'X-API-Key': getApiKey() }
      });
      setBackups(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch backups:', error);
      setLoading(false);
    }
  };

  const fetchSettings = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/settings`, {
        headers: { 'X-API-Key': getApiKey() }
      });
      setSettings(response.data);
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    }
  };

  const createBackup = async () => {
    setCreating(true);
    try {
      await axios.post(`${API_URL}/api/backups/create`, {}, {
        headers: { 'X-API-Key': getApiKey() }
      });
      alert('Backup created successfully!');
      fetchBackups();
      fetchSettings();
    } catch (error) {
      console.error('Failed to create backup:', error);
      alert('Failed to create backup');
    } finally {
      setCreating(false);
    }
  };

  const downloadBackup = async (backupId, filename) => {
    try {
      const response = await axios.get(
        `${API_URL}/api/backups/${backupId}/download`,
        {
          headers: { 'X-API-Key': getApiKey() },
          responseType: 'blob'
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to download backup:', error);
      alert('Failed to download backup');
    }
  };

  const deleteBackup = async (backupId) => {
    if (!confirm('Are you sure you want to delete this backup?')) {
      return;
    }

    try {
      await axios.delete(`${API_URL}/api/backups/${backupId}`, {
        headers: { 'X-API-Key': getApiKey() }
      });
      fetchBackups();
    } catch (error) {
      console.error('Failed to delete backup:', error);
      alert('Failed to delete backup');
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('ru-RU', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getTimeSinceLastBackup = () => {
    if (!settings || !settings.last_backup_date) {
      return 'Never';
    }

    const now = new Date();
    const lastBackup = new Date(settings.last_backup_date);
    const diffMs = now - lastBackup;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 60) {
      return `${diffMins} min ago`;
    } else if (diffHours < 24) {
      return `${diffHours} hours ago`;
    } else {
      return `${diffDays} days ago`;
    }
  };

  const getBackupStatus = () => {
    if (!settings || !settings.last_backup_date) {
      return 'error';
    }

    const now = new Date();
    const lastBackup = new Date(settings.last_backup_date);
    const diffHours = (now - lastBackup) / (1000 * 60 * 60);

    if (diffHours < 24) return 'ok';
    if (diffHours < 24 * 7) return 'warning';
    return 'error';
  };

  if (loading) {
    return <div className="loading">LOADING_BACKUPS...</div>;
  }

  const backupStatus = getBackupStatus();

  return (
    <div>
      {/* Action Bar */}
      <div className="action-bar">
        <button
          className="btn btn-primary"
          onClick={createBackup}
          disabled={creating}
        >
          {creating ? '[ CREATING... ]' : '[ + CREATE_BACKUP ]'}
        </button>
      </div>

      {/* Status Widget */}
      <div className="widget">
        <div className="widget-header">
          <span className="widget-title">[STATUS]</span>
          <span className={`widget-status ${backupStatus === 'ok' ? 'status-ok' : backupStatus === 'warning' ? 'status-warning' : 'status-error'}`}>
            {backupStatus === 'ok' ? 'OK' : backupStatus === 'warning' ? 'WARNING' : 'OUTDATED'}
          </span>
        </div>
        <div className="widget-body">
          <div className="backup-info">
            <div className="backup-info-row">
              <span className="backup-label">LAST_BACKUP:</span>
              <span className="backup-value">{getTimeSinceLastBackup()}</span>
              {settings && settings.last_backup_date && (
                <span className="backup-date">({formatDate(settings.last_backup_date)})</span>
              )}
            </div>
            {settings && (
              <div className="backup-info-row">
                <span className="backup-label">AUTO_BACKUP:</span>
                <span className="backup-value">{settings.auto_backup_enabled ? 'ENABLED' : 'DISABLED'}</span>
                {settings.auto_backup_enabled && (
                  <>
                    <span className="backup-meta">| Every {settings.backup_interval_days}d at {settings.backup_time}</span>
                    <span className="backup-meta">| Keep: {settings.backup_keep_local_count}</span>
                    {settings.google_drive_enabled && <span className="backup-meta">| GDrive: ON</span>}
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Backup History Widget */}
      <div className="widget">
        <div className="widget-header">
          <span className="widget-title">[BACKUP_HISTORY]</span>
          <span className="widget-count">{backups.length}</span>
        </div>
        <div className="widget-body">
          {backups.length === 0 ? (
            <div className="empty-state">
              No backups found. Create your first backup.
            </div>
          ) : (
            <div className="task-list">
              {backups.map((backup) => (
                <div key={backup.id} className="task-item">
                  <div className="task-header">
                    <div className="task-title">{backup.filename}</div>
                    <div className="task-actions">
                      <button
                        className="btn btn-small btn-primary"
                        onClick={() => downloadBackup(backup.id, backup.filename)}
                      >
                        Download
                      </button>
                      <button
                        className="btn btn-small btn-danger"
                        onClick={() => deleteBackup(backup.id)}
                      >
                        ×
                      </button>
                    </div>
                  </div>
                  <div className="task-meta">
                    <span>{formatDate(backup.created_at)}</span>
                    <span>{formatFileSize(backup.size_bytes)}</span>
                    <span>{backup.backup_type.toUpperCase()}</span>
                    {backup.uploaded_to_drive && <span>GDRIVE</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Backups;
