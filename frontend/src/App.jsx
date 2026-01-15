import { useState, useEffect } from 'react';
import {
  getStats,
  getCurrentTask,
  getPendingTasks,
  getHabits,
  getTodayTasks,
  getTodayHabits,
  startTask,
  stopTask,
  completeTask,
  rollTasks,
  canRoll,
  createTask,
  updateTask,
  deleteTask,
  getApiKey,
  setApiKey as setApiKeyStorage,
  clearApiKey
} from './api';
import { API_URL } from './config';
import TaskForm from './components/TaskForm';
import TaskList from './components/TaskList';
import HabitList from './components/HabitList';
import Timer from './components/Timer';
import Settings from './components/Settings';
import PointsDisplay from './components/PointsDisplay';
import PointsGoals from './components/PointsGoals';
import PointsCalculator from './components/PointsCalculator';

function App() {
  const [apiKey, setApiKey] = useState(getApiKey());
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [stats, setStats] = useState(null);
  const [currentTask, setCurrentTask] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [habits, setHabits] = useState([]);
  const [todayTasks, setTodayTasks] = useState([]);
  const [todayHabits, setTodayHabits] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [currentView, setCurrentView] = useState('tasks'); // tasks, points, goals, calculator, settings
  const [currentPoints, setCurrentPoints] = useState(0);
  const [canRollToday, setCanRollToday] = useState(true);
  const [rollMessage, setRollMessage] = useState('');

  useEffect(() => {
    if (apiKey) {
      loadData();
      loadPoints();
      checkCanRoll();

      // Auto-refresh every 30 seconds for reactive UI
      const interval = setInterval(() => {
        loadData();
        loadPoints();
        checkCanRoll();
      }, 30000); // 30 seconds

      return () => clearInterval(interval);
    }
  }, [apiKey]);

  const loadPoints = async () => {
    try {
      const response = await fetch(`${API_URL}/api/points/current`, {
        headers: { 'X-API-Key': apiKey }
      });
      const data = await response.json();
      setCurrentPoints(data.points || 0);
    } catch (err) {
      console.error('Failed to load points:', err);
    }
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statsRes, currentRes, tasksRes, habitsRes, todayTasksRes, todayHabitsRes] = await Promise.all([
        getStats(),
        getCurrentTask(),
        getPendingTasks(),
        getHabits(),
        getTodayTasks(),
        getTodayHabits()
      ]);

      setStats(statsRes.data);
      setCurrentTask(currentRes.data);
      setTasks(tasksRes.data);
      setHabits(habitsRes.data);
      setTodayTasks(todayTasksRes.data);
      setTodayHabits(todayHabitsRes.data);
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

  const checkCanRoll = async () => {
    try {
      const response = await canRoll();
      setCanRollToday(response.data.can_roll);
      setRollMessage(response.data.error_message || '');
    } catch (err) {
      console.error('Failed to check roll status:', err);
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
      await loadPoints(); // Reload points after completion
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to complete task');
    }
  };

  const handleRoll = async () => {
    try {
      await rollTasks();
      await loadData();
      await checkCanRoll(); // Update roll availability
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to roll tasks');
    }
  };

  const handleSubmitTask = async (taskData) => {
    try {
      if (editingTask) {
        // Update existing task
        await updateTask(editingTask.id, taskData);
      } else {
        // Create new task
        await createTask(taskData);
      }
      await loadData();
      setShowTaskForm(false);
      setEditingTask(null);
    } catch (err) {
      const action = editingTask ? 'update' : 'create';
      setError(err.response?.data?.detail || `Failed to ${action} task`);
    }
  };

  const handleEditTask = (task) => {
    setEditingTask(task);
    setShowTaskForm(true);
  };

  const handleCancelEdit = () => {
    setShowTaskForm(false);
    setEditingTask(null);
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
        <div className="nav-buttons" style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          <button
            className={currentView === 'tasks' ? 'btn btn-primary' : 'btn'}
            onClick={() => setCurrentView('tasks')}
          >
            Tasks
          </button>
          <button
            className={currentView === 'points' ? 'btn btn-primary' : 'btn'}
            onClick={() => setCurrentView('points')}
          >
            Points
          </button>
          <button
            className={currentView === 'goals' ? 'btn btn-primary' : 'btn'}
            onClick={() => setCurrentView('goals')}
          >
            Goals
          </button>
          <button
            className={currentView === 'calculator' ? 'btn btn-primary' : 'btn'}
            onClick={() => setCurrentView('calculator')}
          >
            Calculator
          </button>
          <button
            className={currentView === 'settings' ? 'btn btn-primary' : 'btn'}
            onClick={() => setCurrentView('settings')}
          >
            Settings
          </button>
        </div>
        <div className="stats">
          <div className="stat-item">
            <span>Points:</span>
            <span className="stat-value">{currentPoints}</span>
          </div>
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

      {/* Render different views based on currentView */}
      {currentView === 'points' && <PointsDisplay />}
      {currentView === 'goals' && <PointsGoals currentPoints={currentPoints} />}
      {currentView === 'calculator' && <PointsCalculator />}
      {currentView === 'settings' && <Settings onClose={() => setCurrentView('tasks')} />}

      {/* Tasks view */}
      {currentView === 'tasks' && (
        <>
          {currentTask && (
        <div className="current-task">
          <div className="current-task-title">CURRENT TASK</div>
          <div className="current-task-desc">{currentTask.description}</div>
          {currentTask.started_at && (
            <div style={{ textAlign: 'center', margin: '1rem 0' }}>
              <Timer startTime={currentTask.started_at} />
            </div>
          )}
          <div className="task-meta">
            {currentTask.project && <span>Project: {currentTask.project}</span>}
            <span>Priority: {currentTask.priority}/10</span>
            <span>Energy: {currentTask.energy}/5</span>
          </div>
          <div className="current-task-actions">
            {currentTask.status === 'active' ? (
              <button className="btn" onClick={handleStop}>Stop</button>
            ) : (
              <button className="btn btn-primary" onClick={() => handleStart(currentTask.id)}>Start</button>
            )}
            <button className="btn btn-primary" onClick={() => handleComplete()}>Complete</button>
          </div>
        </div>
      )}

      <div style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <button className="btn btn-primary" onClick={() => { setShowTaskForm(!showTaskForm); setEditingTask(null); }}>
            {showTaskForm ? 'Cancel' : 'New Task'}
          </button>
          {canRollToday ? (
            <button className="btn" onClick={handleRoll}>Roll Daily Plan</button>
          ) : (
            rollMessage && (
              <span style={{ color: '#888', fontSize: '0.875rem' }}>{rollMessage}</span>
            )
          )}
          {!currentTask && (
            <button className="btn btn-primary" onClick={() => handleStart()}>
              Start Next Task
            </button>
          )}
        </div>
      </div>

      {showTaskForm && (
        <div className="section" style={{ marginBottom: '2rem' }}>
          <TaskForm
            onSubmit={handleSubmitTask}
            onCancel={handleCancelEdit}
            editTask={editingTask}
          />
        </div>
      )}

      {/* Today Section */}
      {(todayTasks.length > 0 || todayHabits.length > 0) && (
        <div className="section" style={{ marginBottom: '2rem', border: '2px solid #10b981', padding: '1rem' }}>
          <div className="section-header">
            <h2 className="section-title" style={{ color: '#10b981' }}>TODAY</h2>
          </div>

          {todayTasks.length > 0 && (
            <div style={{ marginBottom: todayHabits.length > 0 ? '1rem' : '0' }}>
              <h3 style={{ fontSize: '0.875rem', color: '#888', marginBottom: '0.5rem' }}>Tasks</h3>
              <TaskList
                tasks={todayTasks}
                onStart={handleStart}
                onComplete={handleComplete}
                onDelete={handleDeleteTask}
                onEdit={handleEditTask}
              />
            </div>
          )}

          {todayHabits.length > 0 && (
            <div>
              <h3 style={{ fontSize: '0.875rem', color: '#888', marginBottom: '0.5rem' }}>Habits</h3>
              <HabitList
                habits={todayHabits}
                onStart={handleStart}
                onComplete={handleComplete}
                onDelete={handleDeleteTask}
                onEdit={handleEditTask}
              />
            </div>
          )}
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
            onEdit={handleEditTask}
            showAll={true}
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
            onEdit={handleEditTask}
            showAll={true}
          />
        </div>
      </div>
        </>
      )}
    </div>
  );
}

export default App;
