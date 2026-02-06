/**
 * Main Application Component.
 * Uses feature modules and contexts for state management.
 */
import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useSettings } from '../contexts/SettingsContext';

// Feature components
import { TaskList, TaskForm, useTasks } from '../features/tasks';
import { HabitList, useHabits } from '../features/habits';
import { PointsDisplay, usePoints } from '../features/points';
import { PointsGoals } from '../features/goals';
import { Settings } from '../features/settings';
import { Backups } from '../features/backups';
import { Timer } from '../features/timer';

// Dashboard components
import MorningCheckIn from '../features/dashboard/components/MorningCheckIn';
import PointsCalculator from '../features/points/components/PointsCalculator';

function LoginScreen() {
  const { login } = useAuth();
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [error, setError] = useState(null);

  const handleSetApiKey = () => {
    if (apiKeyInput.trim()) {
      login(apiKeyInput);
      setApiKeyInput('');
    }
  };

  return (
    <div className="login-screen">
      <div className="login-box">
        <div className="login-header">
          <div className="logo">TASK_MANAGER</div>
          <div className="version">v2.0</div>
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

function AppContent() {
  const { settings, refetchSettings } = useSettings();
  const { currentPoints, loadCurrentPoints } = usePoints();
  const {
    tasks,
    todayTasks,
    currentTask,
    stats,
    loading,
    error,
    canRollToday,
    rollMessage,
    loadTasks,
    createTask,
    updateTask,
    deleteTask,
    startTask,
    stopTask,
    completeTask,
    rollTasks,
    checkCanRoll,
  } = useTasks();
  const { habits, todayHabits, loadHabits } = useHabits();

  const [currentView, setCurrentView] = useState('tasks');
  const [showTaskForm, setShowTaskForm] = useState(false);
  const [editingTask, setEditingTask] = useState(null);
  const [rollMood, setRollMood] = useState('');
  const [showMorningCheckIn, setShowMorningCheckIn] = useState(false);
  const [appError, setAppError] = useState(null);
  const [actionInProgress, setActionInProgress] = useState(false);

  // Check for pending roll on mount and periodically
  useEffect(() => {
    if (settings?.pending_roll) {
      setShowMorningCheckIn(true);
    }
  }, [settings]);

  // Periodic refresh
  useEffect(() => {
    const interval = setInterval(() => {
      loadTasks();
      loadHabits();
      loadCurrentPoints();
      checkCanRoll();
      refetchSettings();
    }, 30000);

    return () => clearInterval(interval);
  }, [loadTasks, loadHabits, loadCurrentPoints, checkCanRoll, refetchSettings]);

  const handleStart = async (taskId = null) => {
    if (actionInProgress) return;
    setActionInProgress(true);
    setAppError(null);
    try {
      await startTask(taskId);
    } catch (err) {
      setAppError(err.response?.data?.detail || 'Failed to start task');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleStop = async () => {
    if (actionInProgress) return;
    setActionInProgress(true);
    setAppError(null);
    try {
      await stopTask();
    } catch (err) {
      setAppError(err.response?.data?.detail || 'Failed to stop task');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleComplete = async (taskId = null) => {
    if (actionInProgress) return;
    setActionInProgress(true);
    setAppError(null);
    try {
      await completeTask(taskId);
      await loadCurrentPoints();
    } catch (err) {
      setAppError(err.response?.data?.detail || 'Failed to complete task');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleRoll = async () => {
    if (actionInProgress) return;
    setActionInProgress(true);
    setAppError(null);
    try {
      const mood = rollMood || null;
      await rollTasks(mood);
      setRollMood('');
    } catch (err) {
      setAppError(err.response?.data?.detail || 'Failed to roll tasks');
    } finally {
      setActionInProgress(false);
    }
  };

  const handleMorningCheckInComplete = async () => {
    setShowMorningCheckIn(false);
    setAppError(null);
    await loadTasks();
    await loadHabits();
    await checkCanRoll();
    await refetchSettings();
  };

  const handleSubmitTask = async (taskData) => {
    if (actionInProgress) return;
    setActionInProgress(true);
    setAppError(null);
    try {
      if (editingTask) {
        await updateTask(editingTask.id, taskData);
      } else {
        await createTask(taskData);
      }
      setShowTaskForm(false);
      setEditingTask(null);
    } catch (err) {
      const action = editingTask ? 'update' : 'create';
      setAppError(err.response?.data?.detail || `Failed to ${action} task`);
    } finally {
      setActionInProgress(false);
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
    if (actionInProgress) return;
    setActionInProgress(true);
    setAppError(null);
    try {
      await deleteTask(taskId);
    } catch (err) {
      setAppError(err.response?.data?.detail || 'Failed to delete task');
    } finally {
      setActionInProgress(false);
    }
  };

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
    { id: 'settings', label: '[~] CONFIG' },
  ];

  const displayError = appError || error;

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
        {displayError && <div className="error-message">{displayError}</div>}

        {currentView === 'points' && <PointsDisplay />}
        {currentView === 'goals' && <PointsGoals currentPoints={currentPoints} />}
        {currentView === 'calculator' && <PointsCalculator />}
        {currentView === 'backups' && <Backups />}
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
                      <button className="btn btn-secondary" onClick={handleStop} disabled={actionInProgress}>PAUSE</button>
                    ) : (
                      <button className="btn btn-primary" onClick={() => handleStart(currentTask.id)} disabled={actionInProgress}>RESUME</button>
                    )}
                    <button className="btn btn-success" onClick={() => handleComplete()} disabled={actionInProgress}>COMPLETE</button>
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
                <div className="roll-controls">
                  <select
                    value={rollMood}
                    onChange={(e) => setRollMood(e.target.value)}
                    className="mood-select"
                    title="Filter tasks by energy level"
                  >
                    <option value="">[ ALL ENERGY ]</option>
                    <option value="0">[ E:0 ONLY ]</option>
                    <option value="1">[ E:0-1 ]</option>
                    <option value="2">[ E:0-2 ]</option>
                    <option value="3">[ E:0-3 ]</option>
                    <option value="4">[ E:0-4 ]</option>
                    <option value="5">[ E:0-5 ]</option>
                  </select>
                  <button className="btn btn-secondary" onClick={handleRoll} disabled={actionInProgress}>
                    [ ROLL_DAILY_PLAN ]
                  </button>
                </div>
              ) : (
                rollMessage && <span className="roll-message">{rollMessage}</span>
              )}
              {!currentTask && (
                <button className="btn btn-success" onClick={() => handleStart()} disabled={actionInProgress}>
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
                        settings={settings}
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
                        settings={settings}
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
                    settings={settings}
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
                    settings={settings}
                  />
                </div>
              </div>
            </div>
          </>
        )}
      </main>

      {/* Morning Check-in Modal */}
      {showMorningCheckIn && (
        <MorningCheckIn onComplete={handleMorningCheckInComplete} />
      )}
    </div>
  );
}

export default function App() {
  const { isAuthenticated } = useAuth();

  if (!isAuthenticated) {
    return <LoginScreen />;
  }

  return <AppContent />;
}
