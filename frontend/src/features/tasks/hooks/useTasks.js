/**
 * Tasks hook - manages task state and operations.
 */
import { useState, useCallback, useEffect } from 'react';
import { taskApi, statsApi } from '../../../shared/api';
import { useAuth } from '../../../contexts';

export function useTasks() {
  const { isAuthenticated } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [todayTasks, setTodayTasks] = useState([]);
  const [currentTask, setCurrentTask] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [canRollToday, setCanRollToday] = useState(true);
  const [rollMessage, setRollMessage] = useState('');

  const loadTasks = useCallback(async () => {
    if (!isAuthenticated) return;

    setLoading(true);
    setError(null);

    try {
      const [statsRes, currentRes, tasksRes, todayRes] = await Promise.all([
        statsApi.get(),
        taskApi.getCurrent(),
        taskApi.getPending(),
        taskApi.getToday(),
      ]);

      setStats(statsRes.data);
      setCurrentTask(currentRes.data);
      setTasks(tasksRes.data);
      setTodayTasks(todayRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tasks');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  const checkCanRoll = useCallback(async () => {
    try {
      const response = await taskApi.canRoll();
      setCanRollToday(response.data.can_roll);
      setRollMessage(response.data.error_message || '');
    } catch (err) {
      console.error('Failed to check roll status:', err);
    }
  }, []);

  const createTask = useCallback(async (taskData) => {
    const response = await taskApi.create(taskData);
    await loadTasks();
    return response.data;
  }, [loadTasks]);

  const updateTask = useCallback(async (id, taskData) => {
    const response = await taskApi.update(id, taskData);
    await loadTasks();
    return response.data;
  }, [loadTasks]);

  const deleteTask = useCallback(async (id) => {
    await taskApi.delete(id);
    await loadTasks();
  }, [loadTasks]);

  const startTask = useCallback(async (taskId = null) => {
    await taskApi.start(taskId);
    await loadTasks();
  }, [loadTasks]);

  const stopTask = useCallback(async () => {
    await taskApi.stop();
    await loadTasks();
  }, [loadTasks]);

  const completeTask = useCallback(async (taskId = null) => {
    await taskApi.complete(taskId);
    await loadTasks();
  }, [loadTasks]);

  const rollTasks = useCallback(async (mood = null) => {
    await taskApi.roll(mood);
    await loadTasks();
    await checkCanRoll();
  }, [loadTasks, checkCanRoll]);

  // Initial load
  useEffect(() => {
    if (isAuthenticated) {
      loadTasks();
      checkCanRoll();
    }
  }, [isAuthenticated, loadTasks, checkCanRoll]);

  return {
    // State
    tasks,
    todayTasks,
    currentTask,
    stats,
    loading,
    error,
    canRollToday,
    rollMessage,
    // Actions
    loadTasks,
    createTask,
    updateTask,
    deleteTask,
    startTask,
    stopTask,
    completeTask,
    rollTasks,
    checkCanRoll,
  };
}

export default useTasks;
