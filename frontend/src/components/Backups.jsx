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
      fetchSettings(); // Refresh last_backup_date
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

      // Create download link
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
      return 'error'; // red
    }

    const now = new Date();
    const lastBackup = new Date(settings.last_backup_date);
    const diffHours = (now - lastBackup) / (1000 * 60 * 60);

    if (diffHours < 24) return 'ok'; // green
    if (diffHours < 24 * 7) return 'warning'; // yellow
    return 'error'; // red
  };

  if (loading) {
    return <div className="backups">Loading backups...</div>;
  }

  const backupStatus = getBackupStatus();

  return (
    <div className="backups">
      <div className="backups-header">
        <h2>DATABASE BACKUPS</h2>
        <button
          className="btn btn-primary"
          onClick={createBackup}
          disabled={creating}
        >
          {creating ? 'CREATING...' : '[+] BACKUP NOW'}
        </button>
      </div>

      {/* Last Backup Status */}
      <div className={`backup-status backup-status-${backupStatus}`}>
        <div className="status-indicator"></div>
        <div className="status-info">
          <strong>Last Backup:</strong> {getTimeSinceLastBackup()}
          {settings && settings.last_backup_date && (
            <span className="status-date"> ({formatDate(settings.last_backup_date)})</span>
          )}
        </div>
      </div>

      {/* Auto-Backup Info */}
      {settings && (
        <div className="info-box">
          <strong>Auto-Backup:</strong> {settings.auto_backup_enabled ? 'ENABLED' : 'DISABLED'}
          {settings.auto_backup_enabled && (
            <>
              {' | '}
              <strong>Schedule:</strong> Every {settings.backup_interval_days} day(s) at {settings.backup_time}
              {' | '}
              <strong>Keep:</strong> Last {settings.backup_keep_local_count} backups
              {settings.google_drive_enabled && ' | Google Drive: ENABLED'}
            </>
          )}
        </div>
      )}

      {/* Backups List */}
      <div className="backups-list">
        <h3>BACKUP HISTORY ({backups.length})</h3>

        {backups.length === 0 ? (
          <p className="no-backups">No backups found. Create your first backup above.</p>
        ) : (
          <div className="backup-items">
            {backups.map((backup) => (
              <div key={backup.id} className="backup-item">
                <div className="backup-info">
                  <div className="backup-filename">{backup.filename}</div>
                  <div className="backup-meta">
                    <span className="backup-date">{formatDate(backup.created_at)}</span>
                    <span className="backup-size">{formatFileSize(backup.size_bytes)}</span>
                    <span className={`backup-type backup-type-${backup.backup_type}`}>
                      {backup.backup_type.toUpperCase()}
                    </span>
                    {backup.uploaded_to_drive && (
                      <span className="backup-cloud">☁ GOOGLE DRIVE</span>
                    )}
                  </div>
                </div>
                <div className="backup-actions">
                  <button
                    className="btn-small btn-primary"
                    onClick={() => downloadBackup(backup.id, backup.filename)}
                    title="Download"
                  >
                    ↓ DOWNLOAD
                  </button>
                  <button
                    className="btn-small btn-danger"
                    onClick={() => deleteBackup(backup.id)}
                    title="Delete"
                  >
                    × DELETE
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Backups;
