/**
 * Rest days hook.
 */
import { useState, useCallback, useEffect } from 'react';
import { restDaysApi } from '../../../shared/api';
import { useAuth } from '../../../contexts';

export function useRestDays() {
  const { isAuthenticated } = useAuth();
  const [restDays, setRestDays] = useState([]);
  const [loading, setLoading] = useState(false);

  const loadRestDays = useCallback(async () => {
    if (!isAuthenticated) return;

    setLoading(true);
    try {
      const response = await restDaysApi.getAll();
      setRestDays(response.data);
    } catch (error) {
      console.error('Failed to fetch rest days:', error);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  const addRestDay = useCallback(async (date) => {
    await restDaysApi.create({ date });
    await loadRestDays();
  }, [loadRestDays]);

  const deleteRestDay = useCallback(async (id) => {
    await restDaysApi.delete(id);
    await loadRestDays();
  }, [loadRestDays]);

  useEffect(() => {
    if (isAuthenticated) {
      loadRestDays();
    }
  }, [isAuthenticated, loadRestDays]);

  return {
    restDays,
    loading,
    loadRestDays,
    addRestDay,
    deleteRestDay,
  };
}

export default useRestDays;
