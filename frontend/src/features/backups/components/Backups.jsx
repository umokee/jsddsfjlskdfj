/**
 * Backups component.
 */
import { useBackups } from '../hooks/useBackups';

function Backups() {
  const {
    backups,
    settings,
    loading,
    creating,
    createBackup,
    downloadBackup,
    deleteBackup
  } = useBackups();

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

  const handleCreate = async () => {
    const success = await createBackup();
    if (success) {
      alert('Backup created successfully!');
    } else {
      alert('Failed to create backup');
    }
  };

  const handleDownload = async (id, filename) => {
    const success = await downloadBackup(id, filename);
    if (!success) {
      alert('Failed to download backup');
    }
  };

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this backup?')) {
      return;
    }
    const success = await deleteBackup(id);
    if (!success) {
      alert('Failed to delete backup');
    }
  };

  if (loading) {
    return <div className="loading">LOADING_BACKUPS...</div>;
  }

  const backupStatus = getBackupStatus();

  return (
    <div>
      <div className="action-bar">
        <button
          className="btn btn-primary"
          onClick={handleCreate}
          disabled={creating}
        >
          {creating ? '[ CREATING... ]' : '[ + CREATE_BACKUP ]'}
        </button>
      </div>

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
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

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
                        onClick={() => handleDownload(backup.id, backup.filename)}
                      >
                        Download
                      </button>
                      <button
                        className="btn btn-small btn-danger"
                        onClick={() => handleDelete(backup.id)}
                      >
                        x
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
