/**
 * Points hook - manages points state and operations.
 */
import { useState, useCallback, useEffect } from 'react';
import { pointsApi } from '../../../shared/api';
import { useAuth } from '../../../contexts';

export function usePoints() {
  const { isAuthenticated } = useAuth();
  const [currentPoints, setCurrentPoints] = useState(0);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadCurrentPoints = useCallback(async () => {
    if (!isAuthenticated) return;

    try {
      const response = await pointsApi.getCurrent();
      setCurrentPoints(response.data.points || 0);
    } catch (err) {
      console.error('Failed to load points:', err);
    }
  }, [isAuthenticated]);

  const loadHistory = useCallback(async (days = 7) => {
    if (!isAuthenticated) return;

    setLoading(true);
    setError(null);

    try {
      const response = await pointsApi.getHistory(days);
      setHistory(response.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load history');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  const getDayDetails = useCallback(async (date) => {
    try {
      const response = await pointsApi.getHistoryByDate(date);
      return response.data;
    } catch (err) {
      console.error('Failed to fetch day details:', err);
      return null;
    }
  }, []);

  // Initial load
  useEffect(() => {
    if (isAuthenticated) {
      loadCurrentPoints();
    }
  }, [isAuthenticated, loadCurrentPoints]);

  return {
    currentPoints,
    history,
    loading,
    error,
    loadCurrentPoints,
    loadHistory,
    getDayDetails,
  };
}

export default usePoints;
