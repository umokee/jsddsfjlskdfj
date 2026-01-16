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
    return <div className="settings">Loading backups...</div>;
  }

  const backupStatus = getBackupStatus();

  return (
    <div className="settings">
      <div className="settings-header">
        <h2>Database Backups</h2>
      </div>

      <div style={{ padding: '2rem' }}>
        {/* Last Backup Status */}
        <div className="settings-section">
          <h3>Backup Status</h3>
          <div className={`backup-status backup-status-${backupStatus}`}>
            <div className="status-indicator"></div>
            <div className="status-info">
              <strong>Last Backup:</strong> {getTimeSinceLastBackup()}
              {settings && settings.last_backup_date && (
                <span className="status-date"> ({formatDate(settings.last_backup_date)})</span>
              )}
            </div>
          </div>

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

          <button
            className="btn btn-primary"
            onClick={createBackup}
            disabled={creating}
            style={{ marginTop: '1rem' }}
          >
            {creating ? 'Creating...' : '[+] Create Backup Now'}
          </button>
        </div>

        {/* Backups List */}
        <div className="settings-section">
          <h3>Backup History ({backups.length})</h3>

          {backups.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', textAlign: 'center', padding: '2rem' }}>
              No backups found. Create your first backup above.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {backups.map((backup) => (
                <div key={backup.id} style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '1rem',
                  background: 'var(--bg-primary)',
                  border: '1px solid var(--border)',
                  transition: 'all 0.15s'
                }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>{backup.filename}</div>
                    <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      <span>{formatDate(backup.created_at)}</span>
                      <span>{formatFileSize(backup.size_bytes)}</span>
                      <span style={{
                        textTransform: 'uppercase',
                        padding: '0.1rem 0.5rem',
                        background: 'var(--bg-tertiary)',
                        border: '1px solid var(--border)',
                        color: backup.backup_type === 'auto' ? 'var(--accent)' : 'var(--success)'
                      }}>
                        {backup.backup_type}
                      </span>
                      {backup.uploaded_to_drive && (
                        <span style={{ color: '#2196f3' }}>☁ Google Drive</span>
                      )}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      className="btn-small btn-primary"
                      onClick={() => downloadBackup(backup.id, backup.filename)}
                    >
                      ↓ Download
                    </button>
                    <button
                      className="btn-small btn-danger"
                      onClick={() => deleteBackup(backup.id)}
                    >
                      × Delete
                    </button>
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
