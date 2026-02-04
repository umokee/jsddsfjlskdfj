/**
 * Points display component with history.
 */
import { useState, useEffect } from 'react';
import { usePoints } from '../hooks/usePoints';

function PointsDisplay() {
  const { currentPoints, history, loading, loadHistory, getDayDetails } = usePoints();
  const [showHistory, setShowHistory] = useState(false);
  const [days, setDays] = useState(7);
  const [selectedDay, setSelectedDay] = useState(null);
  const [dayDetails, setDayDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  useEffect(() => {
    if (showHistory) {
      loadHistory(days);
    }
  }, [days, showHistory, loadHistory]);

  const fetchDayDetails = async (date) => {
    setLoadingDetails(true);
    const details = await getDayDetails(date);
    setDayDetails(details);
    setSelectedDay(date);
    setLoadingDetails(false);
  };

  const closeDayDetails = () => {
    setSelectedDay(null);
    setDayDetails(null);
  };

  const todayStats = history.length > 0 ? history[0] : null;

  return (
    <div className="points-display">
      <div className="points-current">
        <h2>Total Points</h2>
        <div className="points-value">{currentPoints}</div>
        {todayStats && (
          <div className="points-today">
            <div>Today: {todayStats.daily_total > 0 ? '+' : ''}{todayStats.daily_total}</div>
            <div className="points-breakdown">
              <span className="earned">+{todayStats.points_earned}</span>
              {todayStats.points_penalty > 0 && (
                <span className="penalty">-{todayStats.points_penalty}</span>
              )}
            </div>
          </div>
        )}
      </div>

      <button
        className="toggle-history-btn"
        onClick={() => setShowHistory(!showHistory)}
      >
        {showHistory ? 'Hide History' : 'Show History'}
      </button>

      {showHistory && (
        <div className="points-history">
          <div className="history-controls">
            <select value={days} onChange={(e) => setDays(parseInt(e.target.value))}>
              <option value="7">Last 7 days</option>
              <option value="14">Last 14 days</option>
              <option value="30">Last 30 days</option>
            </select>
          </div>

          {loading ? (
            <div className="loading">Loading...</div>
          ) : (
            <div className="history-list">
              {history.map((entry) => (
                <div
                  key={entry.id}
                  className="history-entry clickable"
                  onClick={() => fetchDayDetails(entry.date)}
                  title="Click for details"
                >
                  <div className="history-date">
                    {new Date(entry.date).toLocaleDateString()}
                  </div>
                  <div className="history-stats">
                    <div className="stat">
                      <span className="stat-label">Tasks:</span>
                      <span className="stat-value">{entry.tasks_completed}/{entry.tasks_planned}</span>
                    </div>
                    <div className="stat">
                      <span className="stat-label">Habits:</span>
                      <span className="stat-value">{entry.habits_completed}</span>
                    </div>
                    <div className="stat">
                      <span className="stat-label">Rate:</span>
                      <span className="stat-value">{(entry.completion_rate * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                  <div className="history-points">
                    <div className="earned">+{entry.points_earned}</div>
                    {entry.points_penalty > 0 && (
                      <div className="penalty">-{entry.points_penalty}</div>
                    )}
                    <div className={`total ${entry.daily_total < 0 ? 'negative' : ''}`}>
                      {entry.daily_total > 0 ? '+' : ''}{entry.daily_total}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Day Details Modal */}
      {selectedDay && (
        <div className="modal-overlay" onClick={closeDayDetails}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Details for {new Date(selectedDay).toLocaleDateString()}</h3>
              <button className="modal-close" onClick={closeDayDetails}>x</button>
            </div>

            {loadingDetails ? (
              <div className="modal-loading">Loading...</div>
            ) : dayDetails && !dayDetails.error ? (
              <div className="modal-body">
                {/* Summary */}
                <div className="day-summary">
                  <div className="summary-stat">
                    <span className="earned">+{dayDetails.summary.points_earned}</span>
                    {dayDetails.summary.points_penalty > 0 && (
                      <span className="penalty">-{dayDetails.summary.points_penalty}</span>
                    )}
                    <span className={`total ${dayDetails.summary.points_earned - dayDetails.summary.points_penalty < 0 ? 'negative' : ''}`}>
                      = {dayDetails.summary.points_earned - dayDetails.summary.points_penalty}
                    </span>
                  </div>
                  <div className="summary-completion">
                    Tasks: {dayDetails.summary.tasks_completed}/{dayDetails.summary.tasks_planned}
                    {' '}({(dayDetails.summary.completion_rate * 100).toFixed(0)}%)
                  </div>
                </div>

                {/* Completed Tasks */}
                {dayDetails.completed_tasks && dayDetails.completed_tasks.length > 0 && (
                  <div className="details-section">
                    <h4>Completed Tasks ({dayDetails.completed_tasks.length})</h4>
                    <div className="details-list">
                      {dayDetails.completed_tasks.map((task) => (
                        <div key={task.id} className="detail-item">
                          <span className="item-desc">{task.description}</span>
                          {task.project && <span className="item-project">{task.project}</span>}
                          <span className="item-energy">E:{task.energy}</span>
                          {task.points > 0 && <span className="item-points">+{task.points}</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Completed Habits */}
                {dayDetails.completed_habits && dayDetails.completed_habits.length > 0 && (
                  <div className="details-section">
                    <h4>Completed Habits ({dayDetails.completed_habits.length})</h4>
                    <div className="details-list">
                      {dayDetails.completed_habits.map((habit) => (
                        <div key={habit.id} className="detail-item">
                          <span className="item-desc">{habit.description}</span>
                          <span className="item-type">{habit.habit_type?.toUpperCase()}</span>
                          {habit.streak > 0 && <span className="item-streak">STREAK: {habit.streak}</span>}
                          {habit.points > 0 && <span className="item-points">+{habit.points}</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Penalties */}
                {dayDetails.penalties && dayDetails.penalties.total > 0 && (
                  <div className="details-section">
                    <h4>Penalties (-{dayDetails.penalties.total})</h4>
                    <div className="details-list">
                      {dayDetails.penalties.idle_penalty > 0 && (
                        <div className="detail-item penalty">
                          <span className="item-desc">Idle Penalty</span>
                          <span className="item-value">-{dayDetails.penalties.idle_penalty}</span>
                        </div>
                      )}
                      {dayDetails.penalties.incomplete_penalty > 0 && (
                        <div className="detail-item penalty">
                          <span className="item-desc">Incomplete Tasks</span>
                          <span className="item-value">-{dayDetails.penalties.incomplete_penalty}</span>
                        </div>
                      )}
                      {dayDetails.penalties.missed_habits_penalty > 0 && (
                        <div className="detail-item penalty">
                          <span className="item-desc">Missed Habits</span>
                          <span className="item-value">-{dayDetails.penalties.missed_habits_penalty}</span>
                        </div>
                      )}
                      {dayDetails.penalties.progressive_multiplier > 1 && (
                        <div className="detail-item">
                          <span className="item-desc">Progressive Multiplier</span>
                          <span className="item-value">x{dayDetails.penalties.progressive_multiplier.toFixed(1)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="modal-error">
                {dayDetails?.error || 'Failed to load details'}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default PointsDisplay;
