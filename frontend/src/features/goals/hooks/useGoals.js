/**
 * Goals hook - manages goals state and operations.
 */
import { useState, useCallback, useEffect } from 'react';
import { goalsApi } from '../../../shared/api';
import { useAuth } from '../../../contexts';

export function useGoals() {
  const { isAuthenticated } = useAuth();
  const [goals, setGoals] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadGoals = useCallback(async (includeAchieved = false) => {
    if (!isAuthenticated) return;

    setLoading(true);
    setError(null);

    try {
      const response = await goalsApi.getAll(includeAchieved);
      setGoals(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load goals');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  const createGoal = useCallback(async (goalData) => {
    const response = await goalsApi.create(goalData);
    await loadGoals();
    return response.data;
  }, [loadGoals]);

  const deleteGoal = useCallback(async (id) => {
    await goalsApi.delete(id);
    await loadGoals();
  }, [loadGoals]);

  const claimReward = useCallback(async (id) => {
    await goalsApi.claim(id);
    await loadGoals();
  }, [loadGoals]);

  // Initial load
  useEffect(() => {
    if (isAuthenticated) {
      loadGoals();
    }
  }, [isAuthenticated, loadGoals]);

  return {
    goals,
    loading,
    error,
    loadGoals,
    createGoal,
    deleteGoal,
    claimReward,
  };
}

export default useGoals;
