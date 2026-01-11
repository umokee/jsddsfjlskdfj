import { useState, useEffect } from 'react';
import {
  getStats,
  getCurrentTask,
  getPendingTasks,
  getHabits,
  startTask,
  stopTask,
  completeTask,
  rollTasks,
  createTask,
  deleteTask,
  getApiKey,
  setApiKey as setApiKeyStorage,
  clearApiKey
} from './api';
import TaskForm from './components/TaskForm';
import TaskList from './components/TaskList';
import HabitList from './components/HabitList';

function App() {
  const [apiKey, setApiKey] = useState(getApiKey());
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [stats, setStats] = useState(null);
  const [currentTask, setCurrentTask] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [habits, setHabits] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showTaskForm, setShowTaskForm] = useState(false);

  useEffect(() => {
    if (apiKey) {
      loadData();
    }
  }, [apiKey]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, currentRes, tasksRes, habitsRes] = await Promise.all([
        getStats(),
        getCurrentTask(),
        getPendingTasks(),
        getHabits()
      ]);

      setStats(statsRes.data);
      setCurrentTask(currentRes.data);
      setTasks(tasksRes.data);
      setHabits(habitsRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load data');
      if (err.response?.status === 401) {
        clearApiKey();
        setApiKey('');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSetApiKey = () => {
    if (apiKeyInput.trim()) {
      setApiKeyStorage(apiKeyInput);
      setApiKey(apiKeyInput);
      setApiKeyInput('');
    }
  };

  const handleStart = async (taskId = null) => {
    try {
      await startTask(taskId);
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start task');
    }
  };

  const handleStop = async () => {
    try {
      await stopTask();
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to stop task');
    }
  };

  const handleComplete = async (taskId = null) => {
    try {
      await completeTask(taskId);
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to complete task');
    }
  };

  const handleRoll = async () => {
    try {
      await rollTasks();
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to roll tasks');
    }
  };

  const handleCreateTask = async (taskData) => {
    try {
      await createTask(taskData);
      await loadData();
      setShowTaskForm(false);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create task');
    }
  };

  const handleDeleteTask = async (taskId) => {
    try {
      await deleteTask(taskId);
      await loadData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete task');
    }
  };

  if (!apiKey) {
    return (
      <div className="app">
        <div className="api-key-setup">
          <h2 className="api-key-title">Task Manager</h2>
          <div className="api-key-info">
            Enter your API key to access the task manager. Default key: <code>your-secret-key-change-me</code>
          </div>
          {error && <div className="error-message">{error}</div>}
          <div className="form-group">
            <label className="form-label">API Key</label>
            <input
              type="password"
              className="form-input"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSetApiKey()}
              placeholder="Enter your API key"
            />
          </div>
          <button className="btn btn-primary" onClick={handleSetApiKey} style={{ width: '100%' }}>
            Connect
          </button>
        </div>
      </div>
    );
  }

  if (loading && !stats) {
    return (
      <div className="app">
        <div className="loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="header">
        <h1>TASK MANAGER</h1>
        <div className="stats">
          <div className="stat-item">
            <span>Done Today:</span>
            <span className="stat-value">{stats?.done_today || 0}</span>
          </div>
          <div className="stat-item">
            <span>Pending Today:</span>
            <span className="stat-value">{stats?.pending_today || 0}</span>
          </div>
          <div className="stat-item">
            <span>Total Pending:</span>
            <span className="stat-value">{stats?.total_pending || 0}</span>
          </div>
        </div>
      </header>

      {error && <div className="error-message">{error}</div>}

      {currentTask && (
        <div className="current-task">
          <div className="current-task-title">CURRENT TASK</div>
          <div className="current-task-desc">{currentTask.description}</div>
          <div className="task-meta">
            {currentTask.project && <span>Project: {currentTask.project}</span>}
            <span>Priority: {currentTask.priority}/10</span>
            <span>Energy: {currentTask.energy}/5</span>
          </div>
          <div className="current-task-actions">
            <button className="btn" onClick={handleStop}>Stop</button>
            <button className="btn btn-primary" onClick={() => handleComplete()}>Complete</button>
          </div>
        </div>
      )}

      <div style={{ marginBottom: '1rem', display: 'flex', gap: '1rem' }}>
        <button className="btn btn-primary" onClick={() => setShowTaskForm(!showTaskForm)}>
          {showTaskForm ? 'Cancel' : 'New Task'}
        </button>
        <button className="btn" onClick={handleRoll}>Roll Daily Plan</button>
        {!currentTask && (
          <button className="btn btn-primary" onClick={() => handleStart()}>
            Start Next Task
          </button>
        )}
      </div>

      {showTaskForm && (
        <div className="section" style={{ marginBottom: '2rem' }}>
          <TaskForm onSubmit={handleCreateTask} onCancel={() => setShowTaskForm(false)} />
        </div>
      )}

      <div className="container">
        <div className="section">
          <div className="section-header">
            <h2 className="section-title">Tasks</h2>
          </div>
          <TaskList
            tasks={tasks}
            onStart={handleStart}
            onComplete={handleComplete}
            onDelete={handleDeleteTask}
          />
        </div>

        <div className="section">
          <div className="section-header">
            <h2 className="section-title">Habits</h2>
          </div>
          <HabitList
            habits={habits}
            onStart={handleStart}
            onComplete={handleComplete}
            onDelete={handleDeleteTask}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
