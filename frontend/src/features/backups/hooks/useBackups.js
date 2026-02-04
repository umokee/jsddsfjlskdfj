/**
 * Backups hook.
 */
import { useState, useCallback, useEffect } from 'react';
import { backupsApi, settingsApi } from '../../../shared/api';
import { useAuth } from '../../../contexts';

export function useBackups() {
  const { isAuthenticated } = useAuth();
  const [backups, setBackups] = useState([]);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  const loadBackups = useCallback(async () => {
    if (!isAuthenticated) return;

    try {
      const response = await backupsApi.getAll();
      setBackups(response.data);
    } catch (error) {
      console.error('Failed to fetch backups:', error);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  const loadSettings = useCallback(async () => {
    if (!isAuthenticated) return;

    try {
      const response = await settingsApi.get();
      setSettings(response.data);
    } catch (error) {
      console.error('Failed to fetch settings:', error);
    }
  }, [isAuthenticated]);

  const createBackup = useCallback(async () => {
    setCreating(true);
    try {
      await backupsApi.create();
      await loadBackups();
      await loadSettings();
      return true;
    } catch (error) {
      console.error('Failed to create backup:', error);
      return false;
    } finally {
      setCreating(false);
    }
  }, [loadBackups, loadSettings]);

  const downloadBackup = useCallback(async (id, filename) => {
    try {
      const response = await backupsApi.download(id);
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      return true;
    } catch (error) {
      console.error('Failed to download backup:', error);
      return false;
    }
  }, []);

  const deleteBackup = useCallback(async (id) => {
    try {
      await backupsApi.delete(id);
      await loadBackups();
      return true;
    } catch (error) {
      console.error('Failed to delete backup:', error);
      return false;
    }
  }, [loadBackups]);

  useEffect(() => {
    if (isAuthenticated) {
      loadBackups();
      loadSettings();
    }
  }, [isAuthenticated, loadBackups, loadSettings]);

  return {
    backups,
    settings,
    loading,
    creating,
    createBackup,
    downloadBackup,
    deleteBackup,
    loadBackups,
  };
}

export default useBackups;
