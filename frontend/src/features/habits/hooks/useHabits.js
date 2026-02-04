/**
 * Habits hook - manages habit state and operations.
 */
import { useState, useCallback, useEffect } from 'react';
import { taskApi } from '../../../shared/api';
import { useAuth } from '../../../contexts';

export function useHabits() {
  const { isAuthenticated } = useAuth();
  const [habits, setHabits] = useState([]);
  const [todayHabits, setTodayHabits] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadHabits = useCallback(async () => {
    if (!isAuthenticated) return;

    setLoading(true);
    setError(null);

    try {
      const [habitsRes, todayRes] = await Promise.all([
        taskApi.getHabits(),
        taskApi.getTodayHabits(),
      ]);

      setHabits(habitsRes.data);
      setTodayHabits(todayRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load habits');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  // Initial load
  useEffect(() => {
    if (isAuthenticated) {
      loadHabits();
    }
  }, [isAuthenticated, loadHabits]);

  return {
    habits,
    todayHabits,
    loading,
    error,
    loadHabits,
  };
}

export default useHabits;
