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
import Backups from './components/Backups';
import SchedulerStatus from './components/SchedulerStatus';

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
  const [currentView, setCurrentView] = useState('tasks');
  const [currentPoints, setCurrentPoints] = useState(0);
  const [canRollToday, setCanRollToday] = useState(true);
  const [rollMessage, setRollMessage] = useState('');

  useEffect(() => {
    if (apiKey) {
      loadData();
      loadPoints();
      checkCanRoll();

      const interval = setInterval(() => {
        loadData();
        loadPoints();
        checkCanRoll();
      }, 30000);

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
      await loadPoints();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to complete task');
    }
  };

  const handleRoll = async () => {
    try {
      await rollTasks();
      await loadData();
      await checkCanRoll();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to roll tasks');
    }
  };

  const handleSubmitTask = async (taskData) => {
    try {
      if (editingTask) {
        await updateTask(editingTask.id, taskData);
      } else {
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
      <div className="login-screen">
        <div className="login-box">
          <div className="login-header">
            <div className="logo">TASK_MANAGER</div>
            <div className="version">v1.0</div>
          </div>
          <div className="login-body">
            <div className="login-info">
              Enter API key to authenticate
            </div>
            {error && <div className="error-message">{error}</div>}
            <div className="form-group">
              <input
                type="password"
                className="form-input"
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSetApiKey()}
                placeholder="API_KEY"
              />
            </div>
            <button className="btn btn-primary btn-block" onClick={handleSetApiKey}>
              AUTHENTICATE
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (loading && !stats) {
    return (
      <div className="login-screen">
        <div className="loading">LOADING...</div>
      </div>
    );
  }

  const navItems = [
    { id: 'tasks', label: '[ ] TASKS' },
    { id: 'points', label: '[*] POINTS' },
    { id: 'goals', label: '[>] GOALS' },
    { id: 'calculator', label: '[=] CALC' },
    { id: 'backups', label: '[#] BACKUPS' },
    { id: 'scheduler', label: '[🤖] SCHEDULER' },
    { id: 'settings', label: '[~] CONFIG' },
  ];

  return (
    <div className="command-center">
      {/* Command Bar */}
      <nav className="command-bar">
        <div className="command-bar-left">
          <div className="app-title">TASK_MANAGER</div>
          <div className="nav-tabs">
            {navItems.map(item => (
              <button
                key={item.id}
                className={`nav-tab ${currentView === item.id ? 'active' : ''}`}
                onClick={() => setCurrentView(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        <div className="command-bar-right">
          <div className="status-bar">
            <div className="status-item">
              <span className="status-label">POINTS</span>
              <span className="status-value">{currentPoints}</span>
            </div>
            <div className="status-divider">|</div>
            <div className="status-item">
              <span className="status-label">DONE</span>
              <span className="status-value">{stats?.done_today || 0}</span>
            </div>
            <div className="status-divider">|</div>
            <div className="status-item">
              <span className="status-label">PENDING</span>
              <span className="status-value">{stats?.pending_today || 0}</span>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="command-content">
        {error && <div className="error-message">{error}</div>}

        {currentView === 'points' && <PointsDisplay />}
        {currentView === 'goals' && <PointsGoals currentPoints={currentPoints} />}
        {currentView === 'calculator' && <PointsCalculator />}
        {currentView === 'backups' && <Backups />}
        {currentView === 'scheduler' && <SchedulerStatus />}
        {currentView === 'settings' && <Settings />}

        {currentView === 'tasks' && (
          <>
            {/* Current Task Widget */}
            {currentTask && (
              <div className="widget current-task-widget">
                <div className="widget-header">
                  <span className="widget-title">[ACTIVE]</span>
                  <span className="widget-status">IN_PROGRESS</span>
                </div>
                <div className="widget-body">
                  <div className="task-description">{currentTask.description}</div>
                  {currentTask.started_at && (
                    <div className="task-timer">
                      <Timer startTime={currentTask.started_at} />
                    </div>
                  )}
                  <div className="task-metadata">
                    {currentTask.project && <span>PROJECT: {currentTask.project}</span>}
                    <span>PRIORITY: {currentTask.priority}/10</span>
                    <span>ENERGY: {currentTask.energy}/5</span>
                  </div>
                  <div className="task-actions">
                    {currentTask.status === 'active' ? (
                      <button className="btn btn-secondary" onClick={handleStop}>PAUSE</button>
                    ) : (
                      <button className="btn btn-primary" onClick={() => handleStart(currentTask.id)}>RESUME</button>
                    )}
                    <button className="btn btn-success" onClick={() => handleComplete()}>COMPLETE</button>
                  </div>
                </div>
              </div>
            )}

            {/* Action Bar */}
            <div className="action-bar">
              <button
                className="btn btn-primary"
                onClick={() => { setShowTaskForm(!showTaskForm); setEditingTask(null); }}
              >
                {showTaskForm ? '[ CANCEL ]' : '[ + NEW_TASK ]'}
              </button>
              {canRollToday ? (
                <button className="btn btn-secondary" onClick={handleRoll}>
                  [ ROLL_DAILY_PLAN ]
                </button>
              ) : (
                rollMessage && <span className="roll-message">{rollMessage}</span>
              )}
              {!currentTask && (
                <button className="btn btn-success" onClick={() => handleStart()}>
                  [ >> START_NEXT ]
                </button>
              )}
            </div>

            {/* Task Form */}
            {showTaskForm && (
              <div className="widget form-widget">
                <div className="widget-header">
                  <span className="widget-title">{editingTask ? '[EDIT_TASK]' : '[NEW_TASK]'}</span>
                </div>
                <div className="widget-body">
                  <TaskForm
                    onSubmit={handleSubmitTask}
                    onCancel={handleCancelEdit}
                    editTask={editingTask}
                  />
                </div>
              </div>
            )}

            {/* Today Section */}
            {(todayTasks.length > 0 || todayHabits.length > 0) && (
              <div className="widget today-widget">
                <div className="widget-header">
                  <span className="widget-title">[TODAY]</span>
                  <span className="widget-count">{todayTasks.length + todayHabits.length} items</span>
                </div>
                <div className="widget-body">
                  {todayTasks.length > 0 && (
                    <div className="section-group">
                      <h3 className="section-subtitle">TASKS</h3>
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
                    <div className="section-group">
                      <h3 className="section-subtitle">HABITS</h3>
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
              </div>
            )}

            {/* Task Lists Grid */}
            <div className="widget-grid">
              <div className="widget">
                <div className="widget-header">
                  <span className="widget-title">[TASKS]</span>
                  <span className="widget-count">{tasks.length}</span>
                </div>
                <div className="widget-body">
                  <TaskList
                    tasks={tasks}
                    onStart={handleStart}
                    onComplete={handleComplete}
                    onDelete={handleDeleteTask}
                    onEdit={handleEditTask}
                    showAll={true}
                  />
                </div>
              </div>

              <div className="widget">
                <div className="widget-header">
                  <span className="widget-title">[HABITS]</span>
                  <span className="widget-count">{habits.length}</span>
                </div>
                <div className="widget-body">
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
            </div>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
